"""Technical analysis on a trading Pandas DataFrame"""

import warnings
import numpy as np
import pandas as pd
from re import compile
from numpy import (
    abs,
    floor,
    max,
    maximum,
    mean,
    minimum,
    nan,
    ndarray,
    round,
    sum as np_sum,
    where,
)
from pandas import concat, DataFrame, Series
from datetime import datetime, timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX, SARIMAXResultsWrapper
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from models.helper.LogHelper import Logger
#####  Setup custom Trading.py file for pandas_ta
try:
    import pandas_ta as ta
except ImportError as err:
    raise SystemExit(f"Pandas-ta Error: {err}")
try:
    import talib
    use_talib = True
except ImportError:
    use_talib = False

warnings.simplefilter("ignore", ConvergenceWarning)


class TechnicalAnalysis:
    def __init__(self, data=DataFrame(), total_periods: int=300) -> None:
        """Technical Analysis object model

        Parameters
        ----------
        data : Pandas Time Series
            data[ts] = [ 'date', 'market', 'granularity', 'low', 'high', 'open', 'close', 'volume' ]
        """

        if not isinstance(data, DataFrame):
            raise TypeError("Data is not a Pandas dataframe.")

        if (
            "date" not in data
            and "market" not in data
            and "granularity" not in data
            and "low" not in data
            and "high" not in data
            and "open" not in data
            and "close" not in data
            and "volume" not in data
        ):
            raise ValueError(
                "Data not not contain date, market, granularity, low, high, open, close, volume"
            )

        if not "close" in data.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not data["close"].dtype == "float64" and not data["close"].dtype == "int64":
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64."
            )

        # treat infinite values as nan
        pd.set_option('use_inf_as_na', True)

        self.df = data
        self.levels = []
        self.total_periods = total_periods

        # enable/disable Pandas-ta module and/or TA-Lib
        self.pandas_ta = True
        self.talib = use_talib

    def getDataFrame(self) -> DataFrame:
        """Returns the Pandas DataFrame"""

        return self.df

    def addAll(self) -> None:
        """Adds analysis to the DataFrame"""

        self.addChangePct()

        self.addCMA()
        # for SMA and EMA, add True if wanting to add pcnt of chg to dataframe
        self.addSMA(5, True)
        self.addSMA(10, True)
        self.addSMA(20)
        if self.total_periods >= 50:
            self.addSMA(50, True)
        if self.total_periods >= 100:
            self.addSMA(100, True)
        if self.total_periods >= 200:
            self.addSMA(200)
        self.addEMA(5, True) # add True if wanting to add pcnt of chg to dataframe
        self.addEMA(9)
        self.addEMA(12)
        self.addEMA(26)
        self.addGoldenCross()
        self.addDeathCross()
        self.addFibonacciBollingerBands()

        self.addRSI(14,14,True) # add MA period to add Moving Average and True to add pcnt of change
#        self.addStochasticRSI(14)
        self.addWilliamsR() # default period is 20, add an integer to change default
        self.addMACD() # add fast, slow, signal to be used, defaults to 12, 26, 9
        self.addOBV(8) # integer is ma_period and is optional, default is 5
        self.addElderRayIndex()

        self.addEMABuySignals()
        if self.total_periods >= 200:
            self.addSMABuySignals()
        self.addMACDBuySignals()
        self.addADXBuySignals()
        self.addEMA_WMAsignal(5,5) # EMA with WMA smoothing

        self.ta_MACDLead() # add fast, slow, signal to be used, defaults to 12, 26, 9

        self.addCandleAstralBuy()
        self.addCandleAstralSell()
        self.addCandleHammer()
        self.addCandleInvertedHammer()
        self.addCandleShootingStar()
        self.addCandleHangingMan()
        self.addCandleThreeWhiteSoldiers()
        self.addCandleThreeBlackCrows()
        self.addCandleDoji()
        self.addCandleThreeLineStrike()
        self.addCandleTwoBlackGapping()
        self.addCandleMorningStar()
        self.addCandleEveningStar()
        self.addCandleAbandonedBaby()
        self.addCandleMorningDojiStar()
        self.addCandleEveningDojiStar()

    """Candlestick References
    https://commodity.com/technical-analysis
    https://www.investopedia.com
    https://github.com/SpiralDevelopment/candlestick-patterns
    https://www.incrediblecharts.com/candlestick_patterns/candlestick-patterns-strongest.php
    """

    def candleHammer(self) -> Series:
        """* Candlestick Detected: Hammer ("Weak - Reversal - Bullish Signal - Up"""

        return (
            (
                (self.df["high"] - self.df["low"])
                > 3 * (self.df["open"] - self.df["close"])
            )
            & (
                (
                    (self.df["close"] - self.df["low"])
                    / (0.001 + self.df["high"] - self.df["low"])
                )
                > 0.6
            )
            & (
                (
                    (self.df["open"] - self.df["low"])
                    / (0.001 + self.df["high"] - self.df["low"])
                )
                > 0.6
            )
        )

    def addCandleHammer(self) -> None:
        self.df["hammer"] = self.candleHammer()

    def candleShootingStar(self) -> Series:
        """* Candlestick Detected: Shooting Star ("Weak - Reversal - Bearish Pattern - Down")"""

        return (
            (
                (self.df["open"].shift(1) < self.df["close"].shift(1))
                & (self.df["close"].shift(1) < self.df["open"])
            )
            & (
                self.df["high"] - maximum(self.df["open"], self.df["close"])
                >= (abs(self.df["open"] - self.df["close"]) * 3)
            )
            & (
                (minimum(self.df["close"], self.df["open"]) - self.df["low"])
                <= abs(self.df["open"] - self.df["close"])
            )
        )

    def addCandleShootingStar(self) -> None:
        self.df["shooting_star"] = self.candleShootingStar()

    def candleHangingMan(self) -> Series:
        """* Candlestick Detected: Hanging Man ("Weak - Continuation - Bearish Pattern - Down")"""

        return (
            (
                (self.df["high"] - self.df["low"])
                > (4 * (self.df["open"] - self.df["close"]))
            )
            & (
                (
                    (self.df["close"] - self.df["low"])
                    / (0.001 + self.df["high"] - self.df["low"])
                )
                >= 0.75
            )
            & (
                (
                    (self.df["open"] - self.df["low"])
                    / (0.001 + self.df["high"] - self.df["low"])
                )
                >= 0.75
            )
            & (self.df["high"].shift(1) < self.df["open"])
            & (self.df["high"].shift(2) < self.df["open"])
        )

    def addCandleHangingMan(self) -> None:
        self.df["hanging_man"] = self.candleHangingMan()

    def candleInvertedHammer(self) -> Series:
        """* Candlestick Detected: Inverted Hammer ("Weak - Continuation - Bullish Pattern - Up")"""

        return (
            (
                (self.df["high"] - self.df["low"])
                > 3 * (self.df["open"] - self.df["close"])
            )
            & (
                (self.df["high"] - self.df["close"])
                / (0.001 + self.df["high"] - self.df["low"])
                > 0.6
            )
            & (
                (self.df["high"] - self.df["open"])
                / (0.001 + self.df["high"] - self.df["low"])
                > 0.6
            )
        )

    def addCandleInvertedHammer(self) -> None:
        self.df["inverted_hammer"] = self.candleInvertedHammer()

    def candleThreeWhiteSoldiers(self) -> Series:
        """*** Candlestick Detected: Three White Soldiers ("Strong - Reversal - Bullish Pattern - Up")"""

        return (
            (
                (self.df["open"] > self.df["open"].shift(1))
                & (self.df["open"] < self.df["close"].shift(1))
            )
            & (self.df["close"] > self.df["high"].shift(1))
            & (
                self.df["high"] - maximum(self.df["open"], self.df["close"])
                < (abs(self.df["open"] - self.df["close"]))
            )
            & (
                (self.df["open"].shift(1) > self.df["open"].shift(2))
                & (self.df["open"].shift(1) < self.df["close"].shift(2))
            )
            & (self.df["close"].shift(1) > self.df["high"].shift(2))
            & (
                self.df["high"].shift(1)
                - maximum(self.df["open"].shift(1), self.df["close"].shift(1))
                < (abs(self.df["open"].shift(1) - self.df["close"].shift(1)))
            )
        )

    def addCandleThreeWhiteSoldiers(self) -> None:
        self.df["three_white_soldiers"] = self.candleThreeWhiteSoldiers()

    def candleThreeBlackCrows(self) -> Series:
        """* Candlestick Detected: Three Black Crows ("Strong - Reversal - Bearish Pattern - Down")"""

        return (
            (
                (self.df["open"] < self.df["open"].shift(1))
                & (self.df["open"] > self.df["close"].shift(1))
            )
            & (self.df["close"] < self.df["low"].shift(1))
            & (
                self.df["low"] - maximum(self.df["open"], self.df["close"])
                < (abs(self.df["open"] - self.df["close"]))
            )
            & (
                (self.df["open"].shift(1) < self.df["open"].shift(2))
                & (self.df["open"].shift(1) > self.df["close"].shift(2))
            )
            & (self.df["close"].shift(1) < self.df["low"].shift(2))
            & (
                self.df["low"].shift(1)
                - maximum(self.df["open"].shift(1), self.df["close"].shift(1))
                < (abs(self.df["open"].shift(1) - self.df["close"].shift(1)))
            )
        )

    def addCandleThreeBlackCrows(self) -> None:
        self.df["three_black_crows"] = self.candleThreeBlackCrows()

    def candleDoji(self) -> Series:
        """! Candlestick Detected: Doji ("Indecision")"""

        return (
            (
                (
                    abs(self.df["close"] - self.df["open"])
                    / (self.df["high"] - self.df["low"])
                )
                < 0.1
            )
            & (
                (self.df["high"] - maximum(self.df["close"], self.df["open"]))
                > (3 * abs(self.df["close"] - self.df["open"]))
            )
            & (
                (minimum(self.df["close"], self.df["open"]) - self.df["low"])
                > (3 * abs(self.df["close"] - self.df["open"]))
            )
        )

    def addCandleDoji(self) -> None:
        self.df["doji"] = self.candleDoji()

    def candleThreeLineStrike(self) -> Series:
        """** Candlestick Detected: Three Line Strike ("Reliable - Reversal - Bullish Pattern - Up")"""

        return (
            (
                (self.df["open"].shift(1) < self.df["open"].shift(2))
                & (self.df["open"].shift(1) > self.df["close"].shift(2))
            )
            & (self.df["close"].shift(1) < self.df["low"].shift(2))
            & (
                self.df["low"].shift(1)
                - maximum(self.df["open"].shift(1), self.df["close"].shift(1))
                < (abs(self.df["open"].shift(1) - self.df["close"].shift(1)))
            )
            & (
                (self.df["open"].shift(2) < self.df["open"].shift(3))
                & (self.df["open"].shift(2) > self.df["close"].shift(3))
            )
            & (self.df["close"].shift(2) < self.df["low"].shift(3))
            & (
                self.df["low"].shift(2)
                - maximum(self.df["open"].shift(2), self.df["close"].shift(2))
                < (abs(self.df["open"].shift(2) - self.df["close"].shift(2)))
            )
            & (
                (self.df["open"] < self.df["low"].shift(1))
                & (self.df["close"] > self.df["high"].shift(3))
            )
        )

    def addCandleThreeLineStrike(self) -> None:
        self.df["three_line_strike"] = self.candleThreeLineStrike()

    def candleTwoBlackGapping(self) -> Series:
        """*** Candlestick Detected: Two Black Gapping ("Reliable - Reversal - Bearish Pattern - Down")"""

        return (
            (
                (self.df["open"] < self.df["open"].shift(1))
                & (self.df["open"] > self.df["close"].shift(1))
            )
            & (self.df["close"] < self.df["low"].shift(1))
            & (
                self.df["low"] - maximum(self.df["open"], self.df["close"])
                < (abs(self.df["open"] - self.df["close"]))
            )
            & (self.df["high"].shift(1) < self.df["low"].shift(2))
        )

    def addCandleTwoBlackGapping(self) -> None:
        self.df["two_black_gapping"] = self.candleTwoBlackGapping()

    def candleMorningStar(self) -> Series:
        """*** Candlestick Detected: Morning Star ("Strong - Reversal - Bullish Pattern - Up")"""

        return (
            (
                maximum(self.df["open"].shift(1), self.df["close"].shift(1))
                < self.df["close"].shift(2)
            )
            & (self.df["close"].shift(2) < self.df["open"].shift(2))
        ) & (
            (self.df["close"] > self.df["open"])
            & (
                self.df["open"]
                > maximum(self.df["open"].shift(1), self.df["close"].shift(1))
            )
        )

    def addCandleMorningStar(self) -> None:
        self.df["morning_star"] = self.candleMorningStar()

    def candleEveningStar(self) -> ndarray:
        """*** Candlestick Detected: Evening Star ("Strong - Reversal - Bearish Pattern - Down")"""

        return (
            (
                minimum(self.df["open"].shift(1), self.df["close"].shift(1))
                > self.df["close"].shift(2)
            )
            & (self.df["close"].shift(2) > self.df["open"].shift(2))
        ) & (
            (self.df["close"] < self.df["open"])
            & (
                self.df["open"]
                < minimum(self.df["open"].shift(1), self.df["close"].shift(1))
            )
        )

    def addCandleEveningStar(self) -> None:
        self.df["evening_star"] = self.candleEveningStar()

    def candleAbandonedBaby(self):
        """** Candlestick Detected: Abandoned Baby ("Reliable - Reversal - Bullish Pattern - Up")"""

        return (
            (self.df["open"] < self.df["close"])
            & (self.df["high"].shift(1) < self.df["low"])
            & (self.df["open"].shift(2) > self.df["close"].shift(2))
            & (self.df["high"].shift(1) < self.df["low"].shift(2))
        )

    def addCandleAbandonedBaby(self) -> None:
        self.df["abandoned_baby"] = self.candleAbandonedBaby()

    def candleMorningDojiStar(self) -> Series:
        """** Candlestick Detected: Morning Doji Star ("Reliable - Reversal - Bullish Pattern - Up")"""

        return (self.df["close"].shift(2) < self.df["open"].shift(2)) & (
            abs(self.df["close"].shift(2) - self.df["open"].shift(2))
            / (self.df["high"].shift(2) - self.df["low"].shift(2))
            >= 0.7
        ) & (
            abs(self.df["close"].shift(1) - self.df["open"].shift(1))
            / (self.df["high"].shift(1) - self.df["low"].shift(1))
            < 0.1
        ) & (
            self.df["close"] > self.df["open"]
        ) & (
            abs(self.df["close"] - self.df["open"]) / (self.df["high"] - self.df["low"])
            >= 0.7
        ) & (
            self.df["close"].shift(2) > self.df["close"].shift(1)
        ) & (
            self.df["close"].shift(2) > self.df["open"].shift(1)
        ) & (
            self.df["close"].shift(1) < self.df["open"]
        ) & (
            self.df["open"].shift(1) < self.df["open"]
        ) & (
            self.df["close"] > self.df["close"].shift(2)
        ) & (
            (
                self.df["high"].shift(1)
                - maximum(self.df["close"].shift(1), self.df["open"].shift(1))
            )
            > (3 * abs(self.df["close"].shift(1) - self.df["open"].shift(1)))
        ) & (
            minimum(self.df["close"].shift(1), self.df["open"].shift(1))
            - self.df["low"].shift(1)
        ) > (
            3 * abs(self.df["close"].shift(1) - self.df["open"].shift(1))
        )

    def addCandleMorningDojiStar(self) -> None:
        self.df["morning_doji_star"] = self.candleMorningDojiStar()

    def candleEveningDojiStar(self) -> Series:
        """** Candlestick Detected: Evening Doji Star ("Reliable - Reversal - Bearish Pattern - Down")"""

        return (self.df["close"].shift(2) > self.df["open"].shift(2)) & (
            abs(self.df["close"].shift(2) - self.df["open"].shift(2))
            / (self.df["high"].shift(2) - self.df["low"].shift(2))
            >= 0.7
        ) & (
            abs(self.df["close"].shift(1) - self.df["open"].shift(1))
            / (self.df["high"].shift(1) - self.df["low"].shift(1))
            < 0.1
        ) & (
            self.df["close"] < self.df["open"]
        ) & (
            abs(self.df["close"] - self.df["open"]) / (self.df["high"] - self.df["low"])
            >= 0.7
        ) & (
            self.df["close"].shift(2) < self.df["close"].shift(1)
        ) & (
            self.df["close"].shift(2) < self.df["open"].shift(1)
        ) & (
            self.df["close"].shift(1) > self.df["open"]
        ) & (
            self.df["open"].shift(1) > self.df["open"]
        ) & (
            self.df["close"] < self.df["close"].shift(2)
        ) & (
            (
                self.df["high"].shift(1)
                - maximum(self.df["close"].shift(1), self.df["open"].shift(1))
            )
            > (3 * abs(self.df["close"].shift(1) - self.df["open"].shift(1)))
        ) & (
            minimum(self.df["close"].shift(1), self.df["open"].shift(1))
            - self.df["low"].shift(1)
        ) > (
            3 * abs(self.df["close"].shift(1) - self.df["open"].shift(1))
        )

    def addCandleEveningDojiStar(self) -> None:
        self.df["evening_doji_star"] = self.candleEveningDojiStar()

    def candleAstralBuy(self) -> Series:
        """*** Candlestick Detected: Astral Buy (Fibonacci 3, 5, 8)"""

        return (
            (self.df["close"] < self.df["close"].shift(3))
            & (self.df["low"] < self.df["low"].shift(5))
            & (self.df["close"].shift(1) < self.df["close"].shift(4))
            & (self.df["low"].shift(1) < self.df["low"].shift(6))
            & (self.df["close"].shift(2) < self.df["close"].shift(5))
            & (self.df["low"].shift(2) < self.df["low"].shift(7))
            & (self.df["close"].shift(3) < self.df["close"].shift(6))
            & (self.df["low"].shift(3) < self.df["low"].shift(8))
            & (self.df["close"].shift(4) < self.df["close"].shift(7))
            & (self.df["low"].shift(4) < self.df["low"].shift(9))
            & (self.df["close"].shift(5) < self.df["close"].shift(8))
            & (self.df["low"].shift(5) < self.df["low"].shift(10))
            & (self.df["close"].shift(6) < self.df["close"].shift(9))
            & (self.df["low"].shift(6) < self.df["low"].shift(11))
            & (self.df["close"].shift(7) < self.df["close"].shift(10))
            & (self.df["low"].shift(7) < self.df["low"].shift(12))
        )

    def addCandleAstralBuy(self) -> None:
        self.df["astral_buy"] = self.candleAstralBuy()

    def candleAstralSell(self) -> Series:
        """*** Candlestick Detected: Astral Sell (Fibonacci 3, 5, 8)"""

        return (
            (self.df["close"] > self.df["close"].shift(3))
            & (self.df["high"] > self.df["high"].shift(5))
            & (self.df["close"].shift(1) > self.df["close"].shift(4))
            & (self.df["high"].shift(1) > self.df["high"].shift(6))
            & (self.df["close"].shift(2) > self.df["close"].shift(5))
            & (self.df["high"].shift(2) > self.df["high"].shift(7))
            & (self.df["close"].shift(3) > self.df["close"].shift(6))
            & (self.df["high"].shift(3) > self.df["high"].shift(8))
            & (self.df["close"].shift(4) > self.df["close"].shift(7))
            & (self.df["high"].shift(4) > self.df["high"].shift(9))
            & (self.df["close"].shift(5) > self.df["close"].shift(8))
            & (self.df["high"].shift(5) > self.df["high"].shift(10))
            & (self.df["close"].shift(6) > self.df["close"].shift(9))
            & (self.df["high"].shift(6) > self.df["high"].shift(11))
            & (self.df["close"].shift(7) > self.df["close"].shift(10))
            & (self.df["high"].shift(7) > self.df["high"].shift(12))
        )

    def addCandleAstralSell(self, period: int = 14) -> None:
        self.df["astral_sell"] = self.candleAstralSell()

    def addADXBuySignals(self, interval: int = 14) -> None:
        """Adds Average Directional Index (ADX) buy and sell signals to the DataFrame"""

        data = self.ta_ADX(interval)
        self.df["+di_pc"] = data["+di_pc"]
        self.df["-di" + str(interval)] = data["-di" + str(interval)]
        self.df["+di" + str(interval)] = data["+di" + str(interval)]
        self.df["adx" + str(interval)] = data["adx" + str(interval)]

    def addADX(self, interval: int = 14) -> None:
        """Adds Average Directional Index (ADX)"""

        """Average Directional Index (ADX)"""

        if not isinstance(interval, int):
            raise TypeError("interval parameter is not intervaleric.")

        if interval > self.total_periods or interval < 5 or interval > 200:
            raise ValueError("interval is out of range")

        if len(self.df) < interval:
            raise Exception("Data range too small.")

        data = self.ta_ADX(interval)
        self.df["-di" + str(interval)] = data["-di" + str(interval)]
        self.df["+di" + str(interval)] = data[["+di" + str(interval)]]
        self.df["adx" + str(interval)] = data[["adx" + str(interval)]]

    def ta_ADX(self, interval: int = 14) -> DataFrame:

        df = self.df.copy()
        df = df.ta.adx(high=df["high"], low=df["low"], close=df["close"], length=interval, mamode="sma", talib=self.talib)

        df["-di" + str(interval)] = df["DMN_" + str(interval)].fillna(0)
        df["+di" + str(interval)] = df["DMP_" + str(interval)].fillna(0)
        df["adx" + str(interval)] = df["ADX_" + str(interval)].fillna(0)

        df["+di_pc"] = round(df["+di" + str(interval)].pct_change() * 100, 2)
        df["+di_pc"] = df["+di_pc"].fillna(0)

        return df[
            [
                "-di" + str(interval),
                "+di" + str(interval),
                "adx" + str(interval),
                "+di_pc"
            ]
        ]

    def addATR(self, interval: int = 14) -> None:
        """Adds Average True Range (ATR)"""

        """Average True Range (ATX)"""

        if not isinstance(interval, int):
            raise TypeError("interval parameter is not intervaleric.")

        if interval > self.total_periods or interval < 5 or interval > 200:
            raise ValueError("interval is out of range")

        if len(self.df) < interval:
            raise Exception("Data range too small.")

        self.df["atr" + str(interval)] = ta.atr(
            high=self.df["high"], low=self.df["low"], close=self.df["close"], length=interval, mamode="sma", talib=self.talib
        )
        self.df["atr" + str(interval)] = self.df["atr" + str(interval)].fillna(0)
 
    def changePct(self) -> DataFrame:
        """Close change percentage"""

        close_pc = self.df["close"] / self.df["close"].shift(1) - 1
        close_pc = close_pc.fillna(0)
        return close_pc

    def addChangePct(self) -> None:
        """Adds the close percentage to the DataFrame"""

        self.df["close_pc"] = self.changePct()

        # cumulative returns
        self.df["close_cpc"] = (1 + self.df["close_pc"]).cumprod() - 1

    def cumulativeMovingAverage(self) -> float:
        """Calculates the Cumulative Moving Average (CMA)"""

        return self.df.close.expanding().mean()

    def addCMA(self) -> None:
        """Adds the Cumulative Moving Average (CMA) to the DataFrame"""

        self.df["cma"] = self.cumulativeMovingAverage()

    def exponentialMovingAverage(self, period: int) -> float:
        """Calculates the Exponential Moving Average (EMA)"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period > self.total_periods or period < 5 or period > 200:
            raise ValueError(f"EMA{period} Period is out of range")

        if len(self.df) < period:
            raise Exception("EMA Data range too small.")

        return self.df.close.ewm(span=period, adjust=False, min_periods=period).mean()

    def addEMA(self, period: int, addPC: bool = False) -> None:
        """Adds the Exponential Moving Average (EMA) the DateFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period > self.total_periods or period < 5 or period > 200:
            raise ValueError(f"addEMA{period} Period is out of range")

        if len(self.df) < period:
            raise Exception("addEMA Data range too small.")

        self.df["ema" + str(period)] = ta.ema(self.df["close"], length=period, talib=self.talib)
        self.df["ema" + str(period)] = self.df["ema" + str(period)].fillna(0)

        if addPC:
            self.df["ema" + str(period) + "_pc"] = round(self.df["ema" + str(period)].pct_change() * 100, 2)

    def addEMA_WMAsignal(self, ema_period: int, wma_period: int) -> None:
        """Adds EMA with WMA smoothing option to the DateFrame"""

        if not isinstance(ema_period, int) or not isinstance(wma_period, int):
            raise TypeError("Period parameter is not perioderic.")

        if ema_period > self.total_periods or ema_period < 5 or ema_period > 200:
            raise ValueError(f"EMA{ema_period} Period is out of range")

        if wma_period > self.total_periods or wma_period < 5 or wma_period > 200:
            raise ValueError(f"WMA{wma_period} Period is out of range")

        if len(self.df) < ema_period or len(self.df) < wma_period:
            raise Exception("addEMA_WMA Data range too small.")

        if "ema" + str(ema_period) not in self.df:
            self.addEMA(ema_period, True)

        self.df["ema" + str(ema_period) + "_wma" + str(wma_period)] = ta.wma(close=self.df["ema" + str(ema_period)], length=wma_period, talib=self.talib)
        self.df["ema" + str(ema_period) + "_wma" + str(wma_period)] = self.df["ema" + str(ema_period) + "_wma" + str(wma_period)].fillna(0)

    def calculateStochasticRelativeStrengthIndex(
        self, series: int, interval: int = 14
    ) -> float:
        """Calculates the Stochastic RSI on a Pandas series of RSI"""

        if not isinstance(series, Series):
            raise TypeError("Pandas Series required.")

        if not isinstance(interval, int):
            raise TypeError("Interval integer required.")

        if len(series) < interval:
            raise IndexError("Pandas Series smaller than interval.")

        return (series - series.rolling(interval).min()) / (
            series.rolling(interval).max() - series.rolling(interval).min()
        )

    def addFibonacciBollingerBands(
        self, interval: int = 20, multiplier: int = 3
    ) -> None:
        """Adds Fibonacci Bollinger Bands."""

        if not isinstance(interval, int):
            raise TypeError("Interval integer required.")

        if not isinstance(multiplier, int):
            raise TypeError("Multiplier integer required.")

        tp = (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        sma = tp.rolling(interval).mean()
        sd = multiplier * tp.rolling(interval).std()

        sma = sma.fillna(0)
        sd = sd.fillna(0)

        self.df["fbb_mid"] = sma
        self.df["fbb_upper0_236"] = sma + (0.236 * sd)
        self.df["fbb_upper0_382"] = sma + (0.382 * sd)
        self.df["fbb_upper0_5"] = sma + (0.5 * sd)
        self.df["fbb_upper0_618"] = sma + (0.618 * sd)
        self.df["fbb_upper0_786"] = sma + (0.786 * sd)
        self.df["fbb_upper1"] = sma + (1 * sd)
        self.df["fbb_lower0_236"] = sma - (0.236 * sd)
        self.df["fbb_lower0_382"] = sma - (0.382 * sd)
        self.df["fbb_lower0_5"] = sma - (0.5 * sd)
        self.df["fbb_lower0_618"] = sma - (0.618 * sd)
        self.df["fbb_lower0_786"] = sma - (0.786 * sd)
        self.df["fbb_lower1"] = sma - (1 * sd)

    def ta_MACD(self, fast: int=12, slow: int=26, sig: int=9) -> DataFrame:
        """Calculates the Moving Average Convergence Divergence (MACD)"""
        """Using EMA Oscillator and SMA Signal Length of 5"""
        """Traditional uses EMA Oscillator and EMA Signal"""
        if len(self.df) < slow:
            raise Exception("ta_MACD Data range too small.")

        df = self.df.copy()
#        df = df.ta.macd(close=df['close'], fast=8, slow=21, signal=5, talib=self.talib)
#        df["macd"] = df["MACD_8_21_5"].fillna(0)
#        df["signal"] = df["MACDs_8_21_5"].fillna(0)
#        df["hist"] = df["MACDh_8_21_5"].fillna(0)

        # modified MACD, above is traditional MACD
        df["fast_ma"] = ta.ema(close=df["close"], length=fast, talib=self.talib)
        df["slow_ma"] = ta.ema(close=df["close"], length=slow, talib=self.talib)
        df["macd"] = df["fast_ma"] - df["slow_ma"]
        df["signal"] = ta.sma(close=df["macd"], length=sig, talib=self.talib)
        df["macd"] = df["macd"].fillna(0)
        df["signal"] = df["signal"].fillna(0)

        df["macd_pc"] = round((df["macd"] - df["macd"].shift()) / abs(df["macd"]) * 100, 2)
        df["macd_pc"] = df["macd_pc"].fillna(0)

        return df

    def addMACD(self, fast: int=12, slow: int=26, sig: int=9) -> None:
        """Adds the Moving Average Convergence Divergence (MACD) to the DataFrame"""

        df = self.ta_MACD(fast,slow,sig)
        self.df["macd"] = df["macd"]
        self.df["signal"] = df["signal"]
        self.df["macd_pc"] = df["macd_pc"]

    def ta_MACDLead(self, fast: int=12, slow: int=26, sig: int=9) -> None:
        """Adds the Leading Moving Average Convergence Divergence (MACDLead) to the DataFrame"""

        df = self.df.copy()

        df['sema'] = ta.rma(df["close"], length=fast, talib=self.talib)
        df['lema'] = ta.rma(df["close"], length=slow, talib=self.talib)
        df['sema'] = df['sema'].fillna(0)
        df['lema'] = df['lema'].fillna(0)

        df['i1'] = df['sema'] + ta.rma(df["close"] - df['sema'], length=fast, talib=self.talib)
        df['i2'] = df['lema'] + ta.rma(df["close"] - df['lema'], length=slow, talib=self.talib)
        df['i1'] = df['i1'].fillna(0)
        df['i2'] = df['i2'].fillna(0)

        df['macdlead'] = df['i1'] - df['i2']
        self.df["macdlead"] = df["macdlead"].fillna(0)

        df2 = self.df.copy()
        df2 = df2.ta.macd(close=df2['close'], fast=fast, slow=slow, signal=sig, talib=self.talib)
        self.df["macdl"] = df2["MACD_" + str(fast) + "_" + str(slow) + "_" + str(sig)].fillna(0)
        self.df["macdl_sig"] = df2["MACDs_" + str(fast) + "_" + str(slow) + "_" + str(sig)].fillna(0)
        self.df["macdl_hist"] = df2["MACDh_" + str(fast) + "_" + str(slow) + "_" + str(sig)].fillna(0)

        df["macdlead_pc"] = round((df["macdlead"] - df["macdlead"].shift()) / abs(df["macdlead"]) * 100, 2)
        self.df["macdlead_pc"] = df["macdlead_pc"].fillna(0)

    def addOBV(self, ma_period: int = 5) -> None:
        """Add the On-Balance Volume (OBV) to the DataFrame"""

        self.df["obv"] = ta.obv(close=self.df["close"], volume=self.df["volume"], talib=self.talib)
        self.df["obv"] = self.df["obv"].fillna(0)
#        self.df['obvsm'] = ta.sma(self.df["obv"], length=ma_period, talib=self.talib)
        self.df['obvsm'] = ta.vwma(self.df["obv"], volume=self.df["volume"], length=ma_period, talib=self.talib)
        self.df["obvsm"] = self.df["obvsm"].fillna(0)
        self.df["obv_pc"] = round(self.df["obv"].pct_change() * 100, 2)
        self.df["obv_pc"] = self.df["obv_pc"].fillna(0)
        self.df["obvsm_pc"] = round(self.df["obvsm"].pct_change() * 100, 2)
        self.df["obvsm_pc"] = self.df["obvsm_pc"].fillna(0)

    def stochasticRelativeStrengthIndex(self, period) -> DataFrame:
        """Calculate the Stochastic Relative Strength Index (Stochastic RSI)"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 7 or period > 21:
            raise ValueError("Stochastic RSI Period is out of range")

        if "rsi" + str(period) not in self.df:
            self.addRSI(period)

        # calculate relative strength index
        stochrsi = self.calculateStochasticRelativeStrengthIndex(
            self.df["rsi" + str(period)], period
        )
        # default to midway-50 for first entries
        stochrsi = stochrsi.fillna(0.5)
        return stochrsi

    def williamsR(self, period) -> DataFrame:
        """Calculate the Williams %R"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 7 or period > 21:
            raise ValueError("WilliamsR Period is out of range")

        return (
            (self.df["high"].rolling(14).max() - self.df["close"]) /
            (self.df["high"].rolling(14).max() - self.df["low"].rolling(14).min())
        ) * -100

    def addRSI(self, period: int, ma_period: int = 0, addPC: bool = False) -> None:
        """Adds the Relative Strength Index (RSI) to the DataFrame"""

        if not isinstance(period, int):
            raise TypeError("addRSI Period parameter is not perioderic.")

        if not isinstance(ma_period, int):
            raise TypeError("addRSI MA Period parameter is not perioderic.")

        if period < 7 or period > 21:
            raise ValueError("addRSI Period is out of range")

        if ma_period < 5 or ma_period > 25:
            raise ValueError("addRSI MA Period is out of range")

        self.df["rsi" + str(period)] = ta.rsi(close=self.df["close"], length=period, talib=self.talib)
        self.df["rsi" + str(period)] = self.df["rsi" + str(period)].fillna(0)

        if addPC is True:
            self.df["rsi" + str(period) + "_pc"] = round(self.df["rsi" + str(period)].pct_change() * 100, 2)
            self.df["rsi" + str(period) + "_pc"] = self.df["rsi" + str(period) + "_pc"].fillna(0)

        if ma_period >=5:
#           self.df["rsima" + str(ma_period)] = ta.vwma(
#               close=self.df["rsi" + str(period)], volume=self.df["volume"], length=(ma_period), talib=self.talib
#           )
            self.df["rsima" + str(ma_period)] = ta.rma(
                close=self.df["rsi" + str(period)], volume=self.df["volume"], length=(ma_period), talib=self.talib
            )
            self.df["rsima" + str(ma_period)] = self.df["rsima" + str(ma_period)].fillna(0)

            if addPC is True:
                self.df["rsima" + str(ma_period) + "_pc"] = round(self.df["rsima" + str(ma_period)].pct_change() * 100, 2)
                self.df["rsima" + str(ma_period) + "_pc"] = self.df["rsima" + str(ma_period) + "_pc"].fillna(0)

    def addStochasticRSI(self, period: int) -> None:
        """Adds the Stochastic Relative Strength Index (RSI) to the DataFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 7 or period > 21:
            raise ValueError("add Stochastic RSI Period is out of range")

        self.df["stochrsi" + str(period)] = self.stochasticRelativeStrengthIndex(period)
        self.df["stochrsi" + str(period)] = self.df["stochrsi" + str(period)].replace(
            nan, 0.5
        )

        # sma3 stoch rsi
        self.df["smastoch" + str(period)] = (
            100 * self.df["stochrsi" + str(period)].rolling(3, min_periods=1).mean()
        )
        self.df["rsi_value"] = self.df["smastoch" + str(period)]

        # true if sma stochrsi is above the 15
        self.df["rsi15"] = self.df["smastoch" + str(period)] > 15
        self.df["rsi15co"] = self.df.rsi15.ne(self.df.rsi15.shift())
        self.df.loc[self.df["rsi15"] == False, "rsi15co"] = False

        # true if sma stochrsi is below the 85
        self.df["rsi85"] = self.df["smastoch" + str(period)] < 85
        self.df["rsi85co"] = self.df.rsi85.ne(self.df.rsi85.shift())
        self.df.loc[self.df["rsi85"] == False, "rsi85co"] = False

    def addWilliamsR(self, period: int=20) -> None:
        """Adds the Willams %R to the DataFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 7 or period > 21:
            raise ValueError("addWilliamsR Period is out of range")

#        self.df["williamsr" + str(period)] = self.williamsR(period)
#        self.df["williamsr" + str(period)] = self.df["williamsr" + str(period)].replace(
#            nan, -50
#        )
        self.df["williamsr" + str(period)] = ta.willr(high=self.df["high"], low=self.df["low"], close=self.df["close"], length=period, talib=self.talib)
        self.df["williamsr" + str(period)] = self.df["williamsr" + str(period)].replace(nan, 0)

    def seasonalARIMAModel(self) -> SARIMAXResultsWrapper:
        """Returns the Seasonal ARIMA Model for price predictions"""

        # hyperparameters for SARIMAX
        if not self.df.index.freq:
            freq = (
                str(self.df["granularity"].iloc[-1])
                .replace("m", "T")
                .replace("h", "H")
                .replace("d", "D")
            )
            if freq.isdigit():
                freq += "S"
            self.df.index = self.df.index.to_period(freq)
        model = SARIMAX(
            self.df["close"], trend="n", order=(0, 1, 0), seasonal_order=(1, 1, 1, 12)
        )
        return model.fit(disp=-1)

    def seasonalARIMAModelFittedValues(self):  # TODO: annotate return type
        """Returns the Seasonal ARIMA Model for price predictions"""

        return self.seasonalARIMAModel().fittedvalues

    def seasonalARIMAModelPrediction(self, minutes: int = 180) -> tuple:
        """Returns seasonal ARIMA model prediction

        Parameters
        ----------
        minutes     : int
            Number of minutes to predict
        """

        if not isinstance(minutes, int):
            raise TypeError("Prediction minutes is not numeric.")

        if minutes < 1 or minutes > 4320:
            raise ValueError("Predication minutes is out of range")

        results_ARIMA = self.seasonalARIMAModel()

        start_ts = self.df.last_valid_index()
        end_ts = start_ts + timedelta(minutes=minutes)
        pred = results_ARIMA.predict(start=str(start_ts), end=str(end_ts), dynamic=True)

        try:
            if len(pred) == 0:
                df_last = self.df["close"].tail(1)
                return (
                    str(df_last.index.values[0])
                    .replace("T", " ")
                    .replace(".000000000", ""),
                    df_last.values[0],
                )
            else:
                df_last = pred.tail(1)
                return (
                    str(df_last.index.values[0])
                    .replace("T", " ")
                    .replace(".000000000", ""),
                    df_last.values[0],
                )
        except Exception:
            return None

        return None

    def simpleMovingAverage(self, period: int) -> float:
        """Calculates the Simple Moving Average (SMA)"""

        if not isinstance(period, int):
            raise TypeError("SMA Period parameter is not perioderic.")

        if period > self.total_periods or period < 5 or period > 200:
            raise ValueError(f"SMA{period} Period is out of range")

        if len(self.df) < period:
            raise Exception("SMA Data range too small.")

        return self.df.close.rolling(period, min_periods=1).mean()

    def addSMA(self, period: int, addPC: bool = False) -> None:
        """Add the Simple Moving Average (SMA) to the DataFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period > self.total_periods or period < 5 or period > 200:
            raise ValueError(f"addSMA{period} Period is out of range")

        if len(self.df) < period:
            raise Exception("addSMA Data range too small.")

        self.df["sma" + str(period)] = ta.sma(self.df["close"], length=period, talib=self.talib)
        self.df["sma" + str(period)] = self.df["sma" + str(period)].fillna(0)

        if addPC:
            self.df["sma" + str(period) + "_pc"] = round(self.df["sma" + str(period)].pct_change() * 100, 3)

    def addGoldenCross(self) -> None:
        """Add Golden Cross SMA50 over SMA200"""

        if self.total_periods < 200:
            self.df["goldencross"] = False
            return

        if "sma50" not in self.df:
            self.addSMA(50)

        if "sma200" not in self.df:
            self.addSMA(200)

        self.df["goldencross"] = self.df["sma50"] > self.df["sma200"]

    def addDeathCross(self) -> None:
        """Add Death Cross SMA50 over SMA200"""

        if self.total_periods < 200:
            self.df["deathcross"] = False
            self.df["bullsma50"] = False
            return

        if "sma50" not in self.df:
            self.addSMA(50)

        if "sma200" not in self.df:
            self.addSMA(200)

        self.df["deathcross"] = self.df["sma50"] < self.df["sma200"]
        self.df["bullsma50"] = self.df["sma50"] > self.df["sma50"].shift(1)

    def addElderRayIndex(self) -> None:
        """Add Elder Ray Index"""

        if "ema13" not in self.df:
            self.addEMA(13)

        self.df["elder_ray_bull"] = self.df["high"] - self.df["ema13"]
        self.df["elder_ray_bear"] = self.df["low"] - self.df["ema13"]

        # bear power’s value is negative but increasing (i.e. becoming less bearish)
        # bull power’s value is increasing (i.e. becoming more bullish)
        self.df["eri_buy"] = (
            (self.df["elder_ray_bear"] < 0)
            & (self.df["elder_ray_bear"] > self.df["elder_ray_bear"].shift(1))
        ) | ((self.df["elder_ray_bull"] > self.df["elder_ray_bull"].shift(1)))

        # bull power’s value is positive but decreasing (i.e. becoming less bullish)
        # bear power’s value is decreasing (i.e., becoming more bearish)
        self.df["eri_sell"] = (
            (self.df["elder_ray_bull"] > 0)
            & (self.df["elder_ray_bull"] < self.df["elder_ray_bull"].shift(1))
        ) | ((self.df["elder_ray_bear"] < self.df["elder_ray_bear"].shift(1)))

    def getSupportResistanceLevels(self) -> Series:
        """Calculate the Support and Resistance Levels"""

        self.levels = []
        self.__calculateSupportResistenceLevels()
        levels_ts = {}
        for level in self.levels:
            levels_ts[self.df.index[level[0]]] = level[1]
        # add the support levels to the DataFrame
        return Series(levels_ts)

    def printSupportResistanceLevel(self, price: float = 0) -> None:
        if isinstance(price, int) or isinstance(price, float):
            df = self.getSupportResistanceLevels()

            if len(df) > 0:
                df_last = df.tail(1)
                if float(df_last[0]) < price:
                    Logger.info(f" Support level of {str(df_last[0])} formed at {str(df_last.index[0])}")
                elif float(df_last[0]) > price:
                    Logger.info(f" Resistance level of {str(df_last[0])} formed at {str(df_last.index[0])}")
                else:
                    Logger.info(f" Support/Resistance level of {str(df_last[0])} formed at {str(df_last.index[0])}")

    def getResistance(self, price: float = 0) -> float:
        if isinstance(price, int) or isinstance(price, float):
            if price > 0:
                sr = self.getSupportResistanceLevels()
                for r in sr.sort_values():
                    if r > price:
                        return r

        return price

    def getFibonacciUpper(self, price: float = 0) -> float:
        if isinstance(price, int) or isinstance(price, float):
            if price > 0:
                fb = self.getFibonacciRetracementLevels()
                for f in fb.values():
                    if f > price:
                        return f

        return price

    def getTradeExit(self, price: float = 0) -> float:
        if isinstance(price, int) or isinstance(price, float):
            if price > 0:
                r = self.getResistance(price)
                f = self.getFibonacciUpper(price)
                if price < r and price < f:
                    r_margin = ((r - price) / price) * 100
                    f_margin = ((f - price) / price) * 100

                    if r_margin > 1 and f_margin > 1 and r <= f:
                        return r
                    elif r_margin > 1 and f_margin > 1 and f <= r:
                        return f
                    elif r_margin > 1 and f_margin < 1:
                        return r
                    elif f_margin > 1 and r_margin < 1:
                        return f

        return price

    def printSupportResistanceFibonacciLevels(self, price: float = 0) -> str:
        if isinstance(price, int) or isinstance(price, float):
            if price > 0:
                sr = self.getSupportResistanceLevels()

                s = price
                for r in sr.sort_values():
                    if r > price:
                        fb = self.getFibonacciRetracementLevels()

                        l = price
                        for b in fb.values():
                            if b > price:
                                return (f"support: {str(s)}, resistance: {str(r)}, fibonacci (l): {str(l)}, fibonacci (u): {str(b)}")
                            else:
                                l = b

                        break
                    else:
                        s = r

                if len(sr) > 1 and sr.iloc[-1] < price:
                    fb = self.getFibonacciRetracementLevels()

                    l = price
                    for b in fb.values():
                        if b > price:
                            return (f"support: {str(sr.iloc[-1])}, fibonacci (l): {str(l)}, fibonacci (u): {str(b)}")
                        else:
                            l = b

        return ""

    def addEMABuySignals(self) -> None:
        """Adds the EMA12/EMA26 buy and sell signals to the DataFrame"""

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        if not "close" in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if (
            not self.df["close"].dtype == "float64"
            and not self.df["close"].dtype == "int64"
        ):
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64."
            )

        if not "ema8" in self.df.columns:
            self.addEMA(8)

        if not "ema12" in self.df.columns:
            self.addEMA(12)

        if not "ema26" in self.df.columns:
            self.addEMA(26)

        # true if EMA8 is above the EMA12
        self.df["ema8gtema12"] = self.df.ema8 > self.df.ema12
        # true if the current frame is where EMA8 crosses over above
        self.df["ema8gtema12co"] = self.df.ema8gtema12.ne(self.df.ema8gtema12.shift())
        self.df.loc[self.df["ema8gtema12"] == False, "ema8gtema12co"] = False

        # true if the EMA8 is below the EMA12
        self.df["ema8ltema12"] = self.df.ema8 < self.df.ema12
        # true if the current frame is where EMA8 crosses over below
        self.df["ema8ltema12co"] = self.df.ema8ltema12.ne(self.df.ema8ltema12.shift())
        self.df.loc[self.df["ema8ltema12"] == False, "ema8ltema12co"] = False

        # true if EMA12 is above the EMA26
        self.df["ema12gtema26"] = self.df.ema12 > self.df.ema26
        # true if the current frame is where EMA12 crosses over above
        self.df["ema12gtema26co"] = self.df.ema12gtema26.ne(
            self.df.ema12gtema26.shift()
        )
        self.df.loc[self.df["ema12gtema26"] == False, "ema12gtema26co"] = False

        # true if the EMA12 is below the EMA26
        self.df["ema12ltema26"] = self.df.ema12 < self.df.ema26
        # true if the current frame is where EMA12 crosses over below
        self.df["ema12ltema26co"] = self.df.ema12ltema26.ne(
            self.df.ema12ltema26.shift()
        )
        self.df.loc[self.df["ema12ltema26"] == False, "ema12ltema26co"] = False

    def addSMABuySignals(self) -> None:
        """Adds the SMA50/SMA200 buy and sell signals to the DataFrame"""

        if self.total_periods < 200:
            raise ValueError("addSMABuySignals Period is out of range")

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        if not "close" in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if (
            not self.df["close"].dtype == "float64"
            and not self.df["close"].dtype == "int64"
        ):
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64."
            )

        if not "sma50" or not "sma200" in self.df.columns:
            self.addSMA(50)
            self.addSMA(200)

        # true if SMA50 is above the SMA200
        self.df["sma50gtsma200"] = self.df.sma50 > self.df.sma200
        # true if the current frame is where SMA50 crosses over above
        self.df["sma50gtsma200co"] = self.df.sma50gtsma200.ne(
            self.df.sma50gtsma200.shift()
        )
        self.df.loc[self.df["sma50gtsma200"] == False, "sma50gtsma200co"] = False

        # true if the SMA50 is below the SMA200
        self.df["sma50ltsma200"] = self.df.sma50 < self.df.sma200
        # true if the current frame is where SMA50 crosses over below
        self.df["sma50ltsma200co"] = self.df.sma50ltsma200.ne(
            self.df.sma50ltsma200.shift()
        )
        self.df.loc[self.df["sma50ltsma200"] == False, "sma50ltsma200co"] = False

    def addMACDBuySignals(self) -> None:
        """Adds the MACD/Signal buy and sell signals to the DataFrame"""

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        if not "close" in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if (
            not self.df["close"].dtype == "float64"
            and not self.df["close"].dtype == "int64"
        ):
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64."
            )

        if not "macd" or not "signal" in self.df.columns:
            self.addMACD()
            self.addOBV()

        # true if MACD is above the Signal
        self.df["macdgtsignal"] = self.df.macd > self.df.signal
        # true if the current frame is where MACD crosses over above
        self.df["macdgtsignalco"] = self.df.macdgtsignal.ne(
            self.df.macdgtsignal.shift()
        )
        self.df.loc[self.df["macdgtsignal"] == False, "macdgtsignalco"] = False

        # true if the MACD is below the Signal
        self.df["macdltsignal"] = self.df.macd < self.df.signal
        # true if the current frame is where MACD crosses over below
        self.df["macdltsignalco"] = self.df.macdltsignal.ne(
            self.df.macdltsignal.shift()
        )
        self.df.loc[self.df["macdltsignal"] == False, "macdltsignalco"] = False

    def getFibonacciRetracementLevels(self, price: float = 0) -> dict:
        # validates price is numeric
        if not isinstance(price, int) and not isinstance(price, float):
            raise TypeError("Optional price is not numeric.")

        price_min = self.df.close.min()
        price_max = self.df.close.max()

        diff = price_max - price_min

        data = {}

        if price != 0 and (price <= price_min):
            data["ratio1"] = float(self.__truncate(price_min, 2))
        elif price == 0:
            data["ratio1"] = float(self.__truncate(price_min, 2))

        if price != 0 and (price > price_min) and (price <= (price_max - 0.768 * diff)):
            data["ratio1"] = float(self.__truncate(price_min, 2))
            data["ratio0_768"] = float(self.__truncate(price_max - 0.768 * diff, 2))
        elif price == 0:
            data["ratio0_768"] = float(self.__truncate(price_max - 0.768 * diff, 2))

        if (
            price != 0
            and (price > (price_max - 0.768 * diff))
            and (price <= (price_max - 0.618 * diff))
        ):
            data["ratio0_768"] = float(self.__truncate(price_max - 0.768 * diff, 2))
            data["ratio0_618"] = float(self.__truncate(price_max - 0.618 * diff, 2))
        elif price == 0:
            data["ratio0_618"] = float(self.__truncate(price_max - 0.618 * diff, 2))

        if (
            price != 0
            and (price > (price_max - 0.618 * diff))
            and (price <= (price_max - 0.5 * diff))
        ):
            data["ratio0_618"] = float(self.__truncate(price_max - 0.618 * diff, 2))
            data["ratio0_5"] = float(self.__truncate(price_max - 0.5 * diff, 2))
        elif price == 0:
            data["ratio0_5"] = float(self.__truncate(price_max - 0.5 * diff, 2))

        if (
            price != 0
            and (price > (price_max - 0.5 * diff))
            and (price <= (price_max - 0.382 * diff))
        ):
            data["ratio0_5"] = float(self.__truncate(price_max - 0.5 * diff, 2))
            data["ratio0_382"] = float(self.__truncate(price_max - 0.382 * diff, 2))
        elif price == 0:
            data["ratio0_382"] = float(self.__truncate(price_max - 0.382 * diff, 2))

        if (
            price != 0
            and (price > (price_max - 0.382 * diff))
            and (price <= (price_max - 0.286 * diff))
        ):
            data["ratio0_382"] = float(self.__truncate(price_max - 0.382 * diff, 2))
            data["ratio0_286"] = float(self.__truncate(price_max - 0.286 * diff, 2))
        elif price == 0:
            data["ratio0_286"] = float(self.__truncate(price_max - 0.286 * diff, 2))

        if price != 0 and (price > (price_max - 0.286 * diff)) and (price <= price_max):
            data["ratio0_286"] = float(self.__truncate(price_max - 0.286 * diff, 2))
            data["ratio0"] = float(self.__truncate(price_max, 2))
        elif price == 0:
            data["ratio0"] = float(self.__truncate(price_max, 2))

        if price != 0 and (price < (price_max + 0.272 * diff)) and (price >= price_max):
            data["ratio0"] = float(self.__truncate(price_max, 2))
            data["ratio1_272"] = float(self.__truncate(price_max + 0.272 * diff, 2))
        elif price == 0:
            data["ratio1_272"] = float(self.__truncate(price_max + 0.272 * diff, 2))

        if (
            price != 0
            and (price < (price_max + 0.414 * diff))
            and (price >= (price_max + 0.272 * diff))
        ):
            data["ratio1_272"] = float(self.__truncate(price_max, 2))
            data["ratio1_414"] = float(self.__truncate(price_max + 0.414 * diff, 2))
        elif price == 0:
            data["ratio1_414"] = float(self.__truncate(price_max + 0.414 * diff, 2))

        if (
            price != 0
            and (price < (price_max + 0.618 * diff))
            and (price >= (price_max + 0.414 * diff))
        ):
            data["ratio1_618"] = float(self.__truncate(price_max + 0.618 * diff, 2))
        elif price == 0:
            data["ratio1_618"] = float(self.__truncate(price_max + 0.618 * diff, 2))

        return data

    def saveCSV(self, filename: str = "tradingdata.csv") -> None:
        """Saves the DataFrame to an uncompressed CSV."""

        p = compile(r"^[\w\-. ]+$")
        if not p.match(filename):
            raise TypeError("Filename required.")

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        try:
            self.df.to_csv(filename)
        except OSError:
            Logger.critical(f"Unable to save: {filename}")

    def __calculateSupportResistenceLevels(self):
        """Support and Resistance levels. (private function)"""

        for i in range(2, self.df.shape[0] - 2):
            if self.__isSupport(self.df, i):
                l = self.df["low"][i]
                if self.__isFarFromLevel(l):
                    self.levels.append((i, l))
            elif self.__isResistance(self.df, i):
                l = self.df["high"][i]
                if self.__isFarFromLevel(l):
                    self.levels.append((i, l))
        return self.levels

    def __isSupport(self, df, i) -> bool:
        """Is support level? (private function)"""

        try:
            c1 = df["low"][i] < df["low"][i - 1]
            c2 = df["low"][i] < df["low"][i + 1]
            c3 = df["low"][i + 1] < df["low"][i + 2]
            c4 = df["low"][i - 1] < df["low"][i - 2]
            support = c1 and c2 and c3 and c4
            return support
        except:
            support = False
            return support

    def __isResistance(self, df, i) -> bool:
        """Is resistance level? (private function)"""

        try:  
            c1 = df["high"][i] > df["high"][i - 1]
            c2 = df["high"][i] > df["high"][i + 1]
            c3 = df["high"][i + 1] > df["high"][i + 2]
            c4 = df["high"][i - 1] > df["high"][i - 2]
            resistance = c1 and c2 and c3 and c4
            return resistance
        except:
            resistance = False
            return resistance

    def __isFarFromLevel(self, l) -> float:
        """Is far from support level? (private function)"""

        s = mean(self.df["high"] - self.df["low"])
        return np_sum([abs(l - x) < s for x in self.levels]) == 0

    def __truncate(self, f, n) -> float:
        return floor(f * 10 ** n) / 10 ** n
