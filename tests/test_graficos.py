import pandas as pd
import pytest

from btc_radar.graficos import (
    NARANJA,
    ROJO,
    VERDE,
    grafico_perfil_volumen,
    grafico_velas,
)
from btc_radar.volume_profile import area_de_valor, nodos_volumen, perfil_volumen


@pytest.fixture
def df() -> pd.DataFrame:
    indice = pd.date_range("2024-01-01", periods=2, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0, 105.0],
            "high": [110.0, 106.0],
            "low": [95.0, 90.0],
            "close": [105.0, 92.0],  # una vela alcista y otra bajista
            "volume": [10.0, 20.0],
            "taker_buy_volume": [6.0, 8.0],
        },
        index=indice,
    )


def test_grafico_velas_tiene_precio_y_volumen(df):
    fig = grafico_velas(df)

    assert [t.type for t in fig.data] == ["candlestick", "bar"]
    assert list(fig.data[1].marker.color) == [VERDE, ROJO]


def test_grafico_perfil_volumen_marca_poc_y_niveles(df):
    perfil = perfil_volumen(df, n_niveles=10)
    niveles = area_de_valor(perfil)
    fig = grafico_perfil_volumen(df, perfil, niveles, nodos_volumen(perfil))

    assert [t.type for t in fig.data][:3] == ["candlestick", "bar", "bar"]
    perfil_trace = fig.data[2]
    assert perfil_trace.orientation == "h"
    assert list(perfil_trace.marker.color).count(NARANJA) == 1  # un único POC
    textos = [a.text for a in fig.layout.annotations]
    assert any(t.startswith("POC") for t in textos)
    assert any(t.startswith("VAH") for t in textos)
    assert any(t.startswith("VAL") for t in textos)
