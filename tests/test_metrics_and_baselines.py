import numpy as np
import pytest

from bnbforecast import metrics, settings
from bnbforecast.models import naive_random_walk


def test_pinball_loss_matches_hand_calculation():
    # actual 1.0; q=0.1 predicts 0 (under by 1 -> 0.1*1); q=0.9 predicts 2 (over by 1 -> 0.1*1)
    loss = metrics.pinball_loss(np.array([1.0]), np.array([[0.0, 2.0]]), [0.1, 0.9])
    assert loss == pytest.approx(0.1)
    # actual 3.0 with the same forecasts: 0.1*3 and 0.9*1 -> mean 0.6
    loss = metrics.pinball_loss(np.array([3.0]), np.array([[0.0, 2.0]]), [0.1, 0.9])
    assert loss == pytest.approx(0.6)


def test_coverage_counts_inclusive_bounds():
    actual = np.array([0.0, 1.0, 2.0, 3.0])
    assert metrics.coverage(actual, np.full(4, 1.0), np.full(4, 2.0)) == 0.5


def test_prob_up_interpolates_and_clips():
    q = [0.1, 0.5, 0.9]
    preds = np.array([
        [-1.0, 0.0, 1.0],   # median at 0 -> 0.5
        [-3.0, -1.0, 1.0],  # 0 is halfway between q0.5 and q0.9 -> cdf 0.7 -> 0.3
        [1.0, 2.0, 3.0],    # everything above 0 -> clipped to 1 - 0.1
        [-3.0, -2.0, -1.0], # everything below 0 -> clipped to 1 - 0.9
    ])  # fmt: skip
    assert metrics.prob_up(preds, q) == pytest.approx([0.5, 0.3, 0.9, 0.1])


def test_wilson_interval_brackets_the_rate():
    low, high = metrics.wilson_interval(30, 60)
    assert low < 0.5 < high
    assert high - low < 0.26


def test_max_drawdown():
    assert metrics.max_drawdown(np.array([1.0, 2.0, 1.0, 3.0])) == pytest.approx(-0.5)


def test_random_walk_has_zero_median_and_drift_keeps_it(closes):
    log_close = np.log(closes[settings.TARGET])
    mid = settings.QUANTILES.index(0.5)
    rw = naive_random_walk.predict(log_close, settings.HORIZONS, settings.QUANTILES, drift=False)
    drift = naive_random_walk.predict(log_close, settings.HORIZONS, settings.QUANTILES, drift=True)
    assert rw.shape == (len(settings.HORIZONS), len(settings.QUANTILES))
    assert np.allclose(rw[:, mid], 0.0)
    assert not np.allclose(drift[:, mid], 0.0)
    assert (np.diff(rw, axis=1) >= 0).all()
    # Longer horizons must have wider bands.
    width = rw[:, -1] - rw[:, 0]
    assert width[-1] > width[0]


def test_diebold_mariano_detects_a_real_difference_only():
    rng = np.random.default_rng(0)
    base = rng.normal(1.0, 0.2, 300)
    assert metrics.diebold_mariano(base + 0.2, base + rng.normal(0, 0.05, 300), lags=5) < 0.01
    assert metrics.diebold_mariano(base + rng.normal(0, 0.05, 300), base, lags=5) > 0.05


def test_arima_and_delta_rf_shapes_and_ordering(closes, monkeypatch):
    from bnbforecast.models import arima_baseline, delta_random_forest

    monkeypatch.setitem(delta_random_forest.PARAMS, "n_estimators", 20)  # keep the test fast
    log_closes = np.log(closes)
    a = arima_baseline.predict(log_closes[settings.TARGET], settings.HORIZONS, settings.QUANTILES)
    r = delta_random_forest.predict(log_closes, [1, 30], settings.QUANTILES)
    assert a.shape == (len(settings.HORIZONS), len(settings.QUANTILES))
    assert r.shape == (2, len(settings.QUANTILES))
    assert (np.diff(a, axis=1) > 0).all() and (np.diff(r, axis=1) >= 0).all()
    assert (a[-1, -1] - a[-1, 0]) > (a[0, -1] - a[0, 0])  # uncertainty grows with horizon
