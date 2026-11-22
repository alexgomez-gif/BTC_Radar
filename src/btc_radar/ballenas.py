"""Flujo de órdenes: de aggTrades a órdenes, ballenas y CVD.

Una orden agresiva grande que barre varios niveles de precio aparece como
varios aggTrades (uno por nivel) con el mismo instante y el mismo lado. Para
medir el tamaño real de cada orden hay que volver a unirlos.
"""

import numpy as np
import pandas as pd

CORTES_USD = [0, 1e3, 1e4, 1e5, 1e6, np.inf]
ETIQUETAS_USD = ["<1k", "1k-10k", "10k-100k", "100k-1M", ">1M"]


def agrupar_ordenes(trades: pd.DataFrame) -> pd.DataFrame:
    """Une los aggTrades consecutivos con el mismo `time` y el mismo lado.

    Devuelve una fila por orden con su precio medio ponderado (VWAP), el rango
    de precios que barrió, la cantidad en BTC, el importe en USD, el lado y el
    número de niveles de precio que consumió.
    """
    usd = trades["price"] * trades["quantity"]
    nueva = (trades["time"] != trades["time"].shift()) | (
        trades["compra_agresiva"] != trades["compra_agresiva"].shift()
    )
    orden = nueva.cumsum().to_numpy()

    ordenes = (
        trades.assign(usd=usd, orden=orden)
        .groupby("orden", sort=False)
        .agg(
            time=("time", "first"),
            precio_min=("price", "min"),
            precio_max=("price", "max"),
            cantidad=("quantity", "sum"),
            usd=("usd", "sum"),
            compra_agresiva=("compra_agresiva", "first"),
            niveles=("price", "size"),
        )
        .reset_index(drop=True)
    )
    ordenes.insert(1, "precio_medio", ordenes["usd"] / ordenes["cantidad"])
    return ordenes


def delta_usd(ordenes: pd.DataFrame) -> pd.Series:
    """Importe con signo: + compra agresiva, − venta agresiva."""
    return ordenes["usd"].where(ordenes["compra_agresiva"], -ordenes["usd"])


def umbral_ballena(ordenes: pd.DataFrame, percentil: float = 0.999) -> float:
    """Tamaño en USD a partir del cual una orden se considera de ballena."""
    return float(ordenes["usd"].quantile(percentil))


def detectar_ballenas(
    ordenes: pd.DataFrame,
    percentil: float = 0.999,
    umbral_usd: float | None = None,
) -> pd.DataFrame:
    """Órdenes por encima del umbral (fijo en USD o, si no se da, por percentil)."""
    umbral = (
        umbral_usd if umbral_usd is not None else umbral_ballena(ordenes, percentil)
    )
    return ordenes[ordenes["usd"] >= umbral].reset_index(drop=True)


def flujo_por_tamano(
    ordenes: pd.DataFrame,
    cortes: list[float] = CORTES_USD,
    etiquetas: list[str] = ETIQUETAS_USD,
) -> pd.DataFrame:
    """Volumen y delta por tamaño de orden.

    `delta_pct` es el delta sobre el volumen del grupo: +100 % si todo fue compra
    agresiva, −100 % si todo fue venta agresiva.
    """
    tamano = pd.cut(ordenes["usd"], cortes, labels=etiquetas, right=False)
    tabla = (
        ordenes.assign(delta=delta_usd(ordenes))
        .groupby(tamano, observed=False)
        .agg(
            ordenes=("usd", "size"),
            volumen_usd=("usd", "sum"),
            delta_usd=("delta", "sum"),
        )
    )
    tabla["volumen_pct"] = tabla["volumen_usd"] / tabla["volumen_usd"].sum()
    tabla["delta_pct"] = tabla["delta_usd"] / tabla["volumen_usd"]
    tabla.index.name = "tamano"
    return tabla


def flujo_por_periodo(
    ordenes: pd.DataFrame,
    frecuencia: str = "W",
    cortes: tuple[float, ...] = (0, 1e4, 1e6, np.inf),
    etiquetas: tuple[str, ...] = ("<10k", "10k-1M", ">1M"),
) -> pd.DataFrame:
    """Delta sobre volumen (tanto por uno) por periodo y por tamaño de orden.

    Permite ver si los grupos cambian de comportamiento con el tiempo, p. ej.
    ballenas vendiendo mientras los minoristas compran.
    """
    datos = pd.DataFrame(
        {
            "periodo": ordenes["time"].dt.tz_localize(None).dt.to_period(frecuencia),
            "tamano": pd.cut(
                ordenes["usd"], list(cortes), labels=list(etiquetas), right=False
            ),
            "delta": delta_usd(ordenes),
            "usd": ordenes["usd"],
        }
    )
    suma = datos.pivot_table(
        index="periodo",
        columns="tamano",
        values=["delta", "usd"],
        aggfunc="sum",
        observed=False,
        fill_value=0,
    )
    return suma["delta"] / suma["usd"].replace(0, np.nan)


def cvd(ordenes: pd.DataFrame, frecuencia: str = "1h") -> pd.Series:
    """Cumulative Volume Delta en USD, muestreado cada `frecuencia`."""
    delta = delta_usd(ordenes).set_axis(ordenes["time"])
    return delta.resample(frecuencia).sum().cumsum().rename("cvd_usd")


def velas_desde_trades(trades: pd.DataFrame, frecuencia: str = "1h") -> pd.DataFrame:
    """Construye velas OHLCV (con taker_buy_volume) a partir de las operaciones."""
    t = trades.set_index("time")
    velas = t["price"].resample(frecuencia).ohlc()
    velas["volume"] = t["quantity"].resample(frecuencia).sum()
    velas["taker_buy_volume"] = (
        t["quantity"].where(t["compra_agresiva"], 0.0).resample(frecuencia).sum()
    )
    velas.index.name = "open_time"
    return velas.dropna(subset=["open"])
