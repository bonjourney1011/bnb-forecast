"""Rolling-origin backtest. At each weekly origin a model sees only data up to that day and
predicts the quantiles of the log return at every horizon. Predictions are stored per model
so a run can be resumed (useful for API quotas) and models can be added later."""

from __future__ import annotations

import numpy as np
import pandas as pd

from bnbforecast import features, settings
from bnbforecast.models import naive_random_walk

SAVE_EVERY = 10


def predictions_path(model: str):
    return settings.BACKTEST_DIR / f"predictions-{model}.csv"


def load_predictions(model: str) -> pd.DataFrame:
    path = predictions_path(model)
    if not path.exists():
        return pd.DataFrame(columns=["origin", "h", *settings.QCOLS, "actual"])
    return pd.read_csv(path, parse_dates=["origin"])


def backtest_origins(table: pd.DataFrame, last_day: pd.Timestamp) -> list[pd.Timestamp]:
    """Weekly origins whose 30-day outcome is already known and which have features."""
    end = last_day - pd.Timedelta(days=settings.MAX_HORIZON)
    days = pd.date_range(settings.BACKTEST_START, end, freq=f"{settings.ORIGIN_STEP_DAYS}D")
    have = set(table["t"])
    return [d for d in days if d in have]


def predict_at(model: str, origin: pd.Timestamp, closes: pd.DataFrame, table: pd.DataFrame) -> np.ndarray:
    """(len(HORIZONS), len(QUANTILES)) log-return quantiles, using data up to `origin` only."""
    log_close = np.log(closes[settings.TARGET].loc[:origin])
    if model in ("random_walk", "random_walk_drift"):
        return naive_random_walk.predict(
            log_close, settings.HORIZONS, settings.QUANTILES, drift=model == "random_walk_drift"
        )
    if model == "chronos2":
        from bnbforecast.models import chronos_zero_shot

        return chronos_zero_shot.predict(log_close, settings.HORIZONS, settings.QUANTILES)
    if model == "arima":
        from bnbforecast.models import arima_baseline

        return arima_baseline.predict(log_close, settings.HORIZONS, settings.QUANTILES)
    if model == "delta_rf":
        from bnbforecast.models import delta_random_forest

        return delta_random_forest.predict(np.log(closes.loc[:origin]), settings.HORIZONS, settings.QUANTILES)
    if model in settings.TABPFN_MODELS:
        from bnbforecast.models import tabpfn_regressor

        context = features.context_rows(table, origin, sparse=model != "tabpfn")
        columns = features.FEATURES_CALENDAR if model == "tabpfn_calendar" else features.FEATURES
        return tabpfn_regressor.predict(context, features.query_rows(table, origin), settings.QUANTILES, columns)
    raise ValueError(f"unknown model: {model}")


def run(model: str, closes: pd.DataFrame, max_origins: int | None = None) -> pd.DataFrame:
    table = features.build_table(closes)
    done = load_predictions(model)
    todo = [o for o in backtest_origins(table, closes.index[-1]) if o not in set(done["origin"])]
    if max_origins:
        todo = todo[:max_origins]
    print(f"{model}: {len(todo)} origin(s) to run, {done['origin'].nunique()} already stored")
    new_rows = []
    try:
        for i, origin in enumerate(todo, 1):
            preds = predict_at(model, origin, closes, table)
            actual = features.query_rows(table, origin)["y"].to_numpy()
            for h, row, y in zip(settings.HORIZONS, preds, actual, strict=True):
                quantiles = dict(zip(settings.QCOLS, row, strict=True))
                new_rows.append({"origin": origin, "h": h, **quantiles, "actual": y})
            if i % SAVE_EVERY == 0 or i == len(todo):
                done = _save(model, done, new_rows)
                new_rows = []
                print(f"  {i}/{len(todo)} (through {origin.date()})")
    finally:  # a quota or network error must not discard origins already paid for
        if new_rows:
            done = _save(model, done, new_rows)
    return done


def _save(model: str, done: pd.DataFrame, new_rows: list[dict]) -> pd.DataFrame:
    frames = [f for f in (done, pd.DataFrame(new_rows)) if not f.empty]
    out = pd.concat(frames, ignore_index=True).sort_values(["origin", "h"], ignore_index=True)
    settings.BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(predictions_path(model), index=False, float_format="%.6f", lineterminator="\n")
    return out
