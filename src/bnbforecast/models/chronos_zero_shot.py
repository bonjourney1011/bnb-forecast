"""Chronos-2 (Apache-2.0) as a zero-shot challenger, on CPU.

It forecasts the log-price path 30 steps ahead; the quantiles at each horizon are converted
to log returns relative to the origin. Caveat: Chronos-2 was pretrained on public time
series, so backtest scores on older periods may flatter it."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

MODEL_ID = "amazon/chronos-2"
CONTEXT_DAYS = 1024


@lru_cache(maxsize=1)
def _pipeline():
    from chronos import Chronos2Pipeline

    return Chronos2Pipeline.from_pretrained(MODEL_ID, device_map="cpu")


def predict(log_close: pd.Series, horizons: list[int], quantiles: list[float]) -> np.ndarray:
    """`log_close` must end at the origin. Returns (len(horizons), len(quantiles)) log returns."""
    context = log_close.to_numpy(dtype=np.float32)[-CONTEXT_DAYS:]
    q_list, _ = _pipeline().predict_quantiles(
        [context], prediction_length=max(horizons), quantile_levels=list(quantiles)
    )
    path = np.asarray(q_list[0]).reshape(max(horizons), len(quantiles))  # (step, quantile)
    steps = [h - 1 for h in horizons]
    return np.sort(path[steps] - float(log_close.iloc[-1]), axis=1)
