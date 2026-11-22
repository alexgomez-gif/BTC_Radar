"""Perfil de volumen: cuánto se negoció en cada nivel de precio.

- POC (Point of Control): nivel con más volumen.
- Área de valor (VAL-VAH): rango alrededor del POC con el 70 % del volumen.
- HVN / LVN: nodos de alto y bajo volumen (zonas de aceptación y de rechazo).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.signal import find_peaks


@dataclass(frozen=True)
class NivelesVolumen:
    poc: float
    vah: float
    val: float


def perfil_volumen(
    df: pd.DataFrame, n_niveles: int = 100, en_usd: bool = False
) -> pd.DataFrame:
    """Reparte el volumen de cada vela entre los niveles de precio que recorrió.

    Las velas no dicen a qué precio exacto se negoció cada unidad, así que se
    asume un reparto uniforme entre `low` y `high`. El volumen comprador
    (`taker_buy_volume`) se reparte igual para obtener compras y ventas por nivel.

    Con `en_usd=True` se usa el volumen en USDT (`quote_volume`). Es lo correcto
    en periodos largos: en BTC, los años de precio bajo pesan artificialmente más.
    """
    bajo = df["low"].to_numpy()
    alto = df["high"].to_numpy()
    bordes = np.linspace(bajo.min(), alto.max(), n_niveles + 1)
    inf, sup = bordes[:-1], bordes[1:]

    # Matriz velas × niveles: fracción del rango de cada vela que cae en cada nivel
    solape = np.minimum(alto[:, None], sup) - np.maximum(bajo[:, None], inf)
    solape = np.clip(solape, 0, None)
    rango = (alto - bajo)[:, None]
    peso = np.divide(solape, rango, out=np.zeros_like(solape), where=rango > 0)

    # Velas sin recorrido (high == low): todo su volumen va al nivel de su precio
    planas = np.flatnonzero(rango[:, 0] == 0)
    if planas.size:
        nivel = np.searchsorted(bordes, bajo[planas], side="right") - 1
        peso[planas, np.clip(nivel, 0, n_niveles - 1)] = 1

    col_vol, col_compra = (
        ("quote_volume", "taker_buy_quote_volume")
        if en_usd
        else ("volume", "taker_buy_volume")
    )
    volumen = peso.T @ df[col_vol].to_numpy()
    compra = peso.T @ df[col_compra].to_numpy()

    return pd.DataFrame(
        {
            "precio_bajo": inf,
            "precio_alto": sup,
            "precio": (inf + sup) / 2,
            "volumen": volumen,
            "volumen_compra": compra,
            "volumen_venta": volumen - compra,
        }
    )


def area_de_valor(perfil: pd.DataFrame, porcentaje: float = 0.70) -> NivelesVolumen:
    """POC, VAH y VAL con el método clásico de Market Profile.

    Desde el POC se añade cada vez el nivel vecino (arriba o abajo) con más
    volumen, hasta acumular `porcentaje` del volumen total.
    """
    vol = perfil["volumen"].to_numpy()
    i_poc = int(vol.argmax())
    abajo_i = arriba_i = i_poc
    acumulado = vol[i_poc]
    objetivo = porcentaje * vol.sum()

    while acumulado < objetivo:
        abajo = vol[abajo_i - 1] if abajo_i > 0 else -1.0
        arriba = vol[arriba_i + 1] if arriba_i < len(vol) - 1 else -1.0
        if arriba >= abajo:
            arriba_i += 1
            acumulado += arriba
        else:
            abajo_i -= 1
            acumulado += abajo

    return NivelesVolumen(
        poc=float(perfil["precio"].iloc[i_poc]),
        vah=float(perfil["precio_alto"].iloc[arriba_i]),
        val=float(perfil["precio_bajo"].iloc[abajo_i]),
    )


def nodos_volumen(
    perfil: pd.DataFrame, prominencia: float = 0.10, suavizado: int = 3
) -> pd.DataFrame:
    """Detecta HVN (picos) y LVN (valles) del perfil.

    `prominencia` es la fracción del volumen máximo que debe sobresalir un pico
    o valle respecto a su entorno; `suavizado` es la ventana de media móvil
    que elimina el ruido entre niveles contiguos.
    """
    vol = (
        perfil["volumen"].rolling(suavizado, center=True, min_periods=1).mean()
    ).to_numpy()
    umbral = prominencia * vol.max()
    picos, _ = find_peaks(vol, prominence=umbral)
    valles, _ = find_peaks(-vol, prominence=umbral)

    nodos = pd.concat(
        [
            perfil.iloc[picos][["precio", "volumen"]].assign(tipo="HVN"),
            perfil.iloc[valles][["precio", "volumen"]].assign(tipo="LVN"),
        ]
    )
    return nodos.sort_values("precio").reset_index(drop=True)
