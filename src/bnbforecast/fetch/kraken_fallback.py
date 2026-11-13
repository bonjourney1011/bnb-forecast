"""Fallback for the most recent days when the Binance endpoint is unreachable (for example
HTTP 451 from a CI runner). Kraken quotes in USD, not USDT; the gap is a few basis points,
and rows are tagged source=kraken so they can be told apart. Returns at most ~720 days."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

import pandas as pd

from bnbforecast.fetch import http_client
from bnbforecast.fetch.binance_klines import COLS

URL = "https://api.kraken.com/0/public/OHLC"
PAIRS = {"BNBUSDT": "BNBUSD", "BTCUSDT": "XBTUSD", "ETHUSDT": "ETHUSD"}
DAY = 86_400


def parse_ohlc(raw: dict, symbol: str, now_s: int) -> pd.DataFrame:
    if not raw or raw.get("error") or not raw.get("result"):
        return pd.DataFrame(columns=COLS)
    candles = next((v for k, v in raw["result"].items() if k != "last"), [])
    rows = [
        (datetime.fromtimestamp(int(c[0]), UTC).strftime("%Y-%m-%d"), symbol, float(c[4]), "kraken")
        for c in candles
        if int(c[0]) + DAY <= now_s  # drop the still-open candle
    ]
    return pd.DataFrame(rows, columns=COLS)


def fetch_symbol(symbol: str, start: date, now_s: int | None = None) -> pd.DataFrame:
    now_s = now_s or int(datetime.now(UTC).timestamp())
    since = int(datetime.combine(start, time(0, 0), tzinfo=UTC).timestamp()) - 1
    raw = http_client.get_json(URL, {"pair": PAIRS[symbol], "interval": 1440, "since": since})
    if not raw or raw.get("error"):
        raise RuntimeError(f"kraken error for {symbol}: {(raw or {}).get("error")}")
    df = parse_ohlc(raw, symbol, now_s)
    return df[df["date"] >= start.isoformat()].reset_index(drop=True)
