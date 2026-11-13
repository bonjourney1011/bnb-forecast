"""Paths and the fixed forecasting design. These constants were chosen before any backtest
result was seen; changing them afterwards must be logged in docs/methodology.md."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKET_CSV = ROOT / "data" / "market" / "daily-close.csv"
BACKTEST_DIR = ROOT / "data" / "backtest"
FORECAST_LOG_CSV = ROOT / "data" / "forecast-log.csv"
WEB_DATA = ROOT / "web" / "data"

TARGET = "BNBUSDT"
SYMBOLS = ["BNBUSDT", "BTCUSDT", "ETHUSDT"]

HORIZONS = [1, 3, 7, 14, 21, 30]  # days ahead
QUANTILES = [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
MAX_HORIZON = max(HORIZONS)

BACKTEST_START = "2021-01-03"
ORIGIN_STEP_DAYS = 7
NAIVE_WINDOW_DAYS = 730

# Trading rule (secondary display only), fixed up front.
TRADE_P_UP_THRESHOLD = 0.55
TRADE_REBALANCE_EVERY = 4  # weekly origins -> every 28 days
TRADE_FEE = 0.001  # per side

MODELS = ["random_walk", "random_walk_drift", "chronos2", "tabpfn"]
# Headline model on the site and in the live track record. Fixed here, not chosen per day,
# and only changed after a model has a complete backtest (log the change in methodology.md).
PRIMARY_MODEL = "chronos2"

MODEL_LABELS = {
    "random_walk": "Random walk (no change)",
    "random_walk_drift": "Random walk with drift",
    "chronos2": "Chronos-2 (zero-shot)",
    "tabpfn": "TabPFN (tabular regression)",
}


def qcol(q: float) -> str:
    return f"q{q:g}"


QCOLS = [qcol(q) for q in QUANTILES]
