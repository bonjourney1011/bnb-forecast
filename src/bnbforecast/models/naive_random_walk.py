"""Naive baselines every other model has to beat.

random_walk:       median return is 0 (price stays put); the spread is the empirical spread of
                   h-day returns over the trailing window, re-centred on 0.
random_walk_drift: same, but keeps the window's own median (trend continues)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from bnbforecast import settings


def predict(log_close: pd.Series, horizons: list[int], quantiles: list[float], drift: bool) -> np.ndarray:
    """`log_close` must end at the origin. Returns (len(horizons), len(quantiles)) log returns."""
    out = np.empty((len(horizons), len(quantiles)))
    for i, h in enumerate(horizons):
        r = log_close.diff(h).dropna().tail(settings.NAIVE_WINDOW_DAYS).to_numpy()
        if not drift:
            r = r - np.median(r)
        out[i] = np.quantile(r, quantiles)
    return out
