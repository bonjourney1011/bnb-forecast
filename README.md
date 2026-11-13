# BNB 30-Day Forecast

A probabilistic forecast of the BNB price over the next 30 days, scored honestly against a random walk.

Live site: https://bonjourney1011.github.io/bnb-forecast/

## What it does

- Forecasts seven quantiles (5% to 95%) of the BNB log return at 1, 3, 7, 14, 21 and 30 days.
- Compares **TabPFN** (tabular foundation model, hosted API, two designs), **Chronos-2** (zero-shot time-series
  foundation model, CPU), **ARIMA(0,1,1)**, a **Delta-Random Forest**, and **random walk** baselines.
- Backtests every model on weekly forecast dates since January 2021, with no look-ahead.
- Logs each daily forecast and scores it once the outcome is known.

The point of the project is the scoreboard. If a model does not beat "the price stays where it is", the site says so.

## Run it

```
uv sync
uv run bnbforecast fetch                 # daily closes since 2017
uv run bnbforecast backtest random_walk  # also: random_walk_drift, arima, delta_rf, chronos2, tabpfn, tabpfn_sparse, tabpfn_calendar
uv run bnbforecast summarize             # web/data/backtest-summary.json
uv run bnbforecast daily                 # latest forecast + forecast log
uv run pytest
python -m http.server -d web 8000
```

TabPFN needs a `TABPFN_TOKEN` environment variable (Prior Labs account). Without it the other models still run.

## Layout

| Path | Role |
|---|---|
| `src/bnbforecast/fetch/` | Polite HTTP client, Binance public klines, Kraken fallback |
| `src/bnbforecast/features.py` | Origin × horizon feature table, purge rule |
| `src/bnbforecast/models/` | Random walk, Chronos-2, TabPFN |
| `src/bnbforecast/backtest.py`, `backtest_summary.py` | Rolling-origin backtest and scoreboard |
| `src/bnbforecast/daily_forecast.py` | Daily forecast, append-only log, live scoring |
| `web/` | Static site (GitHub Pages) |
| `docs/` | Methodology, data sources, runbook |

## Disclaimer

Research project, not investment advice. Data from Binance public market data and Kraken; not affiliated with or
endorsed by either.
