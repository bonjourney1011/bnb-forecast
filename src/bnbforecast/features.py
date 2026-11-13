"""Feature table for the "origin x horizon" design.

A row is (origin day t, horizon h). Every feature uses closes up to and including t only.
The target is the log return from t to t+h. When forecasting at origin T, the context is
restricted to rows whose target date is <= T (purge), so no future outcome can leak in."""

from __future__ import annotations

import numpy as np
import pandas as pd

from bnbforecast import settings

BURN_MONTHS = (1, 4, 7, 10)
BURN_DAY = 15
FEATURES = [
    "ret_1", "ret_7", "ret_30", "ret_90",
    "vol_7", "vol_30", "vol_90",
    "drawdown_365",
    "btc_ret_7", "btc_ret_30", "eth_ret_7", "eth_ret_30",
    "days_to_burn",
    "h",
]  # fmt: skip
# Second design (added after the first TabPFN backtest, see methodology section 7).
CALENDAR = ["day_of_week", "day_of_month", "month", "target_day_of_week"]
FEATURES_CALENDAR = FEATURES + CALENDAR


def days_to_next_burn(index: pd.DatetimeIndex) -> np.ndarray:
    """Days until the next nominal quarterly BNB burn (15 Jan/Apr/Jul/Oct). The nominal
    schedule is what is known in advance; actual burns land within a few days of it."""
    out = []
    for d in index:
        candidates = [pd.Timestamp(y, m, BURN_DAY) for y in (d.year, d.year + 1) for m in BURN_MONTHS]
        out.append(min((c - d).days for c in candidates if c >= d))
    return np.array(out)


def build_features(closes: pd.DataFrame) -> pd.DataFrame:
    """Per-day features. Rolling windows look backwards only."""
    lc = np.log(closes)
    bnb, daily = lc[settings.TARGET], lc[settings.TARGET].diff()
    f = pd.DataFrame(index=closes.index)
    for n in (1, 7, 30, 90):
        f[f"ret_{n}"] = bnb.diff(n)
    for n in (7, 30, 90):
        f[f"vol_{n}"] = daily.rolling(n).std()
    f["drawdown_365"] = bnb - bnb.rolling(365).max()
    for name, sym in (("btc", "BTCUSDT"), ("eth", "ETHUSDT")):
        for n in (7, 30):
            f[f"{name}_ret_{n}"] = lc[sym].diff(n)
    f["days_to_burn"] = days_to_next_burn(closes.index)
    f["day_of_week"] = closes.index.dayofweek
    f["day_of_month"] = closes.index.day
    f["month"] = closes.index.month
    return f.dropna()


def build_table(closes: pd.DataFrame, horizons: list[int] | None = None) -> pd.DataFrame:
    """Long table: one row per (t, h) with features, target `y` and `target_date`.
    `y` is NaN where t+h is beyond the data (those rows are queries, never context)."""
    horizons = horizons or settings.HORIZONS
    feats, bnb = build_features(closes), np.log(closes[settings.TARGET])
    parts = []
    for h in horizons:
        part = feats.copy()
        part["h"] = h
        part["y"] = (bnb.shift(-h) - bnb).reindex(part.index)
        part["target_date"] = part.index + pd.Timedelta(days=h)
        part["target_day_of_week"] = part["target_date"].dt.dayofweek
        parts.append(part)
    table = pd.concat(parts).rename_axis("t").reset_index()
    return table.sort_values(["t", "h"], ignore_index=True)


def context_rows(table: pd.DataFrame, origin: pd.Timestamp, sparse: bool = False) -> pd.DataFrame:
    """Rows usable as context at `origin`: outcome already observed on or before the origin.

    `sparse` keeps, for each horizon h, only rows spaced h days apart (counted back from the
    origin), so their target windows do not overlap. Daily rows with overlapping 30-day
    targets are near-duplicates and made the first TabPFN design overconfident."""
    ctx = table[(table["target_date"] <= origin) & table["y"].notna()]
    if sparse:
        ctx = ctx[(origin - ctx["target_date"]).dt.days % ctx["h"] == 0]
    return ctx


def query_rows(table: pd.DataFrame, origin: pd.Timestamp) -> pd.DataFrame:
    return table[table["t"] == origin].sort_values("h")
