import numpy as np
import pandas as pd
import pytest

from btc_radar.indicadores import (
    drawdown,
    ratio_compra_agresiva,
    retornos_log,
    volatilidad_anualizada,
)


def test_retornos_log():
    r = retornos_log(pd.Series([100.0, 110.0, 99.0]))
    assert np.isnan(r.iloc[0])
    assert r.iloc[1] == pytest.approx(np.log(1.1))
    assert r.iloc[2] == pytest.approx(np.log(0.9))


def test_volatilidad_precio_constante_es_cero():
    vol = volatilidad_anualizada(pd.Series([100.0] * 40), ventana=30)
    assert vol.iloc[-1] == 0
    assert vol.iloc[:30].isna().all()  # hacen falta 30 retornos


def test_volatilidad_escala_con_raiz_del_tiempo():
    close = pd.Series(np.exp(np.cumsum([0.01, -0.01] * 20)) * 100)
    diaria = retornos_log(close).rolling(10).std()
    anual = volatilidad_anualizada(close, ventana=10, interval="1d")
    assert anual.iloc[-1] == pytest.approx(diaria.iloc[-1] * np.sqrt(365))


def test_drawdown():
    dd = drawdown(pd.Series([100.0, 120.0, 60.0, 90.0, 130.0]))
    assert dd.tolist() == pytest.approx([0, 0, -0.5, -0.25, 0])


def test_ratio_compra_agresiva():
    df = pd.DataFrame({"volume": [10.0, 4.0], "taker_buy_volume": [7.0, 1.0]})
    assert ratio_compra_agresiva(df).tolist() == pytest.approx([0.7, 0.25])
