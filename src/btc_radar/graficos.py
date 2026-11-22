"""Gráficos interactivos con Plotly (reutilizables en notebooks y en el dashboard)."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from btc_radar.volume_profile import NivelesVolumen

VERDE = "#26a69a"
ROJO = "#ef5350"
AZUL = "#42a5f5"
GRIS = "#607d8b"
NARANJA = "#ffa726"


def _trazas_velas(df: pd.DataFrame) -> tuple[go.Candlestick, go.Bar]:
    """Velas japonesas y barras de volumen coloreadas según la vela."""
    velas = go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        increasing_line_color=VERDE,
        decreasing_line_color=ROJO,
        name="Precio",
    )
    colores = np.where(df["close"] >= df["open"], VERDE, ROJO)
    volumen = go.Bar(x=df.index, y=df["volume"], marker_color=colores, name="Volumen")
    return velas, volumen


def _estilo(fig: go.Figure, titulo: str) -> None:
    fig.update_layout(
        title=titulo,
        template="plotly_dark",
        showlegend=False,
        xaxis_rangeslider_visible=False,
        height=600,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
    )
    fig.update_yaxes(title_text="USDT", row=1, col=1)
    fig.update_yaxes(title_text="BTC", row=2, col=1)


def grafico_velas(df: pd.DataFrame, titulo: str = "BTCUSDT") -> go.Figure:
    """Velas japonesas arriba y volumen abajo, con el eje temporal compartido.

    `df` debe tener índice temporal y columnas open, high, low, close, volume.
    """
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )
    velas, volumen = _trazas_velas(df)
    fig.add_trace(velas, row=1, col=1)
    fig.add_trace(volumen, row=2, col=1)
    _estilo(fig, titulo)
    return fig


def grafico_perfil_volumen(
    df: pd.DataFrame,
    perfil: pd.DataFrame,
    niveles: NivelesVolumen,
    nodos: pd.DataFrame | None = None,
    titulo: str = "BTCUSDT · perfil de volumen",
) -> go.Figure:
    """Velas + volumen a la izquierda y perfil de volumen a la derecha.

    El perfil comparte el eje de precios con las velas. Barras azules: área de
    valor; naranja: POC; gris: fuera del área de valor. POC, VAH y VAL se
    prolongan como líneas horizontales sobre las velas.
    """
    fig = make_subplots(
        rows=2,
        cols=2,
        shared_xaxes=True,
        shared_yaxes=True,
        column_widths=[0.8, 0.2],
        row_heights=[0.75, 0.25],
        horizontal_spacing=0.01,
        vertical_spacing=0.03,
        specs=[[{}, {}], [{}, None]],
    )
    velas, volumen = _trazas_velas(df)
    fig.add_trace(velas, row=1, col=1)
    fig.add_trace(volumen, row=2, col=1)

    en_area = perfil["precio"].between(niveles.val, niveles.vah)
    colores = np.where(en_area, AZUL, GRIS)
    colores[perfil["precio"].eq(niveles.poc).to_numpy()] = NARANJA
    fig.add_trace(
        go.Bar(
            x=perfil["volumen"],
            y=perfil["precio"],
            orientation="h",
            width=perfil["precio_alto"] - perfil["precio_bajo"],
            marker_color=colores,
            name="Perfil",
            hovertemplate="%{y:,.0f} USDT<br>volumen %{x:,.0f}<extra></extra>",
        ),
        row=1,
        col=2,
    )

    for nombre, precio, color in [
        ("POC", niveles.poc, NARANJA),
        ("VAH", niveles.vah, AZUL),
        ("VAL", niveles.val, AZUL),
    ]:
        fig.add_hline(
            y=precio,
            line={"color": color, "dash": "dash", "width": 1},
            annotation_text=f"{nombre} {precio:,.0f}",
            annotation_position="top left",
            row=1,
            col=1,
        )

    if nodos is not None and not nodos.empty:
        fig.add_trace(
            go.Scatter(
                x=nodos["volumen"],
                y=nodos["precio"],
                mode="markers+text",
                text=nodos["tipo"],
                textposition="middle right",
                marker={"color": "white", "size": 6},
                name="Nodos",
            ),
            row=1,
            col=2,
        )

    _estilo(fig, titulo)
    # Margen a la derecha para que quepan las etiquetas HVN/LVN
    fig.update_xaxes(
        showticklabels=False, range=[0, perfil["volumen"].max() * 1.35], row=1, col=2
    )
    return fig


def grafico_ballenas(
    velas: pd.DataFrame,
    ballenas: pd.DataFrame,
    cvds: dict[str, pd.Series],
    titulo: str = "BTCUSDT · órdenes de ballenas",
) -> go.Figure:
    """Velas con burbujas de ballenas arriba y curvas de CVD abajo.

    Burbujas: área proporcional al importe en USD; verde = compra agresiva,
    roja = venta agresiva. `cvds` mapea un nombre (p. ej. "Ballenas") a su CVD.
    """
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.03,
    )
    velas_traza, _ = _trazas_velas(velas)
    velas_traza.update(opacity=0.6)
    fig.add_trace(velas_traza, row=1, col=1)

    tamano = 40 * np.sqrt(ballenas["usd"] / ballenas["usd"].max())
    for compra, color, nombre in [(True, VERDE, "Compra"), (False, ROJO, "Venta")]:
        lado = ballenas[ballenas["compra_agresiva"] == compra]
        fig.add_trace(
            go.Scatter(
                x=lado["time"],
                y=lado["precio_medio"],
                mode="markers",
                marker={
                    "size": tamano[lado.index],
                    "color": color,
                    "opacity": 0.6,
                    "line": {"width": 0.5, "color": "white"},
                },
                name=f"Ballena · {nombre}",
                customdata=lado["usd"] / 1e6,
                hovertemplate="%{y:,.0f} USDT<br>%{customdata:.2f} M USD"
                "<extra>%{fullData.name}</extra>",
            ),
            row=1,
            col=1,
        )

    for (nombre, serie), color in zip(
        cvds.items(), [NARANJA, AZUL, GRIS], strict=False
    ):
        fig.add_trace(
            go.Scatter(
                x=serie.index,
                y=serie / 1e6,
                mode="lines",
                line={"color": color},
                name=f"CVD {nombre}",
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        title=titulo,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=650,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        legend={"orientation": "h", "y": 1.02, "x": 1, "xanchor": "right"},
    )
    fig.update_yaxes(title_text="USDT", row=1, col=1)
    fig.update_yaxes(title_text="CVD (M USD)", row=2, col=1)
    return fig
