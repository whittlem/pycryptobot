import sys

import numpy as np
import pandas as pd
import pytest

sys.path.append(".")
# pylint: disable=import-error
from models.Trading import TechnicalAnalysis

TOTAL_PERIODS = 300


def build_data(rows: int = TOTAL_PERIODS) -> pd.DataFrame:
    """Build a deterministic OHLCV data set shaped like exchange candle data."""

    rng = np.random.default_rng(7)
    close = 20000 + np.cumsum(rng.normal(0, 40, rows))
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=rows, freq="h"),
            "market": "BTC-GBP",
            "granularity": "1hour",
            "low": close - rng.uniform(5, 50, rows),
            "high": close + rng.uniform(5, 50, rows),
            "open": close + rng.normal(0, 10, rows),
            "close": close,
            "volume": rng.uniform(1, 100, rows),
        }
    )


def test_add_all_produces_complete_indicators():
    ta = TechnicalAnalysis(build_data(), total_periods=TOTAL_PERIODS)
    ta.add_all()
    df = ta.get_df()

    expected_columns = [
        "close_pc",
        "cma",
        "sma5",
        "sma8",
        "sma13",
        "sma20",
        "sma50",
        "sma200",
        "ema8",
        "ema12",
        "ema26",
        "bb20_upper",
        "bb20_mid",
        "bb20_lower",
        "rsi14",
        "stochrsi14k",
        "stochrsi14d",
        "williamsr14",
        "macd",
        "signal",
        "obv",
        "elder_ray_bull",
        "elder_ray_bear",
    ]
    missing = [column for column in expected_columns if column not in df.columns]
    assert not missing, f"missing indicator columns: {missing}"

    empty = [column for column in expected_columns if df[column].isna().all()]
    assert not empty, f"indicator columns without values: {empty}"

    assert df["rsi14"].between(0, 100).all()
    assert (df["bb20_upper"] >= df["bb20_mid"]).all()
    assert (df["bb20_mid"] >= df["bb20_lower"]).all()
    assert (df["adx14"].between(0, 100)).all()


def test_technical_analysis_requires_close_column():
    data = build_data().drop(columns=["close"])

    with pytest.raises(AttributeError):
        TechnicalAnalysis(data, total_periods=TOTAL_PERIODS)


def test_technical_analysis_requires_dataframe():
    with pytest.raises(TypeError):
        TechnicalAnalysis([], total_periods=TOTAL_PERIODS)
