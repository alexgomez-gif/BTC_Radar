import pandas as pd

from btc_radar import binance_client as bc

UN_DIA_MS = 86_400_000
INICIO_MS = bc.a_milisegundos("2024-01-01")


def vela(open_ms: int) -> list:
    """Vela sintética con el formato de 12 campos de Binance."""
    return [
        open_ms, "100.0", "110.0", "90.0", "105.0", "10.0",
        open_ms + UN_DIA_MS - 1, "1000.0", 50, "6.0", "600.0", "0",
    ]  # fmt: skip


class RespuestaFalsa:
    def __init__(self, datos):
        self.datos = datos

    def raise_for_status(self):
        pass

    def json(self):
        return self.datos


class SesionFalsa:
    """Simula Binance: devuelve hasta `limit` velas desde `startTime`."""

    def __init__(self, total_velas: int):
        self.velas = [vela(INICIO_MS + i * UN_DIA_MS) for i in range(total_velas)]
        self.peticiones = 0

    def get(self, url, params, timeout):
        self.peticiones += 1
        desde = [v for v in self.velas if v[0] >= params["startTime"]]
        return RespuestaFalsa(desde[: params["limit"]])


def test_a_milisegundos_asume_utc():
    assert bc.a_milisegundos("1970-01-02") == UN_DIA_MS


def test_descargar_klines_pagina_hasta_el_final():
    sesion = SesionFalsa(total_velas=2500)
    filas = bc.descargar_klines(inicio="2024-01-01", sesion=sesion, pausa=0)

    assert len(filas) == 2500
    assert sesion.peticiones == 3  # 1000 + 1000 + 500
    assert [f[0] for f in filas] == sorted({f[0] for f in filas})  # sin duplicados


def test_klines_a_dataframe_tipos():
    df = bc.klines_a_dataframe([vela(INICIO_MS)])

    assert "ignore" not in df.columns
    assert str(df["open_time"].dt.tz) == "UTC"
    assert df["close"].dtype == "float64"
    assert df["trades"].dtype == "int64"
    assert df.loc[0, "open_time"] == pd.Timestamp("2024-01-01", tz="UTC")


def test_klines_a_dataframe_descarta_vela_en_curso():
    hoy_ms = bc.a_milisegundos(pd.Timestamp.now(tz="UTC").normalize())
    filas = [vela(hoy_ms - UN_DIA_MS), vela(hoy_ms)]  # ayer (cerrada) y hoy

    assert len(bc.klines_a_dataframe(filas)) == 1
    assert len(bc.klines_a_dataframe(filas, solo_cerradas=False)) == 2


def test_descargar_y_guardar_escribe_parquet(tmp_path, monkeypatch):
    monkeypatch.setattr(bc, "crear_sesion", lambda: SesionFalsa(total_velas=10))
    ruta = bc.descargar_y_guardar(inicio="2024-01-01", carpeta=tmp_path)

    assert ruta == tmp_path / "BTCUSDT_1d.parquet"
    assert len(pd.read_parquet(ruta)) == 10
