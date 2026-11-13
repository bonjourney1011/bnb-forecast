"""Daily job: forecast from the latest closed day, write the JSON the site reads, and keep
an append-only log of every forecast so it can be scored once its outcome is known."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from bnbforecast import features, metrics, settings
from bnbforecast.backtest import predict_at
from bnbforecast.models import tabpfn_regressor

HISTORY_DAYS = 180
LOG_COLS = ["made_on", "model", "h", "target_date", "price_at_origin", *settings.QCOLS]


def _fan(price: float, preds: np.ndarray) -> dict[str, list[float]]:
    """Per-quantile price path for days 0..30, interpolated between the forecast horizons."""
    days = np.arange(settings.MAX_HORIZON + 1)
    knots = [0, *settings.HORIZONS]
    return {
        col: (price * np.exp(np.interp(days, knots, [0.0, *preds[:, i]]))).round(2).tolist()
        for i, col in enumerate(settings.QCOLS)
    }


def _model_block(price: float, preds: np.ndarray) -> dict:
    return {
        "returns": {str(h): row.round(5).tolist() for h, row in zip(settings.HORIZONS, preds, strict=True)},
        "fan": _fan(price, preds),
        "p_up_30": float(metrics.prob_up(preds[-1:], settings.QUANTILES)[0]),
    }


def make_forecast(closes: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Returns (payload for latest-forecast.json, new log rows)."""
    origin, table = closes.index[-1], features.build_table(closes)
    price = float(closes[settings.TARGET].iloc[-1])
    models = [m for m in settings.MODELS if m not in settings.TABPFN_MODELS or tabpfn_regressor.available()]
    blocks, errors, log_rows = {}, {}, []
    for model in models:
        try:
            preds = predict_at(model, origin, closes, table)
        except Exception as e:  # one model failing (quota, network) must not stop the others
            print(f"{model} failed: {type(e).__name__}: {e}")  # details stay in the job log
            errors[model] = type(e).__name__  # the published JSON gets the error class only
            continue
        blocks[model] = _model_block(price, preds)
        for h, row in zip(settings.HORIZONS, preds, strict=True):
            log_rows.append({
                "made_on": origin.date().isoformat(), "model": model, "h": h,
                "target_date": (origin + pd.Timedelta(days=h)).date().isoformat(),
                "price_at_origin": price, **dict(zip(settings.QCOLS, row.round(6), strict=True)),
            })  # fmt: skip
    if not blocks:
        raise RuntimeError("every model failed")
    primary = settings.PRIMARY_MODEL if settings.PRIMARY_MODEL in blocks else next(iter(blocks))
    history = closes[settings.TARGET].tail(HISTORY_DAYS)
    payload = {
        "as_of": origin.date().isoformat(),
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "price": price,
        "primary": primary,
        "track_model": settings.PRIMARY_MODEL,
        "labels": settings.MODEL_LABELS,
        "quantiles": settings.QUANTILES,
        "history": {"dates": [d.date().isoformat() for d in history.index], "close": history.round(2).tolist()},
        "models": blocks,
        "errors": errors,
    }
    return payload, pd.DataFrame(log_rows, columns=LOG_COLS)


def append_log(new_rows: pd.DataFrame) -> pd.DataFrame:
    """Append-only: a (made_on, model) pair already in the log is never overwritten."""
    path = settings.FORECAST_LOG_CSV
    log = pd.read_csv(path, dtype={"made_on": str, "target_date": str}) if path.exists() else new_rows.iloc[:0]
    seen = set(zip(log["made_on"], log["model"], strict=True))
    fresh = new_rows[[k not in seen for k in zip(new_rows["made_on"], new_rows["model"], strict=True)]]
    log = pd.concat([f for f in (log, fresh) if not f.empty], ignore_index=True) if len(fresh) else log
    path.parent.mkdir(parents=True, exist_ok=True)
    log.to_csv(path, index=False, lineterminator="\n")
    return log


def score_log(log: pd.DataFrame, closes: pd.DataFrame) -> dict:
    """Score matured forecasts against realised prices (the live, out-of-sample record)."""
    price = closes[settings.TARGET]
    known = {d.date().isoformat(): float(p) for d, p in price.items()}
    df = log.copy()
    df["actual_price"] = df["target_date"].map(known)
    matured = df.dropna(subset=["actual_price"]).copy()
    matured["actual"] = np.log(matured["actual_price"] / matured["price_at_origin"])
    out = {"first_forecast": log["made_on"].min() if len(log) else None, "models": {}}
    for model, g in matured.groupby("model"):
        a = g["actual"].to_numpy()
        g30 = g[g["h"] == settings.MAX_HORIZON]
        out["models"][model] = {
            "matured": int(len(g)),
            "coverage_80": metrics.coverage(a, g["q0.1"].to_numpy(), g["q0.9"].to_numpy()),
            "pinball": metrics.pinball_loss(a, g[settings.QCOLS].to_numpy(), settings.QUANTILES),
            "matured_30d": [
                {
                    "made_on": r.made_on, "target_date": r.target_date,
                    "low": round(r.price_at_origin * float(np.exp(r.q10)), 2),
                    "median": round(r.price_at_origin * float(np.exp(r.q50)), 2),
                    "high": round(r.price_at_origin * float(np.exp(r.q90)), 2),
                    "actual": round(r.actual_price, 2),
                }
                for r in g30.rename(columns={"q0.1": "q10", "q0.5": "q50", "q0.9": "q90"}).itertuples()
            ],  # fmt: skip
        }
    return out


def write_json(name: str, payload: dict) -> None:
    settings.WEB_DATA.mkdir(parents=True, exist_ok=True)
    (settings.WEB_DATA / name).write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False), encoding="utf-8")
