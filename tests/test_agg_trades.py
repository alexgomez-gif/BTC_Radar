import hashlib
import io
import zipfile
from datetime import date

import pandas as pd
import pytest

from btc_radar import agg_trades as at

# 2026-01-01 00:00:00 UTC
T0_MS = 1_767_225_600_000

FILAS_CSV = [
    f"1,60000.0,0.5,10,12,{T0_MS * 1000 + 1},False,True",  # compra agresiva, µs
    f"2,59990.0,1.0,13,13,{T0_MS * 1000 + 2},True,True",  # venta agresiva
]


def zip_csv(lineas: list[str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("BTCUSDT-aggTrades-2026-01-01.csv", "\n".join(lineas) + "\n")
    return buffer.getvalue()


def test_leer_zip_tipos_y_lado():
    df = at.leer_zip(zip_csv(FILAS_CSV))

    assert df["compra_agresiva"].tolist() == [True, False]
    assert df["compra_agresiva"].dtype == bool
    assert df["n_trades"].tolist() == [3, 1]
    assert df.loc[0, "time"] == pd.Timestamp("2026-01-01 00:00:00.000001", tz="UTC")


def test_leer_zip_con_cabecera_y_milisegundos():
    cabecera = ",".join(at.COLUMNAS_CSV)
    fila_ms = f"1,60000.0,0.5,10,10,{T0_MS},false,true"
    df = at.leer_zip(zip_csv([cabecera, fila_ms]))

    assert len(df) == 1
    assert df.loc[0, "time"] == pd.Timestamp("2026-01-01", tz="UTC")
    assert bool(df.loc[0, "compra_agresiva"])


def test_verificar_checksum():
    contenido = b"datos"
    correcto = hashlib.sha256(contenido).hexdigest()

    at.verificar_checksum(contenido, f"{correcto}  archivo.zip")
    with pytest.raises(ValueError, match="Checksum"):
        at.verificar_checksum(contenido, "0" * 64 + "  archivo.zip")


class RespuestaFalsa:
    def __init__(self, contenido: bytes):
        self.content = contenido
        self.text = contenido.decode(errors="ignore")

    def raise_for_status(self):
        pass


class SesionFalsa:
    def __init__(self):
        self.zip = zip_csv(FILAS_CSV)
        self.peticiones = 0

    def get(self, url, timeout):
        self.peticiones += 1
        if url.endswith(".CHECKSUM"):
            return RespuestaFalsa(hashlib.sha256(self.zip).hexdigest().encode())
        return RespuestaFalsa(self.zip)


def test_descargar_dia_guarda_y_reutiliza(tmp_path):
    sesion = SesionFalsa()
    ruta = at.descargar_dia(date(2026, 1, 1), carpeta=tmp_path, sesion=sesion)

    assert ruta.name == "BTCUSDT-aggTrades-2026-01-01.parquet"
    assert len(pd.read_parquet(ruta)) == 2
    assert sesion.peticiones == 2  # ZIP + CHECKSUM

    at.descargar_dia(date(2026, 1, 1), carpeta=tmp_path, sesion=sesion)
    assert sesion.peticiones == 2  # ya existía: no vuelve a descargar


def test_ultimos_dias_excluye_hoy():
    dias = at.ultimos_dias(3, hasta=date(2026, 1, 10))
    assert dias == [date(2026, 1, 7), date(2026, 1, 8), date(2026, 1, 9)]


def test_cargar_trades_avisa_si_faltan_dias(tmp_path):
    with pytest.raises(FileNotFoundError, match="btc-trades"):
        at.cargar_trades([date(2026, 1, 1)], carpeta=tmp_path)
