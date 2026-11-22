"""Descarga de velas (klines) desde la API pública de Binance.

No requiere clave de API: los datos de mercado son públicos.
Documentación: https://developers.binance.com/docs/binance-spot-api-docs/rest-api
"""

import argparse
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from btc_radar.config import RAW_DIR

BASE_URL = "https://api.binance.com"
KLINES_ENDPOINT = "/api/v3/klines"
LIMITE_POR_PETICION = 1000  # máximo que permite Binance
PAUSA_ENTRE_PETICIONES = 0.2  # segundos, para respetar el rate limit

# Inicio de BTCUSDT en Binance
INICIO_HISTORICO = "2017-08-17"

COLUMNAS_KLINES = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_volume",
    "taker_buy_quote_volume",
    "ignore",
]
COLUMNAS_PRECIO_VOLUMEN = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "taker_buy_volume",
    "taker_buy_quote_volume",
]


def crear_sesion() -> requests.Session:
    """Sesión HTTP con reintentos ante errores temporales (429, 5xx)."""
    reintentos = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        respect_retry_after_header=True,
    )
    sesion = requests.Session()
    sesion.mount("https://", HTTPAdapter(max_retries=reintentos))
    return sesion


def a_milisegundos(fecha: str | datetime) -> int:
    """Convierte una fecha (str ISO o datetime) a milisegundos UTC."""
    ts = pd.Timestamp(fecha)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return int(ts.timestamp() * 1000)


def descargar_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    inicio: str | datetime = INICIO_HISTORICO,
    fin: str | datetime | None = None,
    sesion: requests.Session | None = None,
    pausa: float = PAUSA_ENTRE_PETICIONES,
) -> list[list]:
    """Descarga todas las velas entre `inicio` y `fin`, paginando de 1000 en 1000."""
    sesion = sesion or crear_sesion()
    inicio_ms = a_milisegundos(inicio)
    fin_ms = a_milisegundos(fin) if fin is not None else None

    filas: list[list] = []
    while True:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": inicio_ms,
            "limit": LIMITE_POR_PETICION,
        }
        if fin_ms is not None:
            params["endTime"] = fin_ms

        respuesta = sesion.get(BASE_URL + KLINES_ENDPOINT, params=params, timeout=30)
        respuesta.raise_for_status()
        pagina = respuesta.json()
        if not pagina:
            break

        filas.extend(pagina)
        if len(pagina) < LIMITE_POR_PETICION:
            break

        # La siguiente página empieza justo después de la última vela recibida
        inicio_ms = pagina[-1][0] + 1
        time.sleep(pausa)

    return filas


def klines_a_dataframe(filas: list[list], solo_cerradas: bool = True) -> pd.DataFrame:
    """Convierte la respuesta cruda de Binance en un DataFrame tipado.

    Con `solo_cerradas=True` se descarta la vela en curso, que aún no es definitiva.
    """
    df = pd.DataFrame(filas, columns=COLUMNAS_KLINES).drop(columns="ignore")

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    df[COLUMNAS_PRECIO_VOLUMEN] = df[COLUMNAS_PRECIO_VOLUMEN].astype("float64")
    df["trades"] = df["trades"].astype("int64")

    if solo_cerradas:
        df = df[df["close_time"] < datetime.now(UTC)]

    return (
        df.drop_duplicates(subset="open_time")
        .sort_values("open_time")
        .reset_index(drop=True)
    )


def ruta_parquet(symbol: str, interval: str, carpeta: Path = RAW_DIR) -> Path:
    """Ruta estándar del archivo de velas: data/raw/BTCUSDT_1d.parquet."""
    return carpeta / f"{symbol}_{interval}.parquet"


def descargar_y_guardar(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    inicio: str | datetime = INICIO_HISTORICO,
    carpeta: Path = RAW_DIR,
) -> Path:
    """Descarga las velas y las guarda en Parquet. Devuelve la ruta del archivo."""
    df = klines_a_dataframe(descargar_klines(symbol, interval, inicio))
    ruta = ruta_parquet(symbol, interval, carpeta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ruta, index=False)
    return ruta


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga velas de Binance a Parquet")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--intervals", nargs="+", default=["1d", "4h"])
    parser.add_argument("--desde", default=INICIO_HISTORICO, help="AAAA-MM-DD")
    args = parser.parse_args()

    for interval in args.intervals:
        ruta = descargar_y_guardar(args.symbol, interval, args.desde)
        df = pd.read_parquet(ruta)
        print(
            f"{args.symbol} {interval}: {len(df):,} velas "
            f"({df['open_time'].min():%Y-%m-%d} → {df['open_time'].max():%Y-%m-%d}) "
            f"→ {ruta}"
        )


if __name__ == "__main__":
    main()
