from datetime import datetime
from pandas import DataFrame
from models.PyCryptoBot import PyCryptoBot
from models.PyCryptoBot import truncate as _truncate
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
        self, app, price, now: datetime = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    ) -> bool:

        # set to true for verbose debugging
        debug = False

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
            if not app.isSimulation() or (
                app.isSimulation() and not app.simResultOnly()
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

        ## if last_action was set to "WAIT" due to an API problem, do not buy
        if ( self.state.last_action == "WAIT"):
            log_text = (f"{str(now)} | {self.app.getMarket()} | {self.app.printGranularity()} | last_action is WAIT, do not buy yet")
            Logger.warning(log_text)
            return False

        # if EMA, MACD are disabled, do not buy
        if self.app.disableBuyEMA() and self.app.disableBuyMACD():
            log_text = f"{str(now)} | {self.app.getMarket()} | {self.app.printGranularity()} | EMA, MACD indicators are disabled"
            Logger.warning(log_text)

            return False

        # initial funds check
        if self.app.enableinsufficientfundslogging and self.app.insufficientfunds:
            # Logger.warning(f"{str(now)} | Insufficient funds, ignoring buy signal.")
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

            if debug:
                Logger.debug("*** Buy Signal ***")
                for indicator in required_indicators:
                    Logger.debug(f"{indicator}: {self._df_last[indicator].values[0]}")
                Logger.debug(f"last_action: {self.state.last_action}")

            return True

        # criteria for buy signal 2 (optionally add additional buy signals)
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

            if debug:
                Logger.debug("*** Buy Signal ***")
                for indicator in required_indicators:
                    Logger.debug(f"{indicator}: {self._df_last[indicator].values[0]}")
                Logger.debug(f"last_action: {self.state.last_action}")

            return True

        return False

    def isSellSignal(self) -> bool:
        # set to true for verbose debugging
        debug = False
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

            if debug:
                Logger.debug("*** Sell Signal ***")
                for indicator in required_indicators:
                    Logger.debug(f"{indicator}: {self._df_last[indicator].values[0]}")
                Logger.debug(f"last_action: {self.state.last_action}")

            return True

        return False

    def isSellTrigger(
        self,
        app,
        state,
        price: float = 0.0,
        price_exit: float = 0.0,
        margin: float = 0.0,
        change_pcnt_high: float = 0.0,
        obv_pc: float = 0.0,
        macdltsignal: bool = False,
    ) -> bool:
        # set to true for verbose debugging
        debug = False

        # preventloss - attempt selling before margin drops below 0%
        if self.app.preventLoss():
            if state.prevent_loss == 0 and margin > self.app.preventLossTrigger():
                state.prevent_loss = 1
                Logger.warning(f"{self.app.getMarket()} - reached prevent loss trigger of {self.app.preventLossTrigger()}%.  Watch margin ({self.app.preventLossMargin()}%) to prevent loss.")
            elif (
                    state.prevent_loss == 1 and margin <= self.app.preventLossMargin()
                ) or ( # trigger of 0 disables trigger check and only checks margin set point
                    self.app.preventLossTrigger() == 0 and margin <= self.app.preventLossMargin()
                ):
                Logger.warning(f"{self.app.getMarket()} - time to sell before losing funds! Prevent Loss Activated!")
                self.app.notifyTelegram(f"{self.app.getMarket()} - time to sell before losing funds! Prevent Loss Activated!")
                return True

        # check sellatloss and nosell bounds before continuing
        if not self.app.allowSellAtLoss() and margin <= 0:
            return False
        elif (
            (self.app.nosellminpcnt is not None) and (margin >= self.app.nosellminpcnt)
        ) and (
            (self.app.nosellmaxpcnt is not None) and (margin <= self.app.nosellmaxpcnt)
        ):
            return False

        if debug:
            Logger.debug(f"Trailing Stop Loss Enabled {self.app.trailingStopLoss()}")
            Logger.debug(f"Change Percentage {change_pcnt_high} < Stop Loss Percent {self.app.trailingStopLoss()} = {change_pcnt_high < self.app.trailingStopLoss()}")
            Logger.debug(f"Margin {margin} > Stop Loss Trigger  {self.app.trailingStopLossTrigger()} = {margin > self.app.trailingStopLossTrigger()}")
        # loss failsafe sell at trailing_stop_loss
        if self.app.trailingStopLoss() != None:
            if margin > self.app.trailingStopLossTrigger():
                state.tsl_triggered = 1

            if state.tsl_triggered == 1 and change_pcnt_high < self.app.trailingStopLoss():
                log_text = f"! Trailing Stop Loss Triggered (< {str(self.app.trailingStopLoss())}%)"
                if not app.isSimulation() or (
                    app.isSimulation() and not app.simResultOnly()
                ):
                    Logger.warning(log_text)

                self.app.notifyTelegram(
                    f"{self.app.getMarket()} ({self.app.printGranularity()}) {log_text}"
                )
                return True

        if debug:
            Logger.debug("-- loss failsafe sell at sell_lower_pcnt --")
            Logger.debug(
                f"self.app.disableFailsafeLowerPcnt() is False (actual: {self.app.disableFailsafeLowerPcnt()})"
            )
            Logger.debug(
                f"and self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()})"
            )
            Logger.debug(
                f"and self.app.sellLowerPcnt() != None (actual: {self.app.sellLowerPcnt()})"
            )
            Logger.debug(
                f"and margin ({margin}) < self.app.sellLowerPcnt() ({self.app.sellLowerPcnt()})"
            )
            Logger.debug(
                f"(self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()}) or margin ({margin}) > 0)"
            )
            Logger.debug("\n")

        # loss failsafe sell at sell_lower_pcnt
        if (
            self.app.disableFailsafeLowerPcnt() is False
            and self.app.allowSellAtLoss()
            and self.app.sellLowerPcnt() != None
            and margin < self.app.sellLowerPcnt()
        ):
            log_text = (
                "! Loss Failsafe Triggered (< " + str(self.app.sellLowerPcnt()) + "%)"
            )
            Logger.warning(log_text)
            self.app.notifyTelegram(
                f"{self.app.getMarket()} ({self.app.printGranularity()}) {log_text}"
            )
            return True

        if debug:
            Logger.debug("\n*** isSellTrigger ***\n")
            Logger.debug("-- ignoring sell signal --")
            Logger.debug(
                f"self.app.nosellminpcnt is None (nosellminpcnt: {self.app.nosellminpcnt})"
            )
            Logger.debug(f"margin >= self.app.nosellminpcnt (margin: {margin})")
            Logger.debug(
                f"margin <= self.app.nosellmaxpcnt (nosellmaxpcnt: {self.app.nosellmaxpcnt})"
            )
            Logger.debug("\n")

        if debug:
            Logger.debug("\n*** isSellTrigger ***\n")
            Logger.debug("-- loss failsafe sell at fibonacci band --")
            Logger.debug(
                f"self.app.disableFailsafeFibonacciLow() is False (actual: {self.app.disableFailsafeFibonacciLow()})"
            )
            Logger.debug(
                f"self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()})"
            )
            Logger.debug(
                f"self.app.sellLowerPcnt() is None (actual: {self.app.sellLowerPcnt()})"
            )
            Logger.debug(f"self.state.fib_low {self.state.fib_low} > 0")
            Logger.debug(f"self.state.fib_low {self.state.fib_low} >= {float(price)}")
            Logger.debug(
                f"(self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()}) or margin ({margin}) > 0)"
            )
            Logger.debug("\n")

        # loss failsafe sell at fibonacci band
        if (
            self.app.disableFailsafeFibonacciLow() is False
            and self.app.allowSellAtLoss()
            and self.app.sellLowerPcnt() is None
            and self.state.fib_low > 0
            and self.state.fib_low >= float(price)
        ):
            log_text = (
                f"! Loss Failsafe Triggered (Fibonacci Band: {str(self.state.fib_low)})"
            )
            Logger.warning(log_text)
            self.app.notifyTelegram(
                f"{self.app.getMarket()} ({self.app.printGranularity()}) {log_text}"
            )
            return True

        if debug:
            Logger.debug("-- loss failsafe sell at trailing_stop_loss --")
            Logger.debug(
                f"self.app.trailingStopLoss() != None (actual: {self.app.trailingStopLoss()})"
            )
            Logger.debug(
                f"change_pcnt_high ({change_pcnt_high}) < self.app.trailingStopLoss() ({self.app.trailingStopLoss()})"
            )
            Logger.debug(
                f"margin ({margin}) > self.app.trailingStopLossTrigger() ({self.app.trailingStopLossTrigger()})"
            )
            Logger.debug(
                f"(self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()}) or margin ({margin}) > 0)"
            )
            Logger.debug("\n")

        if debug:
            Logger.debug("-- profit bank at sell_upper_pcnt --")
            Logger.debug(
                f"self.app.disableProfitbankUpperPcnt() is False (actual: {self.app.disableProfitbankUpperPcnt()})"
            )
            Logger.debug(
                f"and self.app.sellUpperPcnt() != None (actual: {self.app.sellUpperPcnt()})"
            )
            Logger.debug(
                f"and margin ({margin}) > self.app.sellUpperPcnt() ({self.app.sellUpperPcnt()})"
            )
            Logger.debug(
                f"(self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()}) or margin ({margin}) > 0)"
            )
            Logger.debug("\n")

        # profit bank at sell_upper_pcnt
        if (
            self.app.disableProfitbankUpperPcnt() is False
            and self.app.sellUpperPcnt() != None
            and margin > self.app.sellUpperPcnt()
        ):
            log_text = f"! Profit Bank Triggered (> {str(self.app.sellUpperPcnt())}%)"
            if not app.isSimulation() or (
                app.isSimulation() and not app.simResultOnly()
            ):
                Logger.warning(log_text)
            self.app.notifyTelegram(
                f"{self.app.getMarket()} ({self.app.printGranularity()}) {log_text}"
            )
            return True

        if debug:
            Logger.debug("-- profit bank when strong reversal detected --")
            Logger.debug(
                f"self.app.sellAtResistance() is True (actual {self.app.sellAtResistance()})"
            )
            Logger.debug(f"and price ({price}) > 0")
            Logger.debug(f"and price ({price}) >= price_exit ({price_exit})")
            Logger.debug(
                f"(self.app.allowSellAtLoss() is True (actual: {self.app.allowSellAtLoss()}) or margin ({margin}) > 0)"
            )
            Logger.debug("\n")

        # profit bank when strong reversal detected
        if (
            self.app.sellAtResistance() is True
            and margin >= 2
            and price > 0
            and price >= price_exit
            and (self.app.allowSellAtLoss() or margin > 0)
        ):
            log_text = "! Profit Bank Triggered (Selling At Resistance)"
            if not app.isSimulation() or (
                app.isSimulation() and not app.simResultOnly()
            ):
                Logger.warning(log_text)
            if not (not self.app.allowSellAtLoss() and margin <= 0):
                self.app.notifyTelegram(
                    f"{self.app.getMarket()} ({self.app.printGranularity()}) {log_text}"
                )
            return True

        return False

    def isWaitTrigger(self, app, margin: float = 0.0, goldencross: bool = False):
        # set to true for verbose debugging
        debug = False

        if debug and self.state.action != "WAIT":
            Logger.debug("\n*** isWaitTrigger ***\n")

        if debug and self.state.action == "BUY":
            Logger.debug(
                "-- if bear market and bull only return true to abort buy --"
            )
            Logger.debug(f"self.state.action == 'BUY' (actual: {self.state.action})")
            Logger.debug(
                f"and self.app.disableBullOnly() is True (actual: {self.app.disableBullOnly()})"
            )
            Logger.debug(f"and goldencross is False (actual: {goldencross})")
            Logger.debug("\n")

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
            Logger.debug("-- configuration specifies to not sell at a loss --")
            Logger.debug(f"self.state.action == 'SELL' (actual: {self.state.action})")
            Logger.debug(
                f"and self.app.allowSellAtLoss() is False (actual: {self.app.allowSellAtLoss()})"
            )
            Logger.debug(f"and margin ({margin}) <= 0")
            Logger.debug("\n")

        # configuration specifies to not sell at a loss
        if (
            self.state.action == "SELL"
            and not self.app.allowSellAtLoss()
            and margin <= 0
        ):
            if not app.isSimulation() or (
                app.isSimulation() and not app.simResultOnly()
            ):
                log_text = "! Ignore Sell Signal (No Sell At Loss)"
                Logger.warning(log_text)
            return True

        if debug and self.state.action == "SELL":
            Logger.debug(
                "-- configuration specifies not to sell within min and max margin percent bounds --"
            )
            Logger.debug(f"self.state.action == 'SELL' (actual: {self.state.action})")
            Logger.debug(
                f"(self.app.nosellminpcnt is not None (actual: {self.app.nosellminpcnt})) and (margin ({margin}) >= self.app.nosellminpcnt ({self.app.nosellminpcnt}))"
            )
            Logger.debug(
                f"(self.app.nosellmaxpcnt is not None (actual: {self.app.nosellmaxpcnt})) and (margin ({margin}) <= self.app.nosellmaxpcnt ({self.app.nosellmaxpcnt}))"
            )
            Logger.debug("\n")

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
            if not app.isSimulation() or (
                app.isSimulation() and not app.simResultOnly()
            ):
                Logger.warning("! Ignore Sell Signal (Within No-Sell Bounds)")
            return True

        return False

    def checkTrailingBuy(self, app, state, price: float = 0.0):
        # If buy signal, save the price and check if it decreases before buying.
        trailing_buy_logtext = ""
        waitpcnttext = ""
        immediate_action = False
        if state.trailing_buy == 0:
            state.waiting_buy_price = price
            pricechange = 0
        elif state.trailing_buy == 1 and state.waiting_buy_price > 0:
            pricechange = (
                (price - state.waiting_buy_price) / state.waiting_buy_price * 100
            )
            if price < state.waiting_buy_price:
                state.waiting_buy_price = price
                waitpcnttext += f"Price decreased - resetting wait price. "

        waitpcnttext += f"** {app.getMarket()} - "
        if pricechange < app.getTrailingBuyPcnt(): # get pcnt from config, if not, use 0%
            state.action = "WAIT"
            state.trailing_buy = 1
            if app.getTrailingBuyPcnt() > 0:
                trailing_buy_logtext = f" - Wait Chg: {_truncate(pricechange,2)}%/{app.getTrailingBuyPcnt()}%"
                waitpcnttext += f"Waiting to buy until {state.waiting_buy_price} increases {app.getTrailingBuyPcnt()}% - change {_truncate(pricechange,2)}%"
            else:
                trailing_buy_logtext = f" - Wait Chg: {_truncate(pricechange,2)}%"
                waitpcnttext += f"Waiting to buy until {state.waiting_buy_price} stops decreasing - change {_truncate(pricechange,2)}%"
        else:
            state.action = "BUY"
            state.trailing_buy = 1
            if app.trailingImmediateBuy():
                immediate_action = True
            trailing_buy_logtext = f" - Ready Chg: {_truncate(pricechange,2)}%/{app.getTrailingBuyPcnt()}%"
            waitpcnttext += f"Ready to buy. {state.waiting_buy_price} change of {_truncate(pricechange,2)}% is above setting of {app.getTrailingBuyPcnt()}%"

        if app.isVerbose() and (
            not app.isSimulation()
            or (app.isSimulation() and not app.simResultOnly())
        ):
            Logger.info(waitpcnttext)

        return state.action, state.trailing_buy, trailing_buy_logtext, immediate_action


    def getAction(self, app, price, dt):
        if self.isBuySignal(app, price, dt):
            return "BUY"
        elif self.isSellSignal():
            return "SELL"
        else:
            return "WAIT"
