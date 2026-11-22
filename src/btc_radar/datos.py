"""Carga de las velas descargadas y controles de calidad."""

from pathlib import Path

import pandas as pd

from btc_radar.binance_client import ruta_parquet
from btc_radar.config import RAW_DIR


def cargar_velas(
    interval: str = "1d", symbol: str = "BTCUSDT", carpeta: Path = RAW_DIR
) -> pd.DataFrame:
    """Lee data/raw/{symbol}_{interval}.parquet con `open_time` como índice."""
    ruta = ruta_parquet(symbol, interval, carpeta)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Ejecuta primero: btc-descargar")
    return pd.read_parquet(ruta).set_index("open_time")


def detectar_huecos(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Devuelve los tramos sin velas (p. ej. mantenimientos del exchange).

    `interval` es el de Binance (15m, 1h, 4h, 1d, 1w).
    """
    paso = pd.Timedelta(interval)
    tiempos = df.index.to_series()
    salto = tiempos.diff()
    huecos = salto[salto > paso]

    return pd.DataFrame(
        {
            "desde": tiempos.shift()[huecos.index] + paso,
            "hasta": huecos.index,
            "velas_faltantes": (huecos // paso - 1).astype("int64"),
        }
    ).reset_index(drop=True)
