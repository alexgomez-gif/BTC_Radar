"""Gráficos interactivos con Plotly (reutilizables en notebooks y en el dashboard)."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

VERDE = "#26a69a"
ROJO = "#ef5350"


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
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            increasing_line_color=VERDE,
            decreasing_line_color=ROJO,
            name="Precio",
        ),
        row=1,
        col=1,
    )
    colores = np.where(df["close"] >= df["open"], VERDE, ROJO)
    fig.add_trace(
        go.Bar(x=df.index, y=df["volume"], marker_color=colores, name="Volumen"),
        row=2,
        col=1,
    )
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
    return fig
