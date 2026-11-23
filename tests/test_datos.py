import sqlite3
from pathlib import Path
from src.datos import limpiar_empleados, leer_consultas

def fila(**cambios):
    base = {"id_empleado": "E001", "nombre": "Ana", "correo": "ana@ejemplo.com", "area": "TI",
            "cargo": "Analista", "fecha_ingreso": "2021-01-01",
            "dias_vacaciones_disponibles": "5", "documento": "123"}
    return {**base, **cambios}


def test_correo_se_normaliza():
    limpios, _ = limpiar_empleados([fila(correo=" ANA@Ejemplo.com ")])
    assert limpios[0]["correo"] == "ana@ejemplo.com"


def test_area_vacia_queda_sin_area():
    limpios, eventos = limpiar_empleados([fila(area="")])
    assert limpios[0]["area"] == "SIN_AREA"
    assert len(eventos) == 1


def test_duplicado_exacto_queda_una_vez():
    limpios, _ = limpiar_empleados([fila(), fila()])
    assert len(limpios) == 1


def test_consulta_c_excluye_saldo_igual_a_5():
    conn = sqlite3.connect(":memory:")
    conn.executescript(Path("sql/schema.sql").read_text(encoding="utf-8"))
    conn.executemany("INSERT INTO empleados VALUES (?,?,?,?,?,?,?,?)", [
        ("E1", "Cinco", "a@x.com", "TI", "", "2021-01-01", 5, "1"),
        ("E2", "Cuatro", "b@x.com", "TI", "", "2021-01-01", 4, "2"),
    ])
    sql = leer_consultas("sql/consultas.sql")["consulta_c_saldo_menor_5"]
    ids = [f[0] for f in conn.execute(sql)]
    assert ids == ["E2"]