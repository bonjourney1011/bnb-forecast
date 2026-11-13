# Data sources

| Data | Source | Endpoint | Key | Notes |
|---|---|---|---|---|
| BNB, BTC, ETH daily close (USDT) | Binance public market data | `https://data-api.binance.vision/api/v3/klines` | none | Primary. History from 2017. Only closed candles are stored. |
| Same, recent days only | Kraken public OHLC | `https://api.kraken.com/0/public/OHLC` | none | Fallback when Binance is unreachable. USD quote; rows tagged `source=kraken`. At most ~720 days. |

Checked 13 Nov 2026: `data-api.binance.vision/robots.txt` returns 404 (no restrictions published).

## Rules

- Every request goes through `src/bnbforecast/fetch/http_client.py`: generic user agent with no personal details,
  robots.txt is a hard stop, at least one second between requests to a host, three retries.
- Binance is allowed **in this repository only**. It remains on the banned list of the personal-finance repository.
- Not used: vnstock, Yahoo Finance, CoinGecko, Binance bulk dumps (`data.binance.vision` files are non-commercial
  since 30 Sep 2026), the `python-binance` package.
- Attribution on the site: "Daily closes: Binance public market data, with Kraken as fallback. Not affiliated with or
  endorsed by either."

## Model services

| Service | Use | Terms to respect |
|---|---|---|
| Prior Labs TabPFN API | Quantile regression | Free tier 5M tokens/day; token in `TABPFN_TOKEN` only; telemetry disabled; Acceptable Use Policy still to be read before relying on it |
| Hugging Face Hub | Download `amazon/chronos-2` weights (Apache-2.0) | Anonymous download, cached in CI |

## Not yet used (candidates if the backtest calls for them)

Fear & Greed index (alternative.me, attribution required), DefiLlama BSC metrics, funding rates. Each needs a terms
and robots.txt check first, and must be knowable at the forecast day.
