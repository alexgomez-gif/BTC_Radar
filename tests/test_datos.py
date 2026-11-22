import pandas as pd
import pytest

from btc_radar.datos import cargar_velas, detectar_huecos


def velas_4h(tiempos: list[str]) -> pd.DataFrame:
    indice = pd.DatetimeIndex(pd.to_datetime(tiempos, utc=True), name="open_time")
    return pd.DataFrame({"close": range(len(tiempos))}, index=indice)


def test_detectar_huecos_sin_huecos():
    df = velas_4h(["2024-01-01 00:00", "2024-01-01 04:00", "2024-01-01 08:00"])
    assert detectar_huecos(df, "4h").empty


def test_detectar_huecos_cuenta_velas_faltantes():
    # Faltan las velas de las 08:00 y las 12:00
    df = velas_4h(["2024-01-01 00:00", "2024-01-01 04:00", "2024-01-01 16:00"])
    huecos = detectar_huecos(df, "4h")

    assert len(huecos) == 1
    assert huecos.loc[0, "desde"] == pd.Timestamp("2024-01-01 08:00", tz="UTC")
    assert huecos.loc[0, "hasta"] == pd.Timestamp("2024-01-01 16:00", tz="UTC")
    assert huecos.loc[0, "velas_faltantes"] == 2


def test_cargar_velas_indexa_por_open_time(tmp_path):
    df = velas_4h(["2024-01-01 00:00", "2024-01-01 04:00"]).reset_index()
    df.to_parquet(tmp_path / "BTCUSDT_4h.parquet", index=False)

    cargado = cargar_velas("4h", carpeta=tmp_path)
    assert cargado.index.name == "open_time"
    assert len(cargado) == 2


def test_cargar_velas_sin_archivo_explica_que_hacer(tmp_path):
    with pytest.raises(FileNotFoundError, match="btc-descargar"):
        cargar_velas("1d", carpeta=tmp_path)
