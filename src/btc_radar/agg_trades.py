"""Descarga de operaciones agregadas (aggTrades) desde data.binance.vision.

Un aggTrade agrupa las ejecuciones de una misma orden agresiva (taker) al mismo
precio y en el mismo instante. Binance publica un ZIP diario por par con un
archivo .CHECKSUM (SHA-256) para verificar la descarga.
"""

import argparse
import hashlib
import io
import zipfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

from btc_radar.binance_client import crear_sesion
from btc_radar.config import RAW_DIR

URL_BASE = "https://data.binance.vision/data/spot/daily/aggTrades"
CARPETA = RAW_DIR / "aggTrades"

COLUMNAS_CSV = [
    "agg_trade_id",
    "price",
    "quantity",
    "first_trade_id",
    "last_trade_id",
    "time",
    "is_buyer_maker",
    "is_best_match",
]


def url_dia(fecha: date, symbol: str = "BTCUSDT") -> str:
    return f"{URL_BASE}/{symbol}/{symbol}-aggTrades-{fecha:%Y-%m-%d}.zip"


def ruta_dia(fecha: date, symbol: str = "BTCUSDT", carpeta: Path = CARPETA) -> Path:
    return carpeta / f"{symbol}-aggTrades-{fecha:%Y-%m-%d}.parquet"


def verificar_checksum(contenido: bytes, texto_checksum: str) -> None:
    """Compara el SHA-256 del ZIP con el publicado en el archivo .CHECKSUM."""
    esperado = texto_checksum.split()[0].lower()
    obtenido = hashlib.sha256(contenido).hexdigest()
    if obtenido != esperado:
        raise ValueError(f"Checksum incorrecto: {obtenido} != {esperado}")


def leer_zip(contenido: bytes) -> pd.DataFrame:
    """Lee el CSV del ZIP y lo convierte a un DataFrame tipado y compacto.

    - `time` llega en microsegundos (archivos desde 2025) o milisegundos.
    - `is_buyer_maker=True` significa que el comprador era el pasivo, es decir,
      la orden agresiva fue una **venta**. Se guarda el inverso, más intuitivo:
      `compra_agresiva`.
    """
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        nombre = z.namelist()[0]
        with z.open(nombre) as f:
            primera = f.readline().decode()
        tiene_cabecera = not primera.split(",")[0].strip().isdigit()
        with z.open(nombre) as f:
            df = pd.read_csv(
                f,
                header=0 if tiene_cabecera else None,
                names=COLUMNAS_CSV,
                dtype={"is_buyer_maker": "string", "is_best_match": "string"},
            )

    unidad = "us" if df["time"].iloc[0] > 10**14 else "ms"
    return pd.DataFrame(
        {
            "agg_trade_id": df["agg_trade_id"].astype("int64"),
            "time": pd.to_datetime(df["time"], unit=unidad, utc=True),
            "price": df["price"].astype("float64"),
            "quantity": df["quantity"].astype("float64"),
            "n_trades": (df["last_trade_id"] - df["first_trade_id"] + 1).astype(
                "int64"
            ),
            "compra_agresiva": (
                df["is_buyer_maker"].str.lower().eq("false").to_numpy(dtype=bool)
            ),
        }
    )


def descargar_dia(
    fecha: date,
    symbol: str = "BTCUSDT",
    carpeta: Path = CARPETA,
    sesion: requests.Session | None = None,
) -> Path:
    """Descarga, verifica y guarda en Parquet un día. Si ya existe, no descarga."""
    ruta = ruta_dia(fecha, symbol, carpeta)
    if ruta.exists():
        return ruta

    sesion = sesion or crear_sesion()
    url = url_dia(fecha, symbol)
    respuesta = sesion.get(url, timeout=120)
    respuesta.raise_for_status()
    checksum = sesion.get(url + ".CHECKSUM", timeout=30)
    checksum.raise_for_status()
    verificar_checksum(respuesta.content, checksum.text)

    ruta.parent.mkdir(parents=True, exist_ok=True)
    leer_zip(respuesta.content).to_parquet(ruta, index=False)
    return ruta


def ultimos_dias(dias: int, hasta: date | None = None) -> list[date]:
    """Los `dias` días completos anteriores a `hasta` (por defecto, hoy en UTC)."""
    hasta = hasta or datetime.now(UTC).date()
    return [hasta - timedelta(days=i) for i in range(dias, 0, -1)]


def cargar_trades(
    fechas: list[date], symbol: str = "BTCUSDT", carpeta: Path = CARPETA
) -> pd.DataFrame:
    """Une los Parquet diarios en un solo DataFrame ordenado por `agg_trade_id`."""
    faltan = [f for f in fechas if not ruta_dia(f, symbol, carpeta).exists()]
    if faltan:
        raise FileNotFoundError(
            f"Faltan {len(faltan)} días (p. ej. {faltan[0]}). Ejecuta: btc-trades"
        )
    partes = [pd.read_parquet(ruta_dia(f, symbol, carpeta)) for f in fechas]
    return pd.concat(partes, ignore_index=True).sort_values("agg_trade_id")


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga aggTrades diarios")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--dias", type=int, default=7)
    args = parser.parse_args()

    sesion = crear_sesion()
    for fecha in ultimos_dias(args.dias):
        try:
            ruta = descargar_dia(fecha, args.symbol, sesion=sesion)
        except requests.HTTPError as error:
            # El archivo del día anterior se publica unas horas después de medianoche
            print(f"{fecha}: no disponible ({error.response.status_code})")
            continue
        filas = pd.read_parquet(ruta, columns=["agg_trade_id"]).shape[0]
        print(f"{fecha}: {filas:,} aggTrades → {ruta.name}")


if __name__ == "__main__":
    main()
