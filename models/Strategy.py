from datetime import datetime
from pandas import DataFrame
from models.PyCryptoBot import PyCryptoBot
from models.AppState import AppState
from models.helper.LogHelper import Logger
import sys


class Strategy:
    def __init__(
        self,
        app: PyCryptoBot = None,
        state: AppState = AppState,
        df: DataFrame = DataFrame,
        iterations: int = 0,
    ) -> None:
        if not isinstance(df, DataFrame):
            raise TypeError("'df' not a Pandas dataframe")

        if len(df) == 0:
            raise ValueError("'df' is empty")

        self._action = "WAIT"
        self.app = app
        self.state = state
        self._df = df
        self._df_last = app.getInterval(df, iterations)

    def isBuySignal(
        self, price, now: datetime = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    ) -> bool:
        # required technical indicators or candle sticks for buy signal strategy
        required_indicators = [
            "ema12gtema26co",
            "macdgtsignal",
            "goldencross",
            "obv_pc",
            "eri_buy",
        ]

        for indicator in required_indicators:
            if indicator not in self._df_last:
                raise AttributeError(f"'{indicator}' not in Pandas dataframe")

        # buy signal exclusion (if disabled, do not buy within 3% of the dataframe close high)
        if (
            self.state.last_action == "SELL"
            and self.app.disableBuyNearHigh() is True
            and (
                price
                > (self._df["close"].max() * (1 - self.app.noBuyNearHighPcnt() / 100))
            )
        ):
            log_text = (
                str(now)
                + " | "
                + self.app.getMarket()
                + " | "
                + self.app.printGranularity()
                + " | Ignoring Buy Signal (price "
                + str(price)
                + " within "
                + str(self.app.noBuyNearHighPcnt())
                + "% of high "
                + str(self._df["close"].max())
                + ")"
            )
            Logger.warning(log_text)

            return False

        # if EMA, MACD are disabled, do not buy
        if self.app.disableBuyEMA() and self.app.disableBuyMACD():
            log_text = (f"{str(now)} | {self.app.getMarket()} | {self.app.printGranularity()} | EMA, MACD indicators are disabled")
            Logger.warning(log_text)

            return False

        # criteria for a buy signal 1
        if (
            (
                bool(self._df_last["ema12gtema26co"].values[0]) is True
                or self.app.disableBuyEMA()
            )
            and (
                bool(self._df_last["macdgtsignal"].values[0]) is True
                or self.app.disableBuyMACD()
            )
            and (
                bool(self._df_last["goldencross"].values[0]) is True
                or self.app.disableBullOnly()
            )
            and (
                float(self._df_last["obv_pc"].values[0]) > -5
                or self.app.disableBuyOBV()
            )
            and (
                bool(self._df_last["eri_buy"].values[0]) is True
                or self.app.disableBuyElderRay()
            )
            and self.state.last_action != "BUY"
        ):  # required for all strategies

            Logger.debug("*** Buy Signal ***")
            for indicator in required_indicators:
                Logger.debug(f"{indicator}: {self._df_last[indicator].values[0]}")
            Logger.debug(f"last_action: {self.state.last_action}")

            return True

        # criteria for buy signal 2 (optionally add additional buy singals)
        elif (
            (
                bool(self._df_last["ema12gtema26co"].values[0]) is True
                or self.app.disableBuyEMA()
            )
            and bool(self._df_last["macdgtsignalco"].values[0]) is True
            and (
                bool(self._df_last["goldencross"].values[0]) is True
                or self.app.disableBullOnly()
            )
            and (
                float(self._df_last["obv_pc"].values[0]) > -5
                or self.app.disableBuyOBV()
            )
            and (
                bool(self._df_last["eri_buy"].values[0]) is True
                or self.app.disableBuyElderRay()
            )
            and self.state.last_action != "BUY"
        ):  # required for all strategies

            Logger.debug("*** Buy Signal ***")
            for indicator in required_indicators:
                Logger.debug(f"{indicator}: {self._df_last[indicator].values[0]}")
            Logger.debug(f"last_action: {self.state.last_action}")

            return True

        return False

    def isSellSignal(self) -> bool:
        # required technical indicators or candle sticks for buy signal strategy
        required_indicators = ["ema12ltema26co", "macdltsignal"]

        for indicator in required_indicators:
            if indicator not in self._df_last:
                raise AttributeError(f"'{indicator}' not in Pandas dataframe")

        # criteria for a sell signal 1
        if (
            bool(self._df_last["ema12ltema26co"].values[0]) is True
            and (
                bool(self._df_last["macdltsignal"].values[0]) is True
                or self.app.disableBuyMACD()
            )
            and self.state.last_action not in ["", "SELL"]
        ):

            Logger.debug("*** Sell Signal ***")
            for indicator in required_indicators:
                Logger.debug(f"{indicator}: {self._df_last[indicator].values[0]}")
            Logger.debug(f"last_action: {self.state.last_action}")

            return True

        return False

    def isSellTrigger(
        self,
        price: float = 0.0,
        price_exit: float = 0.0,
        margin: float = 0.0,
        change_pcnt_high: float = 0.0,
        obv_pc: float = 0.0,
        macdltsignal: bool = False,
    ) -> bool:
        # set to true for verbose debugging
        debug = False
        
        if debug:
            Logger.warning("\n*** isSellTrigger ***\n")
            Logger.warning("-- ignoring sell signal --")
            Logger.warning(f"self.app.nosellminpcnt is None (nosellminpcnt: {self.app.nosellminpcnt})")
            Logger.warning(f"margin >= self.app.nosellminpcnt (margin: {margin})")
            Logger.warning(f"margin <= self.app.nosellmaxpcnt (nosellmaxpcnt: {self.app.nosellmaxpcnt})")
            Logger.warning("\n")
        
        if (
            ((self.app.nosellminpcnt is not None)
                and (margin >= self.app.nosellminpcnt))
                and ((self.app.nosellmaxpcnt is not None)
                and (margin <= self.app.nosellmaxpcnt)
            )):
                log_text = "! Ignore Sell Signal (Within No-Sell Bounds)"
                Logger.warning(log_text)
                return False

        if debug:
            Logger.warning("\n*** isSellTrigger ***\n")
            Logger.warning("-- loss failsafe sell at fibonacci band --")
            Logger.warning(f"self.app.disableFailsafeFibonacciLow() is False (actual: {self.app.disableFailsafeFibonacciLow()})")
            Logger.warning(f"self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()})")
            Logger.warning(f"self.app.sellLowerPcnt() is None (actual: {self.app.sellLowerPcnt()})")
            Logger.warning(f"self.state.fib_low {self.state.fib_low} > 0")
            Logger.warning(f"self.state.fib_low {self.state.fib_low} >= {float(price)}")
            Logger.warning(f"(self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()}) or margin ({margin}) > 0)")
            Logger.warning("\n")

        # loss failsafe sell at fibonacci band
        if (
            self.app.disableFailsafeFibonacciLow() is False
            and self.app.allowSellAtLoss()
            and self.app.sellLowerPcnt() is None
            and self.state.fib_low > 0
            and self.state.fib_low >= float(price)
            and (self.app.allowSellAtLoss() or margin > 0)
        ):
            log_text = (f"! Loss Failsafe Triggered (Fibonacci Band: {str(self.state.fib_low)})")
            Logger.warning(log_text)
            self.app.notifyTelegram(f"{self.app.getMarket()} ({self.app.printGranularity()}) {log_text}")
            return True

        if debug:
            Logger.warning("-- loss failsafe sell at trailing_stop_loss --")
            Logger.warning(f"self.app.trailingStopLoss() != None (actual: {self.app.trailingStopLoss()})")
            Logger.warning(f"change_pcnt_high ({change_pcnt_high}) < self.app.trailingStopLoss() ({self.app.trailingStopLoss()})")
            Logger.warning(f"margin ({margin}) > self.app.trailingStopLossTrigger() ({self.app.trailingStopLossTrigger()})")
            Logger.warning(f"(self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()}) or margin ({margin}) > 0)")
            Logger.warning("\n")

        # loss failsafe sell at trailing_stop_loss
        if (
            self.app.trailingStopLoss() != None
            and change_pcnt_high < self.app.trailingStopLoss()
            and margin > self.app.trailingStopLossTrigger()
            and (self.app.allowSellAtLoss() or margin > 0)):
            log_text = (f"! Trailing Stop Loss Triggered (< {str(self.app.trailingStopLoss())}%)")
            Logger.warning(log_text)
            self.app.notifyTelegram(f"{self.app.getMarket()} ({self.app.printGranularity()}) {log_text}")
            return True

        if debug:
            Logger.warning("-- loss failsafe sell at sell_lower_pcnt --")
            Logger.warning(f"self.app.disableFailsafeLowerPcnt() is False (actual: {self.app.disableFailsafeLowerPcnt()})")
            Logger.warning(f"and self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()})")
            Logger.warning(f"and self.app.sellLowerPcnt() != None (actual: {self.app.sellLowerPcnt()})")
            Logger.warning(f"and margin ({margin}) < self.app.sellLowerPcnt() ({self.app.sellLowerPcnt()})")
            Logger.warning(f"(self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()}) or margin ({margin}) > 0)")
            Logger.warning("\n")

        # loss failsafe sell at sell_lower_pcnt
        if (
            self.app.disableFailsafeLowerPcnt() is False
            and self.app.allowSellAtLoss()
            and self.app.sellLowerPcnt() != None
            and margin < self.app.sellLowerPcnt()
            and (self.app.allowSellAtLoss() or margin > 0)
        ):
            log_text = ("! Loss Failsafe Triggered (< " + str(self.app.sellLowerPcnt()) + "%)")
            Logger.warning(log_text)
            self.app.notifyTelegram(f"{self.app.getMarket()} ({self.app.printGranularity()}) {log_text}")
            return True

        if debug:
            Logger.warning("-- profit bank at sell_upper_pcnt --")
            Logger.warning(
                f"self.app.disableProfitbankUpperPcnt() is False (actual: {self.app.disableProfitbankUpperPcnt()})"
            )
            Logger.warning(
                f"and self.app.sellUpperPcnt() != None (actual: {self.app.sellUpperPcnt()})"
            )
            Logger.warning(
                f"and margin ({margin}) > self.app.sellUpperPcnt() ({self.app.sellUpperPcnt()})"
            )
            Logger.warning(
                f"(self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()}) or margin ({margin}) > 0)"
            )
            Logger.warning("\n")

        # profit bank at sell_upper_pcnt
        if (
            self.app.disableProfitbankUpperPcnt() is False
            and self.app.sellUpperPcnt() != None
            and margin > self.app.sellUpperPcnt()
            and (self.app.allowSellAtLoss() or margin > 0)
        ):
            log_text = (
                f"! Profit Bank Triggered (> {str(self.app.sellUpperPcnt())}%)"
            )
            Logger.warning(log_text)
            self.app.notifyTelegram(f"{self.app.getMarket()} ({self.app.printGranularity()}) {log_text}")
            return True

        if debug:
            Logger.warning("-- profit bank when strong reversal detected --")
            Logger.warning(
                f"self.app.sellAtResistance() is True (actual {self.app.sellAtResistance()})"
            )
            Logger.warning(f"and price ({price}) > 0")
            Logger.warning(f"and price ({price}) >= price_exit ({price_exit})")
            Logger.warning(
                f"(self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()}) or margin ({margin}) > 0)"
            )
            Logger.warning("\n")

        # profit bank when strong reversal detected
        if (
            self.app.sellAtResistance() is True
            and margin >= 2
            and price > 0
            and price >= price_exit
            and (self.app.allowSellAtLoss() or margin > 0)
        ):
            log_text = "! Profit Bank Triggered (Selling At Resistance)"
            Logger.warning(log_text)
            if not (not self.app.allowSellAtLoss() and margin <= 0):
                self.app.notifyTelegram(f"{self.app.getMarket()} ({self.app.printGranularity()}) {log_text}")
            return True

        return False

    def isWaitTrigger(self, margin: float = 0.0, goldencross: bool = False):
        # set to true for verbose debugging
        debug = False

        if debug and self.state.action != "WAIT":
            Logger.warning("\n*** isWaitTrigger ***\n")

        if debug and self.state.action == "BUY":
            Logger.warning("-- if bear market and bull only return true to abort buy --")
            Logger.warning(f"self.state.action == 'BUY' (actual: {self.state.action})")
            Logger.warning(f"and self.app.disableBullOnly() is True (actual: {self.app.disableBullOnly()})")
            Logger.warning(f"and goldencross is False (actual: {goldencross})")
            Logger.warning("\n")

        # if bear market and bull only return true to abort buy
        if (
            self.state.action == "BUY"
            and not self.app.disableBullOnly()
            and not goldencross
        ):
            log_text = "! Ignore Buy Signal (Bear Buy In Bull Only)"
            Logger.warning(log_text)
            return True

        if debug and self.state.action == "SELL":
            Logger.warning("-- configuration specifies to not sell at a loss --")
            Logger.warning(f"self.state.action == 'SELL' (actual: {self.state.action})")
            Logger.warning(f"and self.app.allowSellAtLoss() is False (actual: {self.app.allowSellAtLoss()})")
            Logger.warning(f"and margin ({margin}) <= 0")
            Logger.warning("\n")

        # configuration specifies to not sell at a loss
        if (
            self.state.action == "SELL"
            and not self.app.allowSellAtLoss()
            and margin <= 0
        ):
            log_text = "! Ignore Sell Signal (No Sell At Loss)"
            Logger.warning(log_text)
            return True

        if debug and self.state.action == "SELL":
            Logger.warning(
                "-- configuration specifies not to sell within min and max margin percent bounds --"
            )
            Logger.warning(f"self.state.action == 'SELL' (actual: {self.state.action})")
            Logger.warning(
                f"(self.app.nosellminpcnt is not None (actual: {self.app.nosellminpcnt})) and (margin ({margin}) >= self.app.nosellminpcnt ({self.app.nosellminpcnt}))"
            )
            Logger.warning(
                f"(self.app.nosellmaxpcnt is not None (actual: {self.app.nosellmaxpcnt})) and (margin ({margin}) <= self.app.nosellmaxpcnt ({self.app.nosellmaxpcnt}))"
            )
            Logger.warning("\n")

        # configuration specifies not to sell within min and max margin percent bounds
        if (
            self.state.action == "SELL"
            and (
                (self.app.nosellminpcnt is not None)
                and (margin >= self.app.nosellminpcnt)
            )
            and (
                (self.app.nosellmaxpcnt is not None)
                and (margin <= self.app.nosellmaxpcnt)
            )
        ):
            log_text = "! Ignore Sell Signal (Within No-Sell Bounds)"
            Logger.warning(log_text)
            return True

        return False

    def getAction(self, price):
        if self.isBuySignal(price):
            return "BUY"
        elif self.isSellSignal():
            return "SELL"
        else:
            return "WAIT"
