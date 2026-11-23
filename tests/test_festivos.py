import json
from datetime import date

import pytest
import requests

from src import festivos as fx
from src.festivos import dias_habiles

FESTIVOS_DIC_2026 = {date(2026, 12, 8), date(2026, 12, 25)}

@pytest.fixture(autouse=True)
def memoria_limpia():
    """Cada prueba empieza sin festivos en memoria."""
    fx.limpiar_memoria()


# --- Días hábiles (prueba obligatoria del reto) -----------------------------
@pytest.mark.parametrize("inicio, fin, esperado", [
    ("2026-12-14", "2026-12-18", 5),   # S01: semana normal
    ("2026-12-07", "2026-12-11", 4),   # S05: el 8 de diciembre es festivo
    ("2026-12-21", "2026-12-31", 8),   # S06: el 25 de diciembre es festivo
])
def test_dias_habiles_casos_del_reto(inicio, fin, esperado):
    assert dias_habiles(date.fromisoformat(inicio), date.fromisoformat(fin), FESTIVOS_DIC_2026) == esperado

def test_fin_anterior_a_inicio_falla():
    with pytest.raises(ValueError):
        dias_habiles(date(2026, 12, 18), date(2026, 12, 14), set())


# --- Respaldo y su validación ------------------------------------------------
@pytest.fixture
def cache_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(fx, "CARPETA_CACHE", tmp_path)
    return tmp_path

def fechas_del_anio(anio, n=19):
    return {date(anio, 1, 1 + i) for i in range(n)}

def test_respaldo_de_otro_anio_no_se_usa(cache_temporal):
    fx.guardar_respaldo(2026, fechas_del_anio(2026))
    # se renombra para simular que alguien pide 2027 y solo existe el de 2026
    (cache_temporal / "festivos_2026_CO.json").rename(cache_temporal / "festivos_2027_CO.json")
    assert fx.leer_respaldo_valido(2027) is None

def test_respaldo_con_pocos_festivos_no_se_usa(cache_temporal):
    fx.guardar_respaldo(2026, fechas_del_anio(2026, n=3))
    assert fx.leer_respaldo_valido(2026) is None

def test_respaldo_valido_se_usa(cache_temporal):
    fx.guardar_respaldo(2026, fechas_del_anio(2026))
    assert len(fx.leer_respaldo_valido(2026)) == 19


# --- Cadena de fuentes: API → respaldo → offline ----------------------------
def api_caida(*args, **kwargs):
    raise requests.ConnectionError("sin red")

def test_api_caida_usa_respaldo_valido(cache_temporal, monkeypatch):
    fx.guardar_respaldo(2026, fechas_del_anio(2026))
    monkeypatch.setattr(fx, "descargar_festivos", api_caida)
    _, fuente = fx.obtener_festivos(2026)
    assert fuente == "respaldo"

def test_sin_api_ni_respaldo_usa_calculo_offline(cache_temporal, monkeypatch):
    monkeypatch.setattr(fx, "descargar_festivos", api_caida)
    festivos, fuente = fx.obtener_festivos(2026)
    assert fuente == "offline"
    assert date(2026, 12, 8) in festivos and date(2026, 12, 25) in festivos

def test_sin_ninguna_fuente_lanza_error(cache_temporal, monkeypatch):
    monkeypatch.setattr(fx, "descargar_festivos", api_caida)
    monkeypatch.setattr(fx, "calcular_offline", lambda *a, **k: set())
    with pytest.raises(fx.FestivosNoDisponibles):
        fx.obtener_festivos(2026)


# --- Reintentos ---------------------------------------------------------------
class RespuestaFalsa:
    def __init__(self, status, datos=None):
        self.status_code, self._datos = status, datos or []

    def json(self):
        return self._datos

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


def test_reintenta_ante_fallo_transitorio(monkeypatch):
    respuestas = [RespuestaFalsa(503), RespuestaFalsa(503),
                  RespuestaFalsa(200, [{"date": "2026-12-25", "global": True}])]
    monkeypatch.setattr(fx.requests, "get", lambda *a, **k: respuestas.pop(0))
    monkeypatch.setattr(fx.time, "sleep", lambda s: None)   # no esperar en la prueba
    assert fx.descargar_festivos(2026) == {date(2026, 12, 25)}


def test_no_reintenta_error_404(monkeypatch):
    llamadas = []
    def get_404(*a, **k):
        llamadas.append(1)
        return RespuestaFalsa(404)
    monkeypatch.setattr(fx.requests, "get", get_404)
    with pytest.raises(requests.HTTPError):
        fx.descargar_festivos(2026)
    assert len(llamadas) == 1


def test_rango_que_cruza_de_anio_pide_ambos_anios(monkeypatch):
    pedidos = []
    monkeypatch.setattr(fx, "obtener_festivos", lambda anio, pais="CO": (pedidos.append(anio) or set(), "api"))
    fx.festivos_para_rango(date(2026, 12, 28), date(2027, 1, 5))
    assert pedidos == [2026, 2027]