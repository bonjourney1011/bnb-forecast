"""Turn stored backtest predictions into the scoreboard shown on the site."""

from __future__ import annotations

import numpy as np
import pandas as pd

from bnbforecast import metrics, settings
from bnbforecast.backtest import load_predictions
from bnbforecast.trading_simulation import simulate

Q = settings.QUANTILES
NON_OVERLAP_STEP = 5  # weekly origins -> 35 days apart, longer than the 30-day horizon


def _arrays(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    return df["actual"].to_numpy(), df[settings.QCOLS].to_numpy()


def _score(df: pd.DataFrame, ref: pd.DataFrame) -> dict:
    """Metrics for one model at one horizon; `ref` is the random walk on the same origins."""
    actual, preds = _arrays(df)
    ref_actual, ref_preds = _arrays(ref)
    loss, ref_loss = metrics.pinball_loss(actual, preds, Q), metrics.pinball_loss(ref_actual, ref_preds, Q)
    col = {q: i for i, q in enumerate(Q)}
    return {
        "n": int(len(df)),
        "pinball": loss,
        "skill_vs_rw": 1 - loss / ref_loss,
        "mae_ratio_vs_no_change": float(np.mean(np.abs(actual - preds[:, col[0.5]])) / np.mean(np.abs(actual))),
        "coverage_80": metrics.coverage(actual, preds[:, col[0.1]], preds[:, col[0.9]]),
        "coverage_50": metrics.coverage(actual, preds[:, col[0.25]], preds[:, col[0.75]]),
        "width_80": float(np.mean(preds[:, col[0.9]] - preds[:, col[0.1]])),
    }


def _direction(df30: pd.DataFrame) -> dict:
    """30-day direction on non-overlapping origins, so the n is an honest sample size."""
    df = df30.sort_values("origin").iloc[::NON_OVERLAP_STEP]
    actual, preds = _arrays(df)
    p_up = metrics.prob_up(preds, Q)
    called = p_up != 0.5
    hits = int(np.sum((p_up[called] > 0.5) == (actual[called] > 0)))
    n = int(called.sum())
    low, high = metrics.wilson_interval(hits, n)
    return {
        "n": n,
        "accuracy": hits / n if n else None,
        "ci_low": low,
        "ci_high": high,
        "share_up_periods": float(np.mean(actual > 0)),
    }


def summarize(closes: pd.DataFrame) -> dict:
    preds = {m: load_predictions(m) for m in settings.MODELS}
    preds = {m: df for m, df in preds.items() if not df.empty}
    rw = preds["random_walk"]
    out = {"models": {}, "horizons": settings.HORIZONS, "labels": settings.MODEL_LABELS}
    for model, df in preds.items():
        ref = rw[rw["origin"].isin(df["origin"])]
        df = df[df["origin"].isin(ref["origin"])]
        by_h = {str(h): _score(df[df["h"] == h], ref[ref["h"] == h]) for h in settings.HORIZONS}
        d30, r30 = df[df["h"] == settings.MAX_HORIZON], ref[ref["h"] == settings.MAX_HORIZON]
        by_year = {
            str(y): _score(g, r30[r30["origin"].dt.year == y])["skill_vs_rw"]
            for y, g in d30.groupby(d30["origin"].dt.year)
        }
        out["models"][model] = {
            "origins": int(df["origin"].nunique()),
            "first_origin": df["origin"].min().date().isoformat(),
            "last_origin": df["origin"].max().date().isoformat(),
            "by_horizon": by_h,
            "mean_skill_vs_rw": float(np.mean([v["skill_vs_rw"] for v in by_h.values()])),
            "skill_30d_by_year": by_year,
            "direction_30d": _direction(d30),
            "trading": simulate(d30, closes),
        }
    return out
