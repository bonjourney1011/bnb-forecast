"""Command line: fetch -> backtest -> summarize -> daily."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import typer

from bnbforecast import backtest as backtest_mod
from bnbforecast import backtest_summary, daily_forecast, market_store, settings

app = typer.Typer(add_completion=False, help="BNB 30-day probabilistic forecast")


@app.command()
def fetch() -> None:
    """Append every closed daily candle since the last stored day."""
    used = market_store.update()
    closes = market_store.load_closes()
    print(f"sources: {used}")
    print(f"{len(closes)} days, {closes.index[0].date()} -> {closes.index[-1].date()}")


@app.command()
def backtest(
    model: str = typer.Argument(..., help=f"one of {settings.MODELS}"),
    max_origins: int = typer.Option(0, help="stop after N new origins (0 = all); reruns resume"),
) -> None:
    """Rolling-origin backtest for one model. Safe to rerun: stored origins are skipped."""
    if model not in settings.MODELS:
        raise typer.BadParameter(f"choose from {settings.MODELS}")
    backtest_mod.run(model, market_store.load_closes(), max_origins or None)


@app.command()
def summarize() -> None:
    """Build web/data/backtest-summary.json from the stored predictions."""
    summary = backtest_summary.summarize(market_store.load_closes())
    daily_forecast.write_json("backtest-summary.json", summary)
    for model, s in summary["models"].items():
        d = s["by_horizon"][str(settings.MAX_HORIZON)]
        print(
            f"{model:18s} origins={s['origins']:4d}  mean skill vs RW={s['mean_skill_vs_rw']:+.3f}  "
            f"30d: skill={d['skill_vs_rw']:+.3f} cov80={d['coverage_80']:.2f}"
        )


@app.command()
def daily(skip_fetch: bool = typer.Option(False, help="use stored data as is")) -> None:
    """Fetch, forecast from the latest closed day, log it, score matured forecasts."""
    if not skip_fetch:
        print(f"sources: {market_store.update()}")
    closes = market_store.load_closes()
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date()
    if not skip_fetch and closes.index[-1].date() < yesterday:
        print(f"stale data: last close {closes.index[-1].date()}, expected {yesterday}")
        raise typer.Exit(1)
    payload, rows = daily_forecast.make_forecast(closes)
    log = daily_forecast.append_log(rows)
    daily_forecast.write_json("latest-forecast.json", payload)
    daily_forecast.write_json("forecast-log.json", daily_forecast.score_log(log, closes))
    print(f"as of {payload['as_of']}: price {payload['price']:.2f}, primary model {payload['primary']}")


if __name__ == "__main__":
    app()
