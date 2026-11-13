"""A deliberately simple, pre-registered trading rule, shown as a secondary read only.

Every 28 days: hold BNB when the model's P(30-day return > 0) is at least the threshold,
otherwise hold cash. A fee is charged on each switch. Compared with buy-and-hold over the
same dates. One rule, no tuning: tuning it on this backtest would overstate the result."""

from __future__ import annotations

import numpy as np
import pandas as pd

from bnbforecast import metrics, settings

PERIODS_PER_YEAR = 365 / (settings.TRADE_REBALANCE_EVERY * settings.ORIGIN_STEP_DAYS)


def _stats(period_returns: np.ndarray) -> dict:
    equity = np.cumprod(1 + period_returns)
    std = period_returns.std(ddof=1)
    years = len(period_returns) / PERIODS_PER_YEAR
    return {
        "total_return": float(equity[-1] - 1),
        "annual_return": float(equity[-1] ** (1 / years) - 1),
        "sharpe": float(period_returns.mean() / std * np.sqrt(PERIODS_PER_YEAR)) if std > 0 else 0.0,
        "max_drawdown": metrics.max_drawdown(np.concatenate([[1.0], equity])),
    }


def simulate(preds_30d: pd.DataFrame, closes: pd.DataFrame) -> dict | None:
    df = preds_30d.sort_values("origin").iloc[:: settings.TRADE_REBALANCE_EVERY]
    dates = list(df["origin"])
    if len(dates) < 3:  # too few periods for any statistic (a partial, quota-limited backtest)
        return None
    price = closes[settings.TARGET]
    market = np.array([price[b] / price[a] - 1 for a, b in zip(dates[:-1], dates[1:], strict=True)])
    p_up = metrics.prob_up(df[settings.QCOLS].to_numpy(), settings.QUANTILES)[:-1]
    in_market = p_up >= settings.TRADE_P_UP_THRESHOLD

    strategy, holding = np.zeros(len(market)), False
    for i, want in enumerate(in_market):
        fee = settings.TRADE_FEE if want != holding else 0.0
        strategy[i] = (1 - fee) * (1 + market[i] if want else 1.0) - 1
        holding = bool(want)

    return {
        "periods": int(len(market)),
        "from": dates[0].date().isoformat(),
        "to": dates[-1].date().isoformat(),
        "share_in_market": float(in_market.mean()),
        "switches": int(np.sum(np.diff(np.concatenate([[False], in_market]).astype(int)) != 0)),
        "strategy": _stats(strategy),
        "buy_and_hold": _stats(market),
        "equity_dates": [d.date().isoformat() for d in dates],
        "equity_strategy": [1.0, *np.cumprod(1 + strategy).round(4).tolist()],
        "equity_buy_and_hold": [1.0, *np.cumprod(1 + market).round(4).tolist()],
    }
