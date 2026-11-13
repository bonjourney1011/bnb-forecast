import numpy as np
import pandas as pd

from bnbforecast import features, settings


def test_features_at_origin_ignore_later_data(closes):
    """Cutting the data right after T must not change any feature at or before T."""
    origin = closes.index[600]
    full = features.build_features(closes)
    cut = features.build_features(closes.loc[:origin])
    pd.testing.assert_frame_equal(full.loc[:origin], cut)


def test_changing_the_future_does_not_change_past_features(closes):
    origin = closes.index[600]
    tampered = closes.copy()
    tampered.loc[tampered.index > origin] *= 5
    pd.testing.assert_frame_equal(
        features.build_features(closes).loc[:origin], features.build_features(tampered).loc[:origin]
    )


def test_target_is_forward_log_return(closes):
    table = features.build_table(closes)
    row = table[(table["t"] == closes.index[500]) & (table["h"] == 7)].iloc[0]
    bnb = closes[settings.TARGET]
    assert np.isclose(row["y"], np.log(bnb.iloc[507] / bnb.iloc[500]))
    assert row["target_date"] == closes.index[507]


def test_context_is_purged_at_origin(closes):
    table = features.build_table(closes)
    origin = closes.index[700]
    ctx = features.context_rows(table, origin)
    assert (ctx["target_date"] <= origin).all()
    assert ctx["y"].notna().all()
    # A 30-day row made 29 days before the origin has not resolved yet: it must be excluded.
    late = (ctx["t"] > origin - pd.Timedelta(days=30)) & (ctx["h"] == 30)
    assert not late.any()


def test_context_targets_do_not_depend_on_data_after_origin(closes):
    origin = closes.index[700]
    tampered = closes.copy()
    tampered.loc[tampered.index > origin] *= 5
    a = features.context_rows(features.build_table(closes), origin)
    b = features.context_rows(features.build_table(tampered), origin)
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))


def test_query_has_one_row_per_horizon(closes):
    table = features.build_table(closes)
    q = features.query_rows(table, closes.index[-1])
    assert list(q["h"]) == settings.HORIZONS
    assert q["y"].isna().all()  # the future is unknown at the last day


def test_days_to_burn_counts_down_to_the_15th():
    idx = pd.to_datetime(["2026-01-10", "2026-01-15", "2026-01-16", "2026-12-20"])
    assert list(features.days_to_next_burn(idx)) == [5, 0, 89, 26]
