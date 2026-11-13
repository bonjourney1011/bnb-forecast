"""ARIMA(0,1,1) on the log price: the classical baseline from the walk-forward robusta
study (Quang et al., JDSIS 2026), where it was the locked statistical specification.

The order is fixed, not searched, so nothing is tuned on this series. Quantiles come from
the model's Gaussian forecast distribution at each horizon."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.tsa.arima.model import ARIMA

ORDER = (0, 1, 1)
FIT_DAYS = 1024


def predict(log_close: pd.Series, horizons: list[int], quantiles: list[float]) -> np.ndarray:
    """`log_close` must end at the origin. Returns (len(horizons), len(quantiles)) log returns."""
    series = log_close.to_numpy()[-FIT_DAYS:]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        forecast = ARIMA(series, order=ORDER, trend="n").fit().get_forecast(max(horizons))
    steps = [h - 1 for h in horizons]
    mean = np.asarray(forecast.predicted_mean)[steps] - series[-1]
    se = np.asarray(forecast.se_mean)[steps]
    return mean[:, None] + se[:, None] * norm.ppf(quantiles)[None, :]
