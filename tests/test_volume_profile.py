import numpy as np
import pandas as pd
import pytest

from btc_radar.volume_profile import area_de_valor, nodos_volumen, perfil_volumen


def velas(filas: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """(low, high, volume, taker_buy_volume); el volumen en USD es volume × 100."""
    df = pd.DataFrame(filas, columns=["low", "high", "volume", "taker_buy_volume"])
    df["quote_volume"] = df["volume"] * 100
    df["taker_buy_quote_volume"] = df["taker_buy_volume"] * 100
    return df


def perfil_sintetico(volumenes: list[float]) -> pd.DataFrame:
    bajo = np.arange(len(volumenes), dtype=float)
    return pd.DataFrame(
        {
            "precio_bajo": bajo,
            "precio_alto": bajo + 1,
            "precio": bajo + 0.5,
            "volumen": volumenes,
        }
    )


def test_perfil_reparte_uniforme_y_conserva_el_volumen():
    perfil = perfil_volumen(velas([(0, 10, 50, 20)]), n_niveles=10)

    assert perfil["volumen"].tolist() == pytest.approx([5.0] * 10)
    assert perfil["volumen"].sum() == pytest.approx(50)
    assert (perfil["volumen_compra"] + perfil["volumen_venta"]).tolist() == (
        pytest.approx(perfil["volumen"].tolist())
    )


def test_perfil_vela_sin_recorrido_va_a_su_nivel():
    # Segunda vela con high == low == 7.5 → todo su volumen al nivel 7-8
    perfil = perfil_volumen(velas([(0, 10, 10, 5), (7.5, 7.5, 4, 2)]), n_niveles=10)

    assert perfil.loc[7, "volumen"] == pytest.approx(1 + 4)
    assert perfil["volumen"].sum() == pytest.approx(14)


def test_perfil_en_usd_usa_quote_volume():
    perfil = perfil_volumen(velas([(0, 10, 50, 20)]), n_niveles=10, en_usd=True)
    assert perfil["volumen"].sum() == pytest.approx(5000)
    assert perfil["volumen_compra"].sum() == pytest.approx(2000)


def test_area_de_valor_crece_hacia_el_vecino_con_mas_volumen():
    # Total 17 → objetivo 11.9: POC (10) + nivel de arriba (3) = 13
    niveles = area_de_valor(perfil_sintetico([1, 2, 10, 3, 1]))

    assert niveles.poc == 2.5
    assert niveles.val == 2.0
    assert niveles.vah == 4.0


def test_area_de_valor_cubre_al_menos_el_porcentaje():
    rng = np.random.default_rng(42)
    perfil = perfil_sintetico(rng.uniform(0, 100, 50).tolist())
    niveles = area_de_valor(perfil, porcentaje=0.70)

    dentro = perfil[
        (perfil["precio_bajo"] >= niveles.val) & (perfil["precio_alto"] <= niveles.vah)
    ]
    assert dentro["volumen"].sum() >= 0.70 * perfil["volumen"].sum()
    assert niveles.val <= niveles.poc <= niveles.vah


def test_nodos_volumen_perfil_bimodal():
    x = np.arange(60)
    bimodal = np.exp(-((x - 15) ** 2) / 20) + np.exp(-((x - 45) ** 2) / 20)
    nodos = nodos_volumen(perfil_sintetico(bimodal.tolist()))

    assert nodos["tipo"].tolist() == ["HVN", "LVN", "HVN"]
    assert nodos["precio"].tolist() == pytest.approx([15.5, 30.5, 45.5], abs=1)
