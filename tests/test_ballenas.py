import pandas as pd
import pytest

from btc_radar.ballenas import (
    agrupar_ordenes,
    cvd,
    delta_usd,
    detectar_ballenas,
    flujo_por_tamano,
    velas_desde_trades,
)

T = pd.Timestamp("2026-01-01 00:00", tz="UTC")


@pytest.fixture
def trades() -> pd.DataFrame:
    """Una compra que barre 3 niveles, una venta y una compra pequeña."""
    return pd.DataFrame(
        {
            "time": [T, T, T, T + pd.Timedelta("1s"), T + pd.Timedelta("1h")],
            "price": [100.0, 101.0, 102.0, 99.0, 103.0],
            "quantity": [1.0, 1.0, 2.0, 5.0, 0.5],
            "compra_agresiva": [True, True, True, False, True],
        }
    )


def test_agrupar_ordenes_une_niveles_barridos(trades):
    ordenes = agrupar_ordenes(trades)

    assert len(ordenes) == 3
    primera = ordenes.iloc[0]
    assert primera["niveles"] == 3
    assert primera["cantidad"] == 4.0
    assert primera["usd"] == pytest.approx(100 + 101 + 204)
    assert primera["precio_medio"] == pytest.approx(405 / 4)
    assert (primera["precio_min"], primera["precio_max"]) == (100.0, 102.0)


def test_mismo_instante_lado_distinto_son_ordenes_distintas():
    df = pd.DataFrame(
        {
            "time": [T, T],
            "price": [100.0, 100.0],
            "quantity": [1.0, 1.0],
            "compra_agresiva": [True, False],
        }
    )
    assert len(agrupar_ordenes(df)) == 2


def test_delta_usd_signo(trades):
    ordenes = agrupar_ordenes(trades)
    assert delta_usd(ordenes).tolist() == pytest.approx([405.0, -495.0, 51.5])


def test_detectar_ballenas_umbral_fijo_y_percentil(trades):
    ordenes = agrupar_ordenes(trades)

    assert detectar_ballenas(ordenes, umbral_usd=400)["usd"].tolist() == (
        pytest.approx([405.0, 495.0])
    )
    assert len(detectar_ballenas(ordenes, percentil=0.99)) == 1  # solo la mayor


def test_flujo_por_tamano(trades):
    ordenes = agrupar_ordenes(trades)
    tabla = flujo_por_tamano(ordenes, cortes=[0, 100, 1000], etiquetas=["<100", "100+"])

    assert tabla.loc["<100", "ordenes"] == 1
    assert tabla.loc["<100", "delta_pct"] == pytest.approx(1.0)  # todo compra
    assert tabla.loc["100+", "delta_usd"] == pytest.approx(405 - 495)
    assert tabla["volumen_pct"].sum() == pytest.approx(1.0)


def test_cvd_acumula_por_hora(trades):
    serie = cvd(agrupar_ordenes(trades), frecuencia="1h")
    assert serie.tolist() == pytest.approx([405 - 495, 405 - 495 + 51.5])


def test_velas_desde_trades(trades):
    velas = velas_desde_trades(trades, frecuencia="1h")

    primera = velas.iloc[0]
    assert (primera["open"], primera["high"], primera["low"], primera["close"]) == (
        100.0,
        102.0,
        99.0,
        99.0,
    )
    assert primera["volume"] == 9.0
    assert primera["taker_buy_volume"] == 4.0
    assert len(velas) == 2
