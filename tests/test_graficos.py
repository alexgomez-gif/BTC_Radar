import pandas as pd

from btc_radar.graficos import ROJO, VERDE, grafico_velas


def test_grafico_velas_tiene_precio_y_volumen():
    indice = pd.date_range("2024-01-01", periods=2, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [100.0, 105.0],
            "high": [110.0, 106.0],
            "low": [95.0, 90.0],
            "close": [105.0, 92.0],  # una vela alcista y otra bajista
            "volume": [10.0, 20.0],
        },
        index=indice,
    )
    fig = grafico_velas(df)

    assert [t.type for t in fig.data] == ["candlestick", "bar"]
    assert list(fig.data[1].marker.color) == [VERDE, ROJO]
