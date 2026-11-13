"""Scoring for quantile forecasts of log returns."""

from __future__ import annotations

import math

import numpy as np


def pinball_loss(actual: np.ndarray, preds: np.ndarray, quantiles: list[float]) -> float:
    """Mean pinball (quantile) loss. `preds` is (n, len(quantiles)). Lower is better."""
    q = np.asarray(quantiles)[None, :]
    diff = actual[:, None] - preds
    return float(np.mean(np.maximum(q * diff, (q - 1) * diff)))


def coverage(actual: np.ndarray, low: np.ndarray, high: np.ndarray) -> float:
    return float(np.mean((actual >= low) & (actual <= high)))


def prob_up(preds: np.ndarray, quantiles: list[float]) -> np.ndarray:
    """P(return > 0) per row, by linear interpolation of the quantile function at 0.
    Clipped to the outermost quantile levels because the tails beyond them are unknown."""
    q = np.asarray(quantiles)
    out = np.empty(len(preds))
    for i, row in enumerate(preds):
        if np.all(np.diff(row) <= 0):  # degenerate fan
            out[i] = 0.5
            continue
        out[i] = 1.0 - np.interp(0.0, row, q, left=q[0], right=q[-1])
    return out


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (centre - half, centre + half)


def max_drawdown(equity: np.ndarray) -> float:
    peaks = np.maximum.accumulate(equity)
    return float(np.min(equity / peaks - 1))


def pinball_per_row(actual: np.ndarray, preds: np.ndarray, quantiles: list[float]) -> np.ndarray:
    q = np.asarray(quantiles)[None, :]
    diff = actual[:, None] - preds
    return np.maximum(q * diff, (q - 1) * diff).mean(axis=1)


def diebold_mariano(loss_model: np.ndarray, loss_ref: np.ndarray, lags: int) -> float:
    """Two-sided Diebold-Mariano p-value for equal expected loss. The variance uses a
    Newey-West (Bartlett) estimator with `lags` lags, because forecasts whose target windows
    overlap have autocorrelated errors. A small p-value means the two models really differ."""
    d = loss_model - loss_ref
    n, centred = len(d), d - d.mean()
    var = centred @ centred / n
    for k in range(1, min(lags, n - 1) + 1):
        var += 2 * (1 - k / (lags + 1)) * (centred[k:] @ centred[:-k]) / n
    if var <= 0:
        return 1.0
    stat = d.mean() / math.sqrt(var / n)
    return float(math.erfc(abs(stat) / math.sqrt(2)))
