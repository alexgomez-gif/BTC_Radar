# BTC_Radar

> Bitcoin market analysis with Binance data: Wyckoff phase detection, whale volume
> tracking and backtested entry signals — built as a data analysis portfolio project.

🇪🇸 [Resumen en español](#resumen-en-español)

## Goal

Can the Wyckoff method be turned into measurable rules, and do the entries it
suggests hold up on historical BTC/USDT data?

The project:

1. Downloads BTC/USDT market data from the public Binance API (no API key needed).
2. Detects trading ranges and Wyckoff events (Selling Climax, Spring, Sign of
   Strength, Last Point of Support… and their distribution counterparts).
3. Locates where large volume concentrates ("whales"): volume profile
   (POC / VAH / VAL), large aggressive trades and cumulative volume delta.
4. Backtests the candidate entries (win rate, risk/reward, drawdown).
5. Presents everything in an interactive dashboard (Streamlit + Plotly).

> ⚠️ Educational and analytical project. Nothing here is financial advice.

## Roadmap

- [x] **0. Setup** — repository structure, virtual environment, CI
- [x] **1. Data** — download BTCUSDT candles (1d, 4h) to Parquet
- [ ] **2. Exploration** — returns, volatility, volume, first candlestick chart
- [ ] **3. Volume profile** — POC, VAH, VAL
- [ ] **4. Whales** — large trades, buy/sell aggressor, CVD
- [ ] **5. Wyckoff v1** — rule-based range and event detection
- [ ] **6. Signals + backtest** — entries, stops, targets and metrics
- [ ] **7. Dashboard** — Streamlit app
- [ ] **8. Portfolio polish** — screenshots, live demo, scheduled data refresh

## Repository structure

```
.
├── data/             # raw / interim / processed (not versioned)
├── notebooks/        # step-by-step analysis (NN_description.ipynb)
├── src/btc_radar/    # reusable code: data client, indicators, Wyckoff, backtest
├── sql/              # DuckDB queries
├── reports/figures/  # generated charts
├── tests/            # pytest
└── .github/          # CI: ruff + pytest on every push
```

## Installation

Requires Python 3.12 and Git.

```bash
git clone https://github.com/alexgomez-gif/BTC_Radar.git
cd BTC_Radar
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Usage

Download BTCUSDT candles (1d and 4h, full history since 2017-08-17) to `data/raw/`:

```bash
btc-descargar                                  # defaults: BTCUSDT, 1d + 4h
btc-descargar --intervals 1h --desde 2024-01-01
```

```python
import pandas as pd

df = pd.read_parquet("data/raw/BTCUSDT_1d.parquet")
```

Only closed candles are stored; the in-progress candle is dropped.

## Code quality

```bash
ruff check .     # lint
ruff format .    # format
pytest           # tests
```

## Data

| Source | Description | Location | Refresh |
|--------|-------------|----------|---------|
| Binance `GET /api/v3/klines` | BTCUSDT OHLCV candles | `data/raw/` | On demand |
| Binance `GET /api/v3/aggTrades` | Aggregated trades with aggressor side | `data/raw/` | On demand |

Data is not versioned; scripts in `src/btc_radar/` regenerate it.

## Results

_Coming soon._

## Resumen en español

Proyecto de análisis de datos sobre Bitcoin con la API pública de Binance:
detección de fases Wyckoff, localización de volumen de ballenas (perfil de
volumen, operaciones grandes, CVD) y backtest de las entradas candidatas, todo
presentado en un dashboard interactivo. Proyecto educativo, no es asesoría
financiera.

## Author

Alex Gómez — [github.com/alexgomez-gif](https://github.com/alexgomez-gif)

## License

[MIT](LICENSE)
