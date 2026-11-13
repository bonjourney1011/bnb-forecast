"""TabPFN through the hosted API (tabpfn-client). `fit` uploads the context table; the
quantiles come from one forward pass at predict time. Needs TABPFN_TOKEN in the environment."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from bnbforecast.features import FEATURES

ENV_TOKEN = "TABPFN_TOKEN"


class TokenMissing(RuntimeError):
    pass


def available() -> bool:
    return bool(os.environ.get(ENV_TOKEN))


def _login() -> None:
    token = os.environ.get(ENV_TOKEN)
    if not token:
        raise TokenMissing(f"{ENV_TOKEN} is not set")
    os.environ.setdefault("TABPFN_DISABLE_TELEMETRY", "1")
    import tabpfn_client

    tabpfn_client.set_access_token(token)


def predict(
    context: pd.DataFrame, query: pd.DataFrame, quantiles: list[float], columns: list[str] = FEATURES
) -> np.ndarray:
    """Returns (len(query), len(quantiles)) log returns. `context` needs FEATURES + `y`."""
    _login()
    from tabpfn_client import TabPFNRegressor

    model = TabPFNRegressor()
    model.fit(context[columns], context["y"])
    preds = model.predict(query[columns], output_type="quantiles", quantiles=quantiles)
    # A quantile regressor can cross on rare rows; sorting keeps the fan well-formed.
    return np.sort(np.column_stack([np.asarray(p) for p in preds]), axis=1)
