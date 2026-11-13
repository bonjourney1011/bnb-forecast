"""Daily candles from Binance's public market-data-only endpoint (no API key).
Only candles that have already closed are kept, so a forecast never sees a partial day."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

import pandas as pd

from bnbforecast.fetch import http_client

URL = "https://data-api.binance.vision/api/v3/klines"
LIMIT = 1000
COLS = ["date", "symbol", "close", "source"]


def _ms(d: date) -> int:
    return int(datetime.combine(d, time(0, 0), tzinfo=UTC).timestamp() * 1000)


def parse_klines(raw: list, symbol: str, now_ms: int) -> pd.DataFrame:
    """Kline rows -> [date, symbol, close, source]. Row layout: [openTime, o, h, l, c, v, closeTime, ...]."""
    rows = [
        (datetime.fromtimestamp(k[0] / 1000, UTC).strftime("%Y-%m-%d"), symbol, float(k[4]), "binance")
        for k in raw or []
        if int(k[6]) < now_ms
    ]
    return pd.DataFrame(rows, columns=COLS)


def fetch_symbol(symbol: str, start: date, now_ms: int | None = None) -> pd.DataFrame:
    now_ms = now_ms or int(datetime.now(UTC).timestamp() * 1000)
    frames, cursor = [], _ms(start)
    while cursor < now_ms:
        params = {"symbol": symbol, "interval": "1d", "startTime": cursor, "limit": LIMIT}
        raw = http_client.get_json(URL, params)
        if not raw:
            break
        frames.append(parse_klines(raw, symbol, now_ms))
        if len(raw) < LIMIT:
            break
        cursor = int(raw[-1][0]) + 86_400_000
    if not frames:
        return pd.DataFrame(columns=COLS)
    return pd.concat(frames, ignore_index=True).drop_duplicates(["date", "symbol"], keep="last")
