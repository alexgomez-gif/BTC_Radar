"""Indicadores básicos de precio y volumen."""

import numpy as np
import pandas as pd

# Cripto cotiza todos los días del año
PERIODOS_POR_ANIO = {"1d": 365, "4h": 365 * 6, "1h": 365 * 24}


def retornos_log(close: pd.Series) -> pd.Series:
    """Retorno logarítmico entre velas consecutivas: ln(Pt / Pt-1)."""
    return np.log(close).diff()


def volatilidad_anualizada(
    close: pd.Series, ventana: int = 30, interval: str = "1d"
) -> pd.Series:
    """Desviación estándar móvil de los retornos log, anualizada (en tanto por uno)."""
    return retornos_log(close).rolling(ventana).std() * np.sqrt(
        PERIODOS_POR_ANIO[interval]
    )


def drawdown(close: pd.Series) -> pd.Series:
    """Caída desde el máximo de cierre previo (0 = en máximos, -0.5 = -50 %)."""
    return close / close.cummax() - 1


def ratio_compra_agresiva(df: pd.DataFrame) -> pd.Series:
    """Fracción del volumen ejecutado por compradores agresivos (taker buy).

    > 0.5: dominan las compras a mercado; < 0.5: dominan las ventas a mercado.
    """
    return df["taker_buy_volume"] / df["volume"]
