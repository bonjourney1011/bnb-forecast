import numpy as np
import pandas as pd
import pytest

from bnbforecast import settings


@pytest.fixture
def closes() -> pd.DataFrame:
    """900 days of synthetic geometric random walks for the three symbols."""
    rng = np.random.default_rng(7)
    index = pd.date_range("2020-01-01", periods=900, freq="D")
    steps = rng.normal(0.0005, 0.03, size=(len(index), len(settings.SYMBOLS)))
    return pd.DataFrame(100 * np.exp(steps.cumsum(axis=0)), index=index, columns=settings.SYMBOLS)
