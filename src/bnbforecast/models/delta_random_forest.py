"""Delta-Random Forest, after the best-MAE model of the walk-forward robusta study
(Quang et al., JDSIS 2026): predict the change, not the level, from a 60-step lookback of
past changes. Hyperparameters are the paper's locked ones (300 trees, depth 8, leaf 3).

Adapted here in two ways: one direct model per horizon (target = h-day log return), and
quantiles read from the forest as a quantile regression forest (Meinshausen 2006): the
training targets that share a leaf with the query, weighted per tree."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

LOOKBACK = 60
PARAMS = {"n_estimators": 300, "max_depth": 8, "min_samples_leaf": 3, "max_features": "sqrt", "random_state": 42}


def _lag_matrix(log_closes: pd.DataFrame) -> pd.DataFrame:
    """Row t holds the last LOOKBACK daily log returns of every symbol, up to and including t."""
    daily = log_closes.diff()
    lags = {f"{sym}_lag{k}": daily[sym].shift(k) for sym in daily.columns for k in range(LOOKBACK)}
    return pd.DataFrame(lags, index=daily.index).dropna()


def _forest_quantiles(model, x_train, y_train, x_query, quantiles) -> np.ndarray:
    same_leaf = model.apply(x_train) == model.apply(x_query)  # (n_train, n_trees)
    weights = (same_leaf / same_leaf.sum(axis=0)).mean(axis=1)
    order = np.argsort(y_train)
    return np.interp(quantiles, np.cumsum(weights[order]), y_train[order])


def predict(log_closes: pd.DataFrame, horizons: list[int], quantiles: list[float], target: str = "BNBUSDT"):
    """`log_closes` (all symbols) must end at the origin. Returns (len(horizons), len(quantiles))."""
    x_all = _lag_matrix(log_closes)
    price = log_closes[target].reindex(x_all.index)
    out = np.empty((len(horizons), len(quantiles)))
    for i, h in enumerate(horizons):
        y = (price.shift(-h) - price).dropna()  # only outcomes already observed at the origin
        x_train = x_all.loc[y.index].to_numpy()
        model = RandomForestRegressor(n_jobs=-1, **PARAMS).fit(x_train, y.to_numpy())
        out[i] = _forest_quantiles(model, x_train, y.to_numpy(), x_all.iloc[[-1]].to_numpy(), quantiles)
    return out
