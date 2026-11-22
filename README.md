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
- [x] **2. Exploration** — returns, volatility, volume, first candlestick chart
- [x] **3. Volume profile** — POC, VAH, VAL
- [x] **4. Whales** — large trades, buy/sell aggressor, CVD
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

Download tick data (aggregated trades) for the last N full days to
`data/raw/aggTrades/` (~20 MB per day, verified against Binance's SHA-256):

```bash
btc-trades --dias 7
```

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
| [data.binance.vision](https://data.binance.vision) daily `aggTrades` | Aggregated trades with aggressor side | `data/raw/aggTrades/` | On demand (`btc-trades`) |

Data is not versioned; scripts in `src/btc_radar/` regenerate it.

## Results

### Exploration — [`notebooks/01_exploracion.ipynb`](notebooks/01_exploracion.ipynb)

| Finding | Value |
|---|---|
| Data quality | No nulls or duplicates; 16 missing 4h candles (2018-2020 exchange outages), documented, not imputed |
| Fat tails | Excess kurtosis ≈ 16; 56 days beyond 3σ vs ≈ 9 expected under normality |
| Volatility | Annualized 30d vol fell from ~100% (2017) to ~40% (2025-26) |
| Max drawdown | −83% (Dec 2018) |
| Aggressive buy ratio | Correlates with same-day return (0.29) but not with next-day return (0.02) |

Takeaway: risk must be measured on real (fat-tailed) data, and order flow is
descriptive rather than predictive on its own — it will be used within the
Wyckoff context.

### Volume profile — [`notebooks/02_perfil_volumen.ipynb`](notebooks/02_perfil_volumen.ipynb)

| Finding | Value |
|---|---|
| Last 180 days (4h) | POC ≈ 64,000 (Jun–Aug range); value area 57.4k–78.4k; low-volume node ≈ 70k |
| Delta by level | Aggressive selling dominated around the POC (60–66k), aggressive buying at 72–79k |
| Measurement unit | Long-horizon profiles must use USD volume; BTC volume over-weights cheap years |
| "POC as magnet" test | Price revisits the prior POC as often as an equal-distance control level (weekly 72.7% vs 72.7%; monthly p = 0.77) — no magnet effect |

Takeaway: volume levels are used as context; whether they act as support or
resistance is left to the backtest rather than assumed.

### Whales & order flow — [`notebooks/03_ballenas.ipynb`](notebooks/03_ballenas.ipynb)

7 days of tick data (15–21 Nov 2026): 9.9M aggregated trades, SHA-256 verified,
no missing IDs and an exact match with candle volume.

| Finding | Value |
|---|---|
| Trades → orders | Re-joining aggTrades that share timestamp and side: 9.9M → 5.1M orders; largest order 6.8M USD sweeping 370 price levels |
| Concentration | Top 0.1% of orders = 18% of USD volume; top 1% = 45% |
| Flow by size (price −6%, low 55.1k) | Orders < 1k USD net **sold** (−23% of their volume); orders > 1M USD net **bought** (+7%) — absorption |
| Predictive power | Whale delta tracks the same-hour return (ρ = 0.31) but not the next hour (ρ = −0.03, p = 0.72) |

Takeaway: big money absorbed retail selling during the drop, but following
whale flow alone gives no obvious 1-hour edge.

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
