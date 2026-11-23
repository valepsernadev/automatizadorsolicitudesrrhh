"""
Misión 1: leer, limpiar y cargar los datos en SQLite, y ejecutar las 3 consultas.
Se ejecuta desde la carpeta raíz del proyecto con: python -m src.datos
"""

import csv
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

# Rutas (más adelante vendrán del archivo .env)
RUTA_EMPLEADOS = Path("data/empleados.csv")
RUTA_SOLICITUDES = Path("data/solicitudes.json")
RUTA_DB = Path("data/talento.db")
RUTA_SCHEMA = Path("sql/schema.sql")
RUTA_CONSULTAS = Path("sql/consultas.sql")
CARPETA_SALIDA = Path("output")

CANALES_VALIDOS = {"correo", "chat", "formulario"}


# ---------- 1. LEER: pasar los archivos a listas de diccionarios (todo como texto) -----------

def leer_empleados(ruta):
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def leer_solicitudes(ruta):
    with open(ruta, encoding="utf-8-sig") as f:
        return json.load(f)

# ---------- 2. LIMPIAR: funciones puras. Reciben filas y devuelven (filas_limpias, eventos).
#    No tocan la base de datos, por eso se pueden probar con pytest. -------------

def evento(tabla, registro, campo, original, nuevo, regla):
    return {"tabla": tabla, "registro": registro, "campo": campo,
            "valor_original": original, "valor_nuevo": nuevo, "regla": regla}

def limpiar_empleados(filas):
    limpios, eventos, vistos = [], [], {}

    for fila in filas:
        emp = {k: (v or "").strip() for k, v in fila.items()} # quitar espacios
        eid = emp["id_empleado"]

        correo_original = fila["correo"]
        emp["correo"] = emp["correo"].lower() # normalizar correo
        if emp["correo"] != correo_original:
            eventos.append(evento("empleados", eid, "correo", correo_original, emp["correo"],
                                  "Correo normalizado: sin espacios y en minúsculas"))

        if not emp["area"]: # área vacía
            emp["area"] = "SIN_AREA"
            eventos.append(evento("empleados", eid, "area", "", "SIN_AREA",
                                  "Área vacía: se marca SIN_AREA y no se borra la fila"))

        emp["dias_vacaciones_disponibles"] = int(emp["dias_vacaciones_disponibles"]) # tipos
        date.fromisoformat(emp["fecha_ingreso"]) # valida la fecha

        if eid in vistos: # duplicados
            regla = ("Duplicado exacto: se conserva una sola fila" if vistos[eid] == emp
                     else "CONFLICTO: mismo id con datos distintos; se conserva la primera fila")
            eventos.append(evento("empleados", eid, None, None, None, regla))
            continue

        vistos[eid] = emp
        limpios.append(emp)
    return limpios, eventos

def limpiar_solicitudes(filas):
    limpias, eventos, ids = [], [], set()

    for fila in filas:
        sol = {k: (v.strip() if isinstance(v, str) else v) for k, v in fila.items()}
        sid = sol["id_solicitud"]

        if sid in ids:
            eventos.append(evento("solicitudes", sid, None, None, None,
                                  "Solicitud duplicada: se conserva la primera"))
            continue
        date.fromisoformat(sol["fecha_recepcion"])
        if sol["canal"] not in CANALES_VALIDOS:
            raise ValueError(f"{sid}: canal no válido '{sol['canal']}'")

        ids.add(sid)
        limpias.append(sol)

    return limpias, eventos


# ------------ 3. CARGAR: crear tablas e insertar todo en una sola transacción -----------

def cargar(conn, empleados, solicitudes, eventos, id_ejecucion):
    with conn:  # si algo falla, no se guarda nada
        conn.executescript(RUTA_SCHEMA.read_text(encoding="utf-8"))
        conn.execute("DELETE FROM empleados")     # idempotente: se recarga desde cero
        conn.execute("DELETE FROM solicitudes")
        conn.executemany(
            "INSERT INTO empleados VALUES (:id_empleado, :nombre, :correo, :area, :cargo, "
            ":fecha_ingreso, :dias_vacaciones_disponibles, :documento)", empleados)
        conn.executemany(
            "INSERT INTO solicitudes VALUES (:id_solicitud, :id_empleado, :fecha_recepcion, "
            ":canal, :texto, :etiqueta_esperada)", solicitudes)
        conn.executemany(
            "INSERT INTO log_limpieza (id_ejecucion, tabla, registro, campo, valor_original, "
            "valor_nuevo, regla) VALUES (:id_ejecucion, :tabla, :registro, :campo, "
            ":valor_original, :valor_nuevo, :regla)",
            [{**e, "id_ejecucion": id_ejecucion} for e in eventos])


# ---------- 4. CONSULTAR: ejecutar cada consulta de sql/consultas.sql y guardar un CSV ------------
def leer_consultas(ruta):
    """Separa el archivo en {nombre: sql} usando las líneas '-- nombre: ...'."""
    consultas, nombre, lineas = {}, None, []
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        if linea.startswith("-- nombre:"):
            if nombre:
                consultas[nombre] = "\n".join(lineas)
            nombre, lineas = linea.split(":", 1)[1].strip(), []
        else:
            lineas.append(linea)
    if nombre:
        consultas[nombre] = "\n".join(lineas)
    return consultas

def guardar_csv(ruta, encabezados, filas):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(encabezados)
        escritor.writerows(filas)

def ejecutar_consultas(conn):
    for nombre, sql in leer_consultas(RUTA_CONSULTAS).items():
        cursor = conn.execute(sql)
        encabezados = [col[0] for col in cursor.description]
        filas = cursor.fetchall()
        guardar_csv(CARPETA_SALIDA / "sql" / f"{nombre}.csv", encabezados, filas)
        print(f"  {nombre}: {len(filas)} filas")

def exportar_log(conn, id_ejecucion):
    cursor = conn.execute(
        "SELECT tabla, registro, campo, valor_original, valor_nuevo, regla "
        "FROM log_limpieza WHERE id_ejecucion = ?", (id_ejecucion,))
    guardar_csv(CARPETA_SALIDA / "log_limpieza.csv",
                [c[0] for c in cursor.description], cursor.fetchall())


# ------------ PUNTO DE ENTRADA: lo que pasa al ejecutar "python -m src.datos" ----------

def ejecutar():
    id_ejecucion = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    print(f"Misión 1 · ejecución {id_ejecucion}")

    empleados, ev_emp = limpiar_empleados(leer_empleados(RUTA_EMPLEADOS))
    solicitudes, ev_sol = limpiar_solicitudes(leer_solicitudes(RUTA_SOLICITUDES))
    eventos = ev_emp + ev_sol
    print(f"  {len(empleados)} empleados, {len(solicitudes)} solicitudes, {len(eventos)} eventos de limpieza")

    conn = sqlite3.connect(RUTA_DB)
    try:
        cargar(conn, empleados, solicitudes, eventos, id_ejecucion)
        ejecutar_consultas(conn)
        exportar_log(conn, id_ejecucion)
    finally:
        conn.close()
    print("Listo. Revisa la carpeta output/")

if __name__ == "__main__":
    ejecutar()


