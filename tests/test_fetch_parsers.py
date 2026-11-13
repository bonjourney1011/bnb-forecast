import pandas as pd
import pytest

from bnbforecast import market_store
from bnbforecast.fetch import binance_klines, kraken_fallback

DAY_MS = 86_400_000
D1 = 1_762_992_000_000  # 2025-11-13 00:00 UTC


def _kline(open_ms: int, close: str) -> list:
    return [open_ms, "1", "2", "0.5", close, "10", open_ms + DAY_MS - 1, "0", 1, "0", "0", "0"]


def test_binance_parser_drops_the_open_candle():
    raw = [_kline(D1, "600.5"), _kline(D1 + DAY_MS, "610.0")]
    now_ms = D1 + DAY_MS + 3_600_000  # one hour into the second day
    df = binance_klines.parse_klines(raw, "BNBUSDT", now_ms)
    assert df.to_dict("records") == [
        {"date": "2025-11-13", "symbol": "BNBUSDT", "close": 600.5, "source": "binance"}
    ]


def test_kraken_parser_drops_the_open_candle_and_handles_errors():
    d1 = D1 // 1000
    raw = {"error": [], "result": {"BNBUSD": [[d1, "1", "2", "0.5", "601.0", "0", "0", 1],
                                              [d1 + 86_400, "1", "2", "0.5", "611.0", "0", "0", 1]], "last": 1}}
    df = kraken_fallback.parse_ohlc(raw, "BNBUSDT", d1 + 86_400 + 60)
    assert list(df["date"]) == ["2025-11-13"]
    assert df["source"].iloc[0] == "kraken"
    assert kraken_fallback.parse_ohlc({"error": ["EQuery:Unknown asset pair"]}, "BNBUSDT", d1).empty


def test_to_wide_rejects_gaps():
    rows = [(d, s, 1.0, "binance") for d in ("2025-01-01", "2025-01-03") for s in market_store.settings.SYMBOLS]
    long = pd.DataFrame(rows, columns=binance_klines.COLS)
    with pytest.raises(ValueError, match="missing day"):
        market_store.to_wide(long)
