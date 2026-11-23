"""Misión 2: festivos de Colombia por API REST y cálculo de días hábiles.

Orden para obtener los festivos de un año:
  1. API Nager.Date, con timeout y hasta N reintentos ante fallos transitorios.
  2. Respaldo local en archivo, solo si pasa la validación (año, país, integridad).
  3. Plan C: librería holidays (cálculo sin internet).
  4. Si nada funciona: FestivosNoDisponibles (la solicitud irá a revisión humana).

Demo desde la carpeta raíz:
    python -m src.festivos
"""
import json
import logging
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

log = logging.getLogger(__name__)

# Configuración: viene del .env y tiene valores por defecto razonables
BASE_URL = os.getenv("NAGER_BASE_URL", "https://date.nager.at/api/v3/PublicHolidays")
PAIS = os.getenv("PAIS", "CO")
TIMEOUT = float(os.getenv("API_TIMEOUT_SEG", "10"))
MAX_REINTENTOS = int(os.getenv("API_MAX_REINTENTOS", "3"))
CARPETA_CACHE = Path(os.getenv("CACHE_DIR", "data/cache"))

# Colombia tiene 19 festivos desde la Ley 2578 de 2026 (antes 18).
# Se valida con un rango, no con un número exacto, porque la ley puede cambiar.
MIN_FESTIVOS, MAX_FESTIVOS = 15, 25

# Errores que vale la pena reintentar (pasajeros). Un 404 o un 400 no mejora reintentando.
CODIGOS_TRANSITORIOS = {429, 500, 502, 503, 504}

# Memoria de la ejecución actual: cada año se consulta una sola vez, no una vez por solicitud
_MEMORIA = {}

def limpiar_memoria():
    _MEMORIA.clear()

class FestivosNoDisponibles(Exception):
    """No se pudieron obtener festivos de ninguna fuente."""

 
# ----------- 1. API con reintentos ------------
def descargar_festivos(anio, pais=PAIS):
    """Llama a la API y devuelve un set de fechas. Reintenta solo fallos transitorios."""
    url = f"{BASE_URL}/{anio}/{pais}"
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            if resp.status_code in CODIGOS_TRANSITORIOS:
                raise requests.HTTPError(f"HTTP {resp.status_code} (transitorio)")
            resp.raise_for_status() # 4xx: error persistente, no se reintenta
            datos = resp.json()
            # Solo festivos nacionales: "global" = false indica uno regional
            return {date.fromisoformat(f["date"]) for f in datos if f.get("global", True)}
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            persistente = (isinstance(e, requests.HTTPError) and e.response is not None
                           and e.response.status_code not in CODIGOS_TRANSITORIOS)
            if persistente or intento == MAX_REINTENTOS:
                raise
            espera = 2 ** (intento - 1)      # 1 s, 2 s, 4 s...
            log.warning("API festivos falló (intento %s/%s): %s. Reintento en %ss",
                        intento, MAX_REINTENTOS, e, espera)
            time.sleep(espera)


# ------------ 2. Respaldo local con metadatos y validación --------------
def ruta_respaldo(anio, pais=PAIS):
    return CARPETA_CACHE / f"festivos_{anio}_{pais}.json"

def guardar_respaldo(anio, festivos, pais=PAIS):
    CARPETA_CACHE.mkdir(parents=True, exist_ok=True)
    contenido = {
        "anio": anio,
        "pais": pais,
        "fuente": "nager.date",
        "descargado": datetime.now().isoformat(timespec="seconds"),
        "festivos": sorted(f.isoformat() for f in festivos),
    }
    ruta_respaldo(anio, pais).write_text(json.dumps(contenido, indent=2), encoding="utf-8")

def validar_respaldo(contenido, anio, pais=PAIS):
    """Devuelve la lista de problemas encontrados. Lista vacía = respaldo válido."""
    problemas = []
    if contenido.get("anio") != anio:
        problemas.append(f"año {contenido.get('anio')} distinto de {anio}")
    if contenido.get("pais") != pais:
        problemas.append(f"país {contenido.get('pais')} distinto de {pais}")
    try:
        fechas = [date.fromisoformat(f) for f in contenido.get("festivos", [])]
    except (TypeError, ValueError):
        return problemas + ["fechas con formato inválido"]
    if not MIN_FESTIVOS <= len(fechas) <= MAX_FESTIVOS:
        problemas.append(f"{len(fechas)} festivos, fuera del rango {MIN_FESTIVOS}-{MAX_FESTIVOS}")
    if any(f.year != anio for f in fechas):
        problemas.append("hay fechas de otro año")
    return problemas

def leer_respaldo_valido(anio, pais=PAIS):
    """Devuelve el set de festivos del respaldo, o None si no existe o no es válido."""
    ruta = ruta_respaldo(anio, pais)
    if not ruta.exists():
        return None
    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        log.warning("Respaldo %s ilegible: %s", ruta.name, e)
        return None
    problemas = validar_respaldo(contenido, anio, pais)
    if problemas:
        log.warning("Respaldo %s inválido: %s", ruta.name, "; ".join(problemas))
        return None
    return {date.fromisoformat(f) for f in contenido["festivos"]}


# ------------- 3. Plan C: cálculo offline -------------
def calcular_offline(anio, pais=PAIS):
    import holidays
    return set(holidays.country_holidays(pais, years=anio).keys())


# ---------- Orquestación de las fuentes -------------
def obtener_festivos(anio, pais=PAIS):
    """Devuelve (set_de_festivos, fuente). Usa la memoria si el año ya se consultó."""
    if (anio, pais) not in _MEMORIA:
        _MEMORIA[(anio, pais)] = _obtener_de_fuentes(anio, pais)
    return _MEMORIA[(anio, pais)]

def _obtener_de_fuentes(anio, pais):
    """Prueba API → respaldo → offline."""
    try:
        festivos = descargar_festivos(anio, pais)
        guardar_respaldo(anio, festivos, pais)
        return festivos, "api"
    except Exception as e:  # cualquier fallo de la API pasa al plan B
        log.warning("API festivos no disponible para %s: %s", anio, e)

    festivos = leer_respaldo_valido(anio, pais)
    if festivos:
        log.warning("Usando respaldo local de festivos %s", anio)
        return festivos, "respaldo"

    try:
        festivos = calcular_offline(anio, pais)
        if festivos:
            log.warning("Usando cálculo offline (librería holidays) para %s", anio)
            return festivos, "offline"
    except Exception as e:
        log.error("Cálculo offline falló para %s: %s", anio, e)

    raise FestivosNoDisponibles(f"Sin festivos para {anio}/{pais}")


# -------------- Días hábiles -------------
def dias_habiles(inicio, fin, festivos):
    """Cuenta días de lunes a viernes entre inicio y fin (ambos incluidos), sin festivos."""
    if fin < inicio:
        raise ValueError(f"fecha_fin {fin} es anterior a fecha_inicio {inicio}")
    total, dia = 0, inicio
    while dia <= fin:
        if dia.weekday() < 5 and dia not in festivos:   # 0 = lunes ... 4 = viernes
            total += 1
        dia += timedelta(days=1)
    return total

def festivos_para_rango(inicio, fin, pais=PAIS):
    """Une los festivos de todos los años que toca el rango (ej. 28 dic → 5 ene)."""
    festivos, fuentes = set(), {}
    for anio in range(inicio.year, fin.year + 1):
        f, fuente = obtener_festivos(anio, pais)
        festivos |= f
        fuentes[anio] = fuente
    return festivos, fuentes


# -------------- Demo: los 3 casos de verificación del reto -----------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    casos = {"S01": ("2026-12-14", "2026-12-18", 5),
             "S05": ("2026-12-07", "2026-12-11", 4),
             "S06": ("2026-12-21", "2026-12-31", 8)}
    for sid, (ini, fin, esperado) in casos.items():
        ini, fin = date.fromisoformat(ini), date.fromisoformat(fin)
        festivos, fuentes = festivos_para_rango(ini, fin)
        resultado = dias_habiles(ini, fin, festivos)
        marca = "OK" if resultado == esperado else "REVISAR"
        print(f"{sid}: {resultado} días hábiles (esperado {esperado}) [{marca}] fuente={fuentes}")