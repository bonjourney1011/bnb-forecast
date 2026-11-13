"""Committed CSV of daily closes: load as a wide frame, and append new closed days."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from bnbforecast import settings
from bnbforecast.fetch import binance_klines, kraken_fallback
from bnbforecast.fetch.binance_klines import COLS

FIRST_DAY = date(2017, 8, 1)


def load_long() -> pd.DataFrame:
    if not settings.MARKET_CSV.exists():
        return pd.DataFrame(columns=COLS)
    return pd.read_csv(settings.MARKET_CSV, dtype={"date": str})


def to_wide(long: pd.DataFrame) -> pd.DataFrame:
    """Wide closes on a gap-free daily index, limited to days where every symbol has a close."""
    wide = long.pivot(index="date", columns="symbol", values="close")[settings.SYMBOLS].dropna()
    wide.index = pd.to_datetime(wide.index)
    full = pd.date_range(wide.index[0], wide.index[-1], freq="D")
    missing = full.difference(wide.index)
    if len(missing):
        raise ValueError(f"{len(missing)} missing day(s) in market data, first: {missing[0].date()}")
    return wide


def load_closes() -> pd.DataFrame:
    return to_wide(load_long())


def update() -> dict[str, str]:
    """Fetch every closed day after the last stored one. Returns the source used per symbol."""
    long = load_long()
    used, frames = {}, [long]
    for symbol in settings.SYMBOLS:
        have = long.loc[long["symbol"] == symbol, "date"]
        start = date.fromisoformat(have.max()) + timedelta(days=1) if len(have) else FIRST_DAY
        try:
            new, used[symbol] = binance_klines.fetch_symbol(symbol, start), "binance"
        except Exception as e:  # geo-block, outage: fall back for recent days only
            print(f"{symbol}: binance failed ({e}); trying kraken")
            new, used[symbol] = kraken_fallback.fetch_symbol(symbol, start), "kraken"
        frames.append(new)
    merged = (
        pd.concat([f for f in frames if not f.empty], ignore_index=True)
        .drop_duplicates(["date", "symbol"], keep="first")
        .sort_values(["date", "symbol"])
    )
    to_wide(merged)  # raises on gaps before anything is written
    last = merged.groupby("symbol")["date"].max()
    if last.nunique() != 1:
        raise ValueError(f"symbols end on different days: {last.to_dict()}")
    settings.MARKET_CSV.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(settings.MARKET_CSV, index=False, lineterminator="\n")
    return used
