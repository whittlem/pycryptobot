import os
import sys
import time
import math
import random
import sched
import signal
import functools
import pandas as pd
from typing import Union
from datetime import datetime, timedelta
from urllib3.exceptions import ReadTimeoutError

from models.BotConfig import BotConfig
from models.exchange.ExchangesEnum import Exchange
from models.exchange.Granularity import Granularity
from models.exchange.binance import WebSocketClient as BWebSocketClient
from models.exchange.coinbase_pro import WebSocketClient as CWebSocketClient
from models.exchange.kucoin import WebSocketClient as KWebSocketClient
from models.exchange.binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import AuthAPI as CBAuthAPI, PublicAPI as CBPublicAPI
from models.exchange.kucoin import AuthAPI as KAuthAPI, PublicAPI as KPublicAPI
from models.helper.TelegramBotHelper import TelegramBotHelper
from models.helper.MarginHelper import calculate_margin
from models.TradingAccount import TradingAccount
from models.Stats import Stats
from models.AppState import AppState
from models.helper.TextBoxHelper import TextBox
from models.helper.LogHelper import Logger
from models.Trading import TechnicalAnalysis
from models.Strategy import Strategy
from views.TradingGraphs import TradingGraphs

pd.set_option("display.float_format", "{:.8f}".format)


def signal_handler(signum):
    if signum == 2:
        print("Please be patient while websockets terminate!")
        # Logger.debug(frame)
        return


class PyCryptoBot(BotConfig):
    def __init__(self, config_file: str = None, exchange: Exchange = None):
        self.config_file = config_file or "config.json"
        self.exchange = exchange
        super(PyCryptoBot, self).__init__(
            filename=self.config_file, exchange=self.exchange
        )

        self.s = sched.scheduler(time.time, time.sleep)

        self.price = 0
        self.is_live = 0
        self.websocket = None
        self.account = None
        self.state = None
        self.technical_analysis = None
        self.ticker_self = None
        self.df_last = pd.DataFrame()
        self.trading_data = pd.DataFrame()
        self.telegram_bot = TelegramBotHelper(self)

        # self.state.initLastAction()

    def execute_job(self):
        """Trading bot job which runs at a scheduled interval"""

        print("execute_job")

        if self.is_live:
            self.state.account.mode = "live"
        else:
            self.state.account.mode = "test"

        # This is used to control some API calls when using websockets
        last_api_call_datetime = datetime.now() - self.state.last_api_call_datetime
        if last_api_call_datetime.seconds > 60:
            self.state.last_api_call_datetime = datetime.now()

        # This is used by the telegram bot
        # If it not enabled in config while will always be False
        if not self.is_sim:
            controlstatus = self.telegram_bot.checkbotcontrolstatus()
            while controlstatus == "pause" or controlstatus == "paused":
                if controlstatus == "pause":
                    text_box = TextBox(80, 22)
                    text_box.singleLine()
                    text_box.center(f"Pausing Bot {self.market}")
                    text_box.singleLine()
                    Logger.debug("Pausing Bot.")
                    print(str(datetime.now()).format() + " - Bot is paused")
                    self.notify_telegram(f"{self.market} bot is paused")
                    self.telegram_bot.updatebotstatus("paused")
                    if self.websocket:
                        Logger.info("Stopping self.websocket...")
                        self.websocket.close()

                time.sleep(30)
                controlstatus = self.telegram_bot.checkbotcontrolstatus()

            if controlstatus == "start":
                text_box = TextBox(80, 22)
                text_box.singleLine()
                text_box.center(f"Restarting Bot {self.market}")
                text_box.singleLine()
                Logger.debug("Restarting Bot.")
                self.notify_telegram(f"{self.market} bot has restarted")
                self.telegram_bot.updatebotstatus("active")
                self.read_config(self.exchange)
                if self.websocket:
                    Logger.info("Starting self.websocket...")
                    self.websocket.start()

            if controlstatus == "exit":
                text_box = TextBox(80, 22)
                text_box.singleLine()
                text_box.center(f"Closing Bot {self.market}")
                text_box.singleLine()
                Logger.debug("Closing Bot.")
                self.notify_telegram(f"{self.market} bot is stopping")
                self.telegram_bot.removeactivebot()
                sys.exit(0)

            if controlstatus == "reload":
                text_box = TextBox(80, 22)
                text_box.singleLine()
                text_box.center(f"Reloading config parameters {self.market}")
                text_box.singleLine()
                Logger.debug("Reloading config parameters.")
                self.read_config(self.exchange)
                if self.websocket:
                    self.websocket.close()
                    if self.exchange == Exchange.BINANCE:
                        self.websocket = BWebSocketClient(
                            [self.market], self.granularity
                        )
                    elif self.exchange == Exchange.COINBASEPRO:
                        self.websocket = CWebSocketClient(
                            [self.market], self.granularity
                        )
                    elif self.exchange == Exchange.KUCOIN:
                        self.websocket = KWebSocketClient(
                            [self.market], self.granularity
                        )
                    self.websocket.start()

                list(map(self.s.cancel, self.s.queue))
                self.s.enter(
                    5,
                    1,
                    self.execute_job,
                    (),
                )
                # self.read_config(self.exchange)
                self.telegram_bot.updatebotstatus("active")
        else:
            # runs once at the start of a simulation
            if self.app_started:
                if self.simstart_date is not None:
                    self.state.iterations = self.trading_data.index.get_loc(
                        str(self.get_date_from_iso8601_str(self.simstart_date))
                    )

                self.app_started = False

        # reset self.websocket every 23 hours if applicable
        if self.websocket and not self.is_sim:
            if self.websocket.time_elapsed > 82800:
                Logger.info("Websocket requires a restart every 23 hours!")
                Logger.info("Stopping self.websocket...")
                self.websocket.close()
                Logger.info("Starting self.websocket...")
                self.websocket.start()
                Logger.info("Restarting job in 30 seconds...")
                self.s.enter(
                    30,
                    1,
                    self.execute_job,
                    (),
                )

        # increment self.state.iterations
        self.state.iterations = self.state.iterations + 1

        if not self.is_sim:
            # check if data exists or not and only refresh at candle close.
            if len(self.trading_data) == 0 or (
                len(self.trading_data) > 0
                and (
                    datetime.timestamp(datetime.utcnow()) - self.granularity.to_integer
                    >= datetime.timestamp(
                        self.trading_data.iloc[
                            self.state.closed_candle_row,
                            self.trading_data.columns.get_loc("date"),
                        ]
                    )
                )
            ):
                self.trading_data = self.get_historical_data(
                    self.market, self.granularity, self.websocket
                )
                self.state.closed_candle_row = -1
                self.price = float(
                    self.trading_data.iloc[
                        -1, self.trading_data.columns.get_loc("close")
                    ]
                )

            else:
                # set time and self.price with ticker data and add/update current candle
                ticker = self.get_ticker(self.market, self.websocket)
                # if 0, use last close value as self.price
                self.price = (
                    self.trading_data["close"].iloc[-1] if ticker[1] == 0 else ticker[1]
                )
                self.ticker_date = ticker[0]
                self.ticker_self.price = ticker[1]

                if self.state.closed_candle_row == -2:
                    self.trading_data.iloc[
                        -1, self.trading_data.columns.get_loc("low")
                    ] = (
                        self.price
                        if self.price < self.trading_data["low"].iloc[-1]
                        else self.trading_data["low"].iloc[-1]
                    )
                    self.trading_data.iloc[
                        -1, self.trading_data.columns.get_loc("high")
                    ] = (
                        self.price
                        if self.price > self.trading_data["high"].iloc[-1]
                        else self.trading_data["high"].iloc[-1]
                    )
                    self.trading_data.iloc[
                        -1, self.trading_data.columns.get_loc("close")
                    ] = self.price
                    self.trading_data.iloc[
                        -1, self.trading_data.columns.get_loc("date")
                    ] = datetime.strptime(ticker[0], "%Y-%m-%d %H:%M:%S")
                    tsidx = pd.DatetimeIndex(self.trading_data["date"])
                    self.trading_data.set_index(tsidx, inplace=True)
                    self.trading_data.index.name = "ts"
                else:
                    # not sure what this code is doing as it has a bug.
                    # i've added a websocket check and added a try..catch block

                    if self.websocket:
                        try:
                            self.trading_data.loc[len(self.trading_data.index)] = [
                                datetime.strptime(ticker[0], "%Y-%m-%d %H:%M:%S"),
                                self.trading_data["market"].iloc[-1],
                                self.trading_data["granularity"].iloc[-1],
                                (
                                    self.price
                                    if self.price < self.trading_data["close"].iloc[-1]
                                    else self.trading_data["close"].iloc[-1]
                                ),
                                (
                                    self.price
                                    if self.price > self.trading_data["close"].iloc[-1]
                                    else self.trading_data["close"].iloc[-1]
                                ),
                                self.trading_data["close"].iloc[-1],
                                self.price,
                                self.trading_data["volume"].iloc[-1],
                            ]

                            tsidx = pd.DatetimeIndex(self.trading_data["date"])
                            self.trading_data.set_index(tsidx, inplace=True)
                            self.trading_data.index.name = "ts"
                            self.state.closed_candle_row = -2
                        except Exception:
                            pass

        else:
            self.df_last = self.get_interval(self.trading_data, self.state.iterations)

            if len(self.df_last) > 0 and "close" in self.df_last:
                self.price = self.df_last["close"][0]

            if len(self.trading_data) == 0:
                return None

        # analyse the market data
        if self.is_sim and len(self.trading_data.columns) > 8:
            df = self.trading_data

            # if smartswitch then get the market data using new granularity
            if self.sim_smartswitch:
                self.df_last = self.get_interval(df, self.state.iterations)
                if len(self.df_last.index.format()) > 0:
                    if self.simstart_date is not None:
                        start_date = self.get_date_from_iso8601_str(self.simstart_date)
                    else:
                        start_date = self.get_date_from_iso8601_str(
                            str(df.head(1).index.format()[0])
                        )

                    if self.simend_date is not None:
                        if self.simend_date == "now":
                            end_date = self.get_date_from_iso8601_str(
                                str(datetime.now())
                            )
                        else:
                            end_date = self.get_date_from_iso8601_str(self.simend_date)
                    else:
                        end_date = self.get_date_from_iso8601_str(
                            str(df.tail(1).index.format()[0])
                        )

                    simDate = self.get_date_from_iso8601_str(
                        str(self.state.last_df_index)
                    )

                    trading_data = self.get_smart_switch_historical_data_chained(
                        self.market,
                        self.granularity,
                        str(start_date),
                        str(end_date),
                    )

                    if self.granularity == Granularity.ONE_HOUR:
                        simDate = self.get_date_from_iso8601_str(str(simDate))
                        sim_rounded = pd.Series(simDate).dt.round("60min")
                        simDate = sim_rounded[0]
                    elif self.granularity == Granularity.FIFTEEN_MINUTES:
                        simDate = self.get_date_from_iso8601_str(str(simDate))
                        sim_rounded = pd.Series(simDate).dt.round("15min")
                        simDate = sim_rounded[0]
                    elif self.granularity == Granularity.FIVE_MINUTES:
                        simDate = self.get_date_from_iso8601_str(str(simDate))
                        sim_rounded = pd.Series(simDate).dt.round("5min")
                        simDate = sim_rounded[0]

                    dateFound = False
                    while dateFound is False:
                        try:
                            self.state.iterations = (
                                trading_data.index.get_loc(str(simDate)) + 1
                            )
                            dateFound = True
                        except Exception:  # pylint: disable=bare-except
                            simDate += timedelta(seconds=self.granularity.value[0])

                    if (
                        self.get_date_from_iso8601_str(str(simDate)).isoformat()
                        == self.get_date_from_iso8601_str(
                            str(self.state.last_df_index)
                        ).isoformat()
                    ):
                        self.state.iterations += 1

                    if self.state.iterations == 0:
                        self.state.iterations = 1

                    trading_dataCopy = trading_data.copy()
                    _technical_analysis = TechnicalAnalysis(
                        trading_dataCopy, self.adjust_total_periods
                    )

                    # if 'morning_star' not in df:
                    _technical_analysis.addAll()

                    df = _technical_analysis.getDataFrame()

                    self.sim_smartswitch = False

            elif self.smart_switch == 1 and _technical_analysis is None:
                trading_dataCopy = trading_data.copy()
                _technical_analysis = TechnicalAnalysis(
                    trading_dataCopy, self.adjust_total_periods
                )

                if "morning_star" not in df:
                    _technical_analysis.addAll()

                df = _technical_analysis.getDataFrame()

        else:
            _technical_analysis = TechnicalAnalysis(
                self.trading_data, len(self.trading_data)
            )
            _technical_analysis.addAll()
            df = _technical_analysis.getDataFrame()

        if self.is_sim:
            self.df_last = self.get_interval(df, self.state.iterations)
        else:
            self.df_last = self.get_interval(df)

        # Don't want index of new, unclosed candle, use the historical row setting to set index to last closed candle
        if self.state.closed_candle_row != -2 and len(self.df_last.index.format()) > 0:
            current_df_index = str(self.df_last.index.format()[0])
        else:
            current_df_index = self.state.last_df_index

        formatted_current_df_index = (
            f"{current_df_index} 00:00:00"
            if len(current_df_index) == 10
            else current_df_index
        )

        current_sim_date = formatted_current_df_index

        if self.state.iterations == 2:
            # check if bot has open or closed order
            # update data.json "opentrades"
            if self.state.last_action == "BUY":
                self.telegram_bot.add_open_order()
            else:
                self.telegram_bot.remove_open_order()

        if (
            (last_api_call_datetime.seconds > 60 or self.is_sim)
            and self.smart_switch == 1
            and self.sell_smart_switch == 1
            and self.granularity != Granularity.FIVE_MINUTES
            and self.state.last_action == "BUY"
        ):

            if not self.is_sim or (self.is_sim and not self.simresultonly):
                Logger.info(
                    "*** open order detected smart switching to 300 (5 min) granularity ***"
                )

            if not self.telegramtradesonly:
                self.notify_telegram(
                    self.market
                    + " open order detected smart switching to 300 (5 min) granularity"
                )

            if self.is_sim:
                self.sim_smartswitch = True

            self.granularity = Granularity.FIVE_MINUTES
            list(map(self.s.cancel, self.s.queue))
            self.s.enter(5, 1, self.execute_job, ())

        if (
            (last_api_call_datetime.seconds > 60 or self.is_sim)
            and self.smart_switch == 1
            and self.sell_smart_switch == 1
            and self.granularity == Granularity.FIVE_MINUTES
            and self.state.last_action == "SELL"
        ):

            if not self.is_sim or (self.is_sim and not self.simresultonly):
                Logger.info(
                    "*** sell detected smart switching to 3600 (1 hour) granularity ***"
                )
            if not self.telegramtradesonly:
                self.notify_telegram(
                    self.market
                    + " sell detected smart switching to 3600 (1 hour) granularity"
                )
            if self.is_sim:
                self.sim_smartswitch = True

            self.granularity = Granularity.ONE_HOUR
            list(map(self.s.cancel, self.s.queue))
            self.s.enter(5, 1, self.execute_job, ())

        # use actual sim mode date to check smartchswitch
        if (
            (last_api_call_datetime.seconds > 60 or self.is_sim)
            and self.smart_switch == 1
            and self.granularity == Granularity.ONE_HOUR
            and self.is_1h_ema1226_bull(current_sim_date) is True
            and self.is_6h_ema1226_bull(current_sim_date) is True
        ):
            if not self.is_sim or (self.is_sim and not self.simresultonly):
                Logger.info(
                    "*** smart switch from granularity 3600 (1 hour) to 900 (15 min) ***"
                )

            if self.is_sim:
                self.sim_smartswitch = True

            if not self.telegramtradesonly:
                self.notify_telegram(
                    self.market
                    + " smart switch from granularity 3600 (1 hour) to 900 (15 min)"
                )

            self.granularity = Granularity.FIFTEEN_MINUTES
            list(map(self.s.cancel, self.s.queue))
            self.s.enter(5, 1, self.execute_job, ())

        # use actual sim mode date to check smartchswitch
        if (
            (last_api_call_datetime.seconds > 60 or self.is_sim)
            and self.smart_switch == 1
            and self.granularity == Granularity.FIFTEEN_MINUTES
            and self.is_1h_ema1226_bull(current_sim_date) is False
            and self.is_6h_ema1226_bull(current_sim_date) is False
        ):
            if not self.is_sim or (self.is_sim and not self.simresultonly):
                Logger.info(
                    "*** smart switch from granularity 900 (15 min) to 3600 (1 hour) ***"
                )

            if self.is_sim:
                self.sim_smartswitch = True

            if not self.telegramtradesonly:
                self.notify_telegram(
                    f"{self.market} smart switch from granularity 900 (15 min) to 3600 (1 hour)"
                )

            self.granularity = Granularity.ONE_HOUR
            list(map(self.s.cancel, self.s.queue))
            self.s.enter(5, 1, self.execute_job, ())

        if (
            self.exchange == Exchange.BINANCE
            and self.granularity == Granularity.ONE_DAY
        ):
            if len(df) < 250:
                # data frame should have 250 rows, if not retry
                Logger.error(f"error: data frame length is < 250 ({str(len(df))})")
                list(map(self.s.cancel, self.s.queue))
                self.s.enter(300, 1, self.execute_job, ())
        else:
            # verify 300 rows - subtract 5 to allow small buffer if API is acting up.
            if (
                len(df) < self.adjust_total_periods - 5
            ):  # If 300 is required, set adjust_total_periods in config to 305.
                if not self.is_sim:
                    # data frame should have 300 rows or equal to adjusted total rows if set, if not retry
                    Logger.error(
                        f"error: data frame length is < {str(self.adjust_total_periods)} ({str(len(df))})"
                    )
                    # pause for 10 seconds to prevent multiple calls immediately
                    time.sleep(10)
                    list(map(self.s.cancel, self.s.queue))
                    self.s.enter(
                        300,
                        1,
                        self.execute_job,
                        (),
                    )

        if len(self.df_last) > 0:
            now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

            # last_action polling if live
            if self.is_live:
                last_action_current = self.state.last_action
                # If using websockets make this call every minute instead of each iteration
                if self.websocket and not self.is_sim:
                    if last_api_call_datetime.seconds > 60:
                        self.state.poll_last_action()
                else:
                    self.state.poll_last_action()

                if last_action_current != self.state.last_action:
                    Logger.info(
                        f"last_action change detected from {last_action_current} to {self.state.last_action}"
                    )
                    if not self.telegramtradesonly:
                        self.notify_telegram(
                            f"{self.market} last_action change detected from {last_action_current} to {self.state.last_action}"
                        )

                # this is used to reset variables if error occurred during trade process
                # make sure signals and telegram info is set correctly, close bot if needed on sell
                if (
                    self.state.action == "check_action"
                    and self.state.last_action == "BUY"
                ):
                    self.state.trade_error_cnt = 0
                    self.state.trailing_buy = False
                    self.state.action = None
                    self.state.trailing_buy_immediate = False
                    self.telegram_bot.add_open_order()

                    Logger.warning(
                        f"{self.market} ({self.print_granularity}) - {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Catching BUY that occurred previously. Updating signal information."
                    )

                    if not self.telegramtradesonly:
                        self.notify_telegram(
                            self.market
                            + " ("
                            + self.print_granularity()
                            + ") - "
                            + datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                            + "\n"
                            + "Catching BUY that occurred previously. Updating signal information."
                        )

                elif (
                    self.state.action == "check_action"
                    and self.state.last_action == "SELL"
                ):
                    self.state.prevent_loss = False
                    self.state.trailing_sell = False
                    self.state.trailing_sell_immediate = False
                    self.state.tsl_triggered = False
                    self.state.tsl_pcnt = float(self.trailing_stop_loss)
                    self.state.tsl_trigger = float(self.trailing_stop_loss_trigger)
                    self.state.tsl_max = False
                    self.state.trade_error_cnt = 0
                    self.state.action = None
                    self.telegram_bot.remove_open_order()

                    Logger.warning(
                        f"{self.market} ({self.print_granularity}) - {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Catching SELL that occurred previously. Updating signal information."
                    )

                    if not self.telegramtradesonly:
                        self.notify_telegram(
                            self.market
                            + " ("
                            + self.print_granularity()
                            + ") - "
                            + datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                            + "\n"
                            + "Catching SELL that occurred previously. Updating signal information."
                        )

                    self.telegram_bot.closetrade(
                        str(self.get_date_from_iso8601_str(str(datetime.now()))),
                        0,
                        0,
                    )

                    if self.enableexitaftersell and self.startmethod not in (
                        "standard",
                    ):
                        sys.exit(0)

            if self.price < 0.000001:
                raise Exception(
                    f"{self.market} is unsuitable for trading, quote self.price is less than 0.000001!"
                )

            try:
                # technical indicators
                ema12gtema26 = bool(self.df_last["ema12gtema26"].values[0])
                ema12gtema26co = bool(self.df_last["ema12gtema26co"].values[0])
                goldencross = bool(self.df_last["goldencross"].values[0])
                macdgtsignal = bool(self.df_last["macdgtsignal"].values[0])
                macdgtsignalco = bool(self.df_last["macdgtsignalco"].values[0])
                ema12ltema26 = bool(self.df_last["ema12ltema26"].values[0])
                ema12ltema26co = bool(self.df_last["ema12ltema26co"].values[0])
                macdltsignal = bool(self.df_last["macdltsignal"].values[0])
                macdltsignalco = bool(self.df_last["macdltsignalco"].values[0])
                obv = float(self.df_last["obv"].values[0])
                obv_pc = float(self.df_last["obv_pc"].values[0])
                elder_ray_buy = bool(self.df_last["eri_buy"].values[0])
                elder_ray_sell = bool(self.df_last["eri_sell"].values[0])

                # if simulation, set goldencross based on actual sim date
                if self.is_sim:
                    if self.adjust_total_periods < 200:
                        goldencross = False
                    else:
                        goldencross = self.is_1h_sma50200_bull(current_sim_date)

                # candlestick detection
                hammer = bool(self.df_last["hammer"].values[0])
                inverted_hammer = bool(self.df_last["inverted_hammer"].values[0])
                hanging_man = bool(self.df_last["hanging_man"].values[0])
                shooting_star = bool(self.df_last["shooting_star"].values[0])
                three_white_soldiers = bool(
                    self.df_last["three_white_soldiers"].values[0]
                )
                three_black_crows = bool(self.df_last["three_black_crows"].values[0])
                morning_star = bool(self.df_last["morning_star"].values[0])
                evening_star = bool(self.df_last["evening_star"].values[0])
                three_line_strike = bool(self.df_last["three_line_strike"].values[0])
                abandoned_baby = bool(self.df_last["abandoned_baby"].values[0])
                morning_doji_star = bool(self.df_last["morning_doji_star"].values[0])
                evening_doji_star = bool(self.df_last["evening_doji_star"].values[0])
                two_black_gapping = bool(self.df_last["two_black_gapping"].values[0])
            except KeyError as err:
                Logger.error(err)
                sys.exit()

            # Log data for Telegram Bot
            self.telegram_bot.addindicators("EMA", ema12gtema26 or ema12gtema26co)
            if not self.disablebuyelderray:
                self.telegram_bot.addindicators("ERI", elder_ray_buy)
            if self.disablebullonly:
                self.telegram_bot.addindicators("BULL", goldencross)
            if not self.disablebuymacd:
                self.telegram_bot.addindicators("MACD", macdgtsignal or macdgtsignalco)
            if not self.disablebuyobv:
                self.telegram_bot.addindicators("OBV", float(obv_pc) > 0)

            if self.is_sim:
                # Reset the Strategy so that the last record is the current sim date
                # To allow for calculations to be done on the sim date being processed
                sdf = df[df["date"] <= current_sim_date].tail(self.adjust_total_periods)
                strategy = Strategy(
                    self, self.state, sdf, sdf.index.get_loc(str(current_sim_date)) + 1
                )
            else:
                strategy = Strategy(self, self.state, df)

            trailing_action_logtext = ""

            # determine current action, indicatorvalues will be empty if custom Strategy are disabled or it's debug is False
            self.state.action, indicatorvalues = strategy.getAction(
                self.state, self.price, current_sim_date, self.websocket
            )

            immediate_action = False
            margin, profit, sell_fee, change_pcnt_high = 0, 0, 0, 0

            # Reset the TA so that the last record is the current sim date
            # To allow for calculations to be done on the sim date being processed
            if self.is_sim:
                trading_dataCopy = (
                    self.trading_data[self.trading_data["date"] <= current_sim_date]
                    .tail(self.adjust_total_periods)
                    .copy()
                )
                _technical_analysis = TechnicalAnalysis(
                    trading_dataCopy, self.adjust_total_periods
                )

            if (
                self.state.last_buy_size > 0
                and self.state.last_buy_price > 0
                and self.price > 0
                and self.state.last_action == "BUY"
            ):
                # update last buy high
                if self.price > self.state.last_buy_high:
                    self.state.last_buy_high = self.price

                if self.state.last_buy_high > 0:
                    change_pcnt_high = (
                        (self.price / self.state.last_buy_high) - 1
                    ) * 100
                else:
                    change_pcnt_high = 0

                # buy and sell calculations
                self.state.last_buy_fee = round(
                    self.state.last_buy_size * self.get_taker_fee(), 8
                )
                self.state.last_buy_filled = round(
                    (
                        (self.state.last_buy_size - self.state.last_buy_fee)
                        / self.state.last_buy_price
                    ),
                    8,
                )

                # if not a simulation, sync with exchange orders
                if not self.is_sim:
                    if self.websocket:
                        if last_api_call_datetime.seconds > 60:
                            self.state.exchange_last_buy = self.get_last_buy()
                    else:
                        self.state.exchange_last_buy = self.get_last_buy()
                    exchange_last_buy = self.state.exchange_last_buy
                    if exchange_last_buy is not None:
                        if self.state.last_buy_size != exchange_last_buy["size"]:
                            self.state.last_buy_size = exchange_last_buy["size"]
                        if self.state.last_buy_filled != exchange_last_buy["filled"]:
                            self.state.last_buy_filled = exchange_last_buy["filled"]
                        if self.state.last_buy_price != exchange_last_buy["price"]:
                            self.state.last_buy_price = exchange_last_buy["price"]

                        if (
                            self.exchange == Exchange.COINBASEPRO
                            or self.exchange == Exchange.KUCOIN
                        ):
                            if self.state.last_buy_fee != exchange_last_buy["fee"]:
                                self.state.last_buy_fee = exchange_last_buy["fee"]

                margin, profit, sell_fee = calculate_margin(
                    buy_size=self.state.last_buy_size,
                    buy_filled=self.state.last_buy_filled,
                    buy_price=self.state.last_buy_price,
                    buy_fee=self.state.last_buy_fee,
                    sell_percent=self.getSellPercent(),
                    sell_price=self.price,
                    sell_taker_fee=self.get_taker_fee(),
                )

                # handle immediate sell actions
                if self.manual_trades_only is False and strategy.is_sell_trigger(
                    self,
                    self.state,
                    self.price,
                    _technical_analysis.get_trade_exit(self.price),
                    margin,
                    change_pcnt_high,
                    obv_pc,
                    macdltsignal,
                ):
                    self.state.action = "SELL"
                    immediate_action = True

            # handle overriding wait actions
            # (e.g. do not sell if sell at loss disabled!, do not buy in bull if bull only, manual trades only)
            if self.manual_trades_only is True or (
                self.state.action != "WAIT"
                and strategy.is_wait_trigger(margin, goldencross)
            ):
                self.state.action = "WAIT"
                immediate_action = False

            # If buy signal, save the self.price and check for decrease/increase before buying.
            if self.state.action == "BUY" and immediate_action is not True:
                (
                    self.state.action,
                    self.state.trailing_buy,
                    trailing_action_logtext,
                    immediate_action,
                ) = strategy.check_trailing_buy(self.state, self.price)
            # If sell signal, save the self.price and check for decrease/increase before selling.
            if self.state.action == "SELL" and immediate_action is not True:
                (
                    self.state.action,
                    self.state.trailing_sell,
                    trailing_action_logtext,
                    immediate_action,
                ) = strategy.check_trailing_sell(self.state, self.price)

            if self.enableimmediatebuy:
                if self.state.action == "BUY":
                    immediate_action = True

            if not self.is_sim and self.enabletelegrambotcontrol:
                manual_buy_sell = self.telegram_bot.check_manual_buy_sell()
                if not manual_buy_sell == "WAIT":
                    self.state.action = manual_buy_sell
                    immediate_action = True

            bullbeartext = ""
            if (
                self.disablebullonly is True
                or self.adjust_total_periods < 200
                or self.df_last["sma50"].values[0] == self.df_last["sma200"].values[0]
            ):
                bullbeartext = ""
            elif goldencross is True:
                bullbeartext = " (BULL)"
            elif goldencross is False:
                bullbeartext = " (BEAR)"

            # polling is every 5 minutes (even for hourly intervals), but only process once per interval
            # Logger.debug("DateCheck: " + str(immediate_action) + ' ' + str(self.state.last_df_index) + ' ' + str(current_df_index))
            if immediate_action is True or self.state.last_df_index != current_df_index:
                text_box = TextBox(80, 22)

                precision = 4

                if self.price < 0.01:
                    precision = 8

                # Since precision does not change after this point, it is safe to prepare a tailored `truncate()` that would
                # work with this precision. It should save a couple of `precision` uses, one for each `truncate()` call.
                truncate = functools.partial(self.truncate, n=precision)

                if immediate_action:
                    self.price_text = str(self.price)
                else:
                    self.price_text = "Close: " + str(self.price)
                ema_text = ""
                if self.disablebuyema is False:
                    ema_text = self.compare(
                        self.df_last["ema12"].values[0],
                        self.df_last["ema26"].values[0],
                        "EMA12/26",
                        precision,
                    )

                macd_text = ""
                if self.disablebuymacd is False:
                    macd_text = self.compare(
                        self.df_last["macd"].values[0],
                        self.df_last["signal"].values[0],
                        "MACD",
                        precision,
                    )

                obv_text = ""
                if self.disablebuyobv is False:
                    obv_text = (
                        "OBV: "
                        + truncate(self.df_last["obv"].values[0])
                        + " ("
                        + str(truncate(self.df_last["obv_pc"].values[0]))
                        + "%)"
                    )

                eri_text = ""
                if self.disablebuyelderray is False:
                    if elder_ray_buy is True:
                        eri_text = "ERI: buy"
                    elif elder_ray_sell is True:
                        eri_text = "ERI: sell"

                log_text = ""
                if hammer is True:
                    log_text = '* Candlestick Detected: Hammer ("Weak - Reversal - Bullish Signal - Up")'

                if shooting_star is True:
                    log_text = '* Candlestick Detected: Shooting Star ("Weak - Reversal - Bearish Pattern - Down")'

                if hanging_man is True:
                    log_text = '* Candlestick Detected: Hanging Man ("Weak - Continuation - Bearish Pattern - Down")'

                if inverted_hammer is True:
                    log_text = '* Candlestick Detected: Inverted Hammer ("Weak - Continuation - Bullish Pattern - Up")'

                if three_white_soldiers is True:
                    log_text = '*** Candlestick Detected: Three White Soldiers ("Strong - Reversal - Bullish Pattern - Up")'

                if three_black_crows is True:
                    log_text = '* Candlestick Detected: Three Black Crows ("Strong - Reversal - Bearish Pattern - Down")'

                if morning_star is True:
                    log_text = '*** Candlestick Detected: Morning Star ("Strong - Reversal - Bullish Pattern - Up")'

                if evening_star is True:
                    log_text = '*** Candlestick Detected: Evening Star ("Strong - Reversal - Bearish Pattern - Down")'

                if three_line_strike is True:
                    log_text = '** Candlestick Detected: Three Line Strike ("Reliable - Reversal - Bullish Pattern - Up")'

                if abandoned_baby is True:
                    log_text = '** Candlestick Detected: Abandoned Baby ("Reliable - Reversal - Bullish Pattern - Up")'

                if morning_doji_star is True:
                    log_text = '** Candlestick Detected: Morning Doji Star ("Reliable - Reversal - Bullish Pattern - Up")'

                if evening_doji_star is True:
                    log_text = '** Candlestick Detected: Evening Doji Star ("Reliable - Reversal - Bearish Pattern - Down")'

                if two_black_gapping is True:
                    log_text = '*** Candlestick Detected: Two Black Gapping ("Reliable - Reversal - Bearish Pattern - Down")'

                if (
                    log_text != ""
                    and not self.is_sim
                    or (self.is_sim and not self.simresultonly)
                ):
                    Logger.info(log_text)

                ema_co_prefix = ""
                ema_co_suffix = ""
                if self.disablebuyema is False:
                    if ema12gtema26co is True:
                        ema_co_prefix = "*^ "
                        ema_co_suffix = " ^* | "
                    elif ema12ltema26co is True:
                        ema_co_prefix = "*v "
                        ema_co_suffix = " v* | "
                    elif ema12gtema26 is True:
                        ema_co_prefix = "^ "
                        ema_co_suffix = " ^ | "
                    elif ema12ltema26 is True:
                        ema_co_prefix = "v "
                        ema_co_suffix = " v | "
                    else:
                        ema_co_suffix = " | "

                macd_co_prefix = ""
                macd_co_suffix = ""
                if self.disablebuymacd is False:
                    if macdgtsignalco is True:
                        macd_co_prefix = "*^ "
                        macd_co_suffix = " ^* | "
                    elif macdltsignalco is True:
                        macd_co_prefix = "*v "
                        macd_co_suffix = " v* | "
                    elif macdgtsignal is True:
                        macd_co_prefix = "^ "
                        macd_co_suffix = " ^ | "
                    elif macdltsignal is True:
                        macd_co_prefix = "v "
                        macd_co_suffix = " v | "
                    else:
                        macd_co_suffix = " | "

                obv_prefix = ""
                obv_suffix = ""
                if self.disablebuyobv is False:
                    if float(obv_pc) > 0:
                        obv_prefix = "^ "
                        obv_suffix = " ^ | "
                    elif float(obv_pc) < 0:
                        obv_prefix = "v "
                        obv_suffix = " v | "

                if not self.is_verbose:
                    if self.state.last_action != "":
                        # Not sure if this if is needed just preserving any existing functionality that may have been missed
                        # Updated to show over margin and profit
                        if not self.is_sim:
                            output_text = (
                                formatted_current_df_index
                                + " | "
                                + self.market
                                + bullbeartext
                                + " | "
                                + self.print_granularity()
                                + " | "
                                + self.price_text
                                + trailing_action_logtext
                                + " | "
                                + ema_co_prefix
                                + ema_text
                                + ema_co_suffix
                                + macd_co_prefix
                                + macd_text
                                + macd_co_suffix
                                + obv_prefix
                                + obv_text
                                + obv_suffix
                                + eri_text
                                + " | Action: "
                                + self.state.action
                                + " | Last Action: "
                                + self.state.last_action
                                + " | DF HIGH: "
                                + str(df["close"].max())
                                + " | "
                                + "DF LOW: "
                                + str(df["close"].min())
                                + " | SWING: "
                                + str(
                                    round(
                                        (
                                            (df["close"].max() - df["close"].min())
                                            / df["close"].min()
                                        )
                                        * 100,
                                        2,
                                    )
                                )
                                + "% |"
                                + " CURR Price is "
                                + str(
                                    round(
                                        (
                                            (self.price - df["close"].max())
                                            / df["close"].max()
                                        )
                                        * 100,
                                        2,
                                    )
                                )
                                + "% "
                                + "away from DF HIGH | Range: "
                                + str(df.iloc[0, 0])
                                + " <--> "
                                + str(df.iloc[len(df) - 1, 0])
                            )
                        else:
                            df_high = df[df["date"] <= current_sim_date]["close"].max()
                            df_low = df[df["date"] <= current_sim_date]["close"].min()
                            # print(df_high)
                            output_text = (
                                formatted_current_df_index
                                + " | "
                                + self.market
                                + bullbeartext
                                + " | "
                                + self.print_granularity()
                                + " | "
                                + self.price_text
                                + trailing_action_logtext
                                + " | "
                                + ema_co_prefix
                                + ema_text
                                + ema_co_suffix
                                + macd_co_prefix
                                + macd_text
                                + macd_co_suffix
                                + obv_prefix
                                + obv_text
                                + obv_suffix
                                + eri_text
                                + " | Action: "
                                + self.state.action
                                + " | Last Action: "
                                + self.state.last_action
                                + " | DF HIGH: "
                                + str(df_high)
                                + " | "
                                + "DF LOW: "
                                + str(df_low)
                                + " | SWING: "
                                + str(round(((df_high - df_low) / df_low) * 100, 2))
                                + "% |"
                                + " CURR Price is "
                                + str(
                                    round(((self.price - df_high) / df_high) * 100, 2)
                                )
                                + "% "
                                + "away from DF HIGH | Range: "
                                + str(
                                    df.iloc[
                                        self.state.iterations
                                        - self.adjust_total_periods,
                                        0,
                                    ]
                                )
                                + " <--> "
                                + str(df.iloc[self.state.iterations - 1, 0])
                            )
                    else:
                        if not self.is_sim:
                            output_text = (
                                formatted_current_df_index
                                + " | "
                                + self.market
                                + bullbeartext
                                + " | "
                                + self.print_granularity()
                                + " | "
                                + self.price_text
                                + trailing_action_logtext
                                + " | "
                                + ema_co_prefix
                                + ema_text
                                + ema_co_suffix
                                + macd_co_prefix
                                + macd_text
                                + macd_co_suffix
                                + obv_prefix
                                + obv_text
                                + obv_suffix
                                + eri_text
                                + self.state.action
                                + " | DF HIGH: "
                                + str(df["close"].max())
                                + " | "
                                + "DF LOW: "
                                + str(df["close"].min())
                                + " | SWING: "
                                + str(
                                    round(
                                        (
                                            (df["close"].max() - df["close"].min())
                                            / df["close"].min()
                                        )
                                        * 100,
                                        2,
                                    )
                                )
                                + "%"
                                + " CURR Price is "
                                + str(
                                    round(
                                        (
                                            (self.price - df["close"].max())
                                            / df["close"].max()
                                        )
                                        * 100,
                                        2,
                                    )
                                )
                                + "% "
                                + "away from DF HIGH | Range: "
                                + str(df.iloc[0, 0])
                                + " <--> "
                                + str(df.iloc[len(df) - 1, 0])
                            )
                        else:
                            df_high = df[df["date"] <= current_sim_date]["close"].max()
                            df_low = df[df["date"] <= current_sim_date]["close"].min()

                            output_text = (
                                formatted_current_df_index
                                + " | "
                                + self.market
                                + bullbeartext
                                + " | "
                                + self.print_granularity()
                                + " | "
                                + self.price_text
                                + trailing_action_logtext
                                + " | "
                                + ema_co_prefix
                                + ema_text
                                + ema_co_suffix
                                + macd_co_prefix
                                + macd_text
                                + macd_co_suffix
                                + obv_prefix
                                + obv_text
                                + obv_suffix
                                + eri_text
                                + self.state.action
                                + " | DF HIGH: "
                                + str(df_high)
                                + " | "
                                + "DF LOW: "
                                + str(df_low)
                                + " | SWING: "
                                + str(round(((df_high - df_low) / df_low) * 100, 2))
                                + "%"
                                + " CURR Price is "
                                + str(
                                    round(((self.price - df_high) / df_high) * 100, 2)
                                )
                                + "% "
                                + "away from DF HIGH | Range: "
                                + str(
                                    df.iloc[
                                        self.state.iterations
                                        - self.adjust_total_periods,
                                        0,
                                    ]
                                )
                                + " <--> "
                                + str(df.iloc[self.state.iterations - 1, 0])
                            )
                    if self.state.last_action == "BUY":
                        if self.state.last_buy_size > 0:
                            margin_text = truncate(margin) + "%"
                        else:
                            margin_text = "0%"

                        output_text += (
                            trailing_action_logtext
                            + " | (margin: "
                            + margin_text
                            + " delta: "
                            + str(
                                round(self.price - self.state.last_buy_price, precision)
                            )
                            + ")"
                        )
                        if self.is_sim:
                            # save margin for Summary if open trade
                            self.state.open_trade_margin = margin_text

                    if not self.is_sim or (self.is_sim and not self.simresultonly):
                        Logger.info(output_text)

                    if self.enableml:
                        # Seasonal Autoregressive Integrated Moving Average (ARIMA) model (ML prediction for 3 intervals from now)
                        if not self.is_sim:
                            try:
                                prediction = _technical_analysis.arima_model_prediction(
                                    int(self.granularity.to_integer / 60) * 3
                                )  # 3 intervals from now
                                Logger.info(
                                    f"Seasonal ARIMA model predicts the closing self.price will be {str(round(prediction[1], 2))} at {prediction[0]} (delta: {round(prediction[1] - self.price, 2)})"
                                )
                            # pylint: disable=bare-except
                            except Exception:
                                pass

                    if self.state.last_action == "BUY":
                        # display support, resistance and fibonacci levels
                        if not self.is_sim or (self.is_sim and not self.simresultonly):
                            Logger.info(
                                _technical_analysis.print_sr_fib_levels(self.price)
                            )

                else:
                    # set to true for verbose debugging
                    debug = False

                    if debug:
                        Logger.debug(
                            f"-- Iteration: {str(self.state.iterations)} --{bullbeartext}"
                        )

                    if self.state.last_action == "BUY":
                        if self.state.last_buy_size > 0:
                            margin_text = truncate(margin) + "%"
                        else:
                            margin_text = "0%"
                            if self.is_sim:
                                # save margin for Summary if open trade
                                self.state.open_trade_margin = margin_text
                        if debug:
                            Logger.debug(f"-- Margin: {margin_text} --")

                    if debug:
                        Logger.debug(f"price: {truncate(self.price)}")
                        Logger.debug(
                            f'ema12: {truncate(float(self.df_last["ema12"].values[0]))}'
                        )
                        Logger.debug(
                            f'ema26: {truncate(float(self.df_last["ema26"].values[0]))}'
                        )
                        Logger.debug(f"ema12gtema26co: {str(ema12gtema26co)}")
                        Logger.debug(f"ema12gtema26: {str(ema12gtema26)}")
                        Logger.debug(f"ema12ltema26co: {str(ema12ltema26co)}")
                        Logger.debug(f"ema12ltema26: {str(ema12ltema26)}")
                        if self.adjust_total_periods >= 50:
                            Logger.debug(
                                f'sma50: {truncate(float(self.df_last["sma50"].values[0]))}'
                            )
                        if self.adjust_total_periods >= 200:
                            Logger.debug(
                                f'sma200: {truncate(float(self.df_last["sma200"].values[0]))}'
                            )
                        Logger.debug(
                            f'macd: {truncate(float(self.df_last["macd"].values[0]))}'
                        )
                        Logger.debug(
                            f'signal: {truncate(float(self.df_last["signal"].values[0]))}'
                        )
                        Logger.debug(f"macdgtsignal: {str(macdgtsignal)}")
                        Logger.debug(f"macdltsignal: {str(macdltsignal)}")
                        Logger.debug(f"obv: {str(obv)}")
                        Logger.debug(f"obv_pc: {str(obv_pc)}")
                        Logger.debug(f"action: {self.state.action}")

                    # informational output on the most recent entry
                    Logger.info("")
                    text_box.doubleLine()
                    text_box.line(
                        "Iteration", str(self.state.iterations) + bullbeartext
                    )
                    text_box.line("Timestamp", str(self.df_last.index.format()[0]))
                    text_box.singleLine()
                    text_box.line("Close", truncate(self.price))
                    text_box.line(
                        "EMA12", truncate(float(self.df_last["ema12"].values[0]))
                    )
                    text_box.line(
                        "EMA26", truncate(float(self.df_last["ema26"].values[0]))
                    )
                    text_box.line("Crossing Above", str(ema12gtema26co))
                    text_box.line("Currently Above", str(ema12gtema26))
                    text_box.line("Crossing Below", str(ema12ltema26co))
                    text_box.line("Currently Below", str(ema12ltema26))

                    if ema12gtema26 is True and ema12gtema26co is True:
                        text_box.line(
                            "Condition", "EMA12 is currently crossing above EMA26"
                        )
                    elif ema12gtema26 is True and ema12gtema26co is False:
                        text_box.line(
                            "Condition",
                            "EMA12 is currently above EMA26 and has crossed over",
                        )
                    elif ema12ltema26 is True and ema12ltema26co is True:
                        text_box.line(
                            "Condition", "EMA12 is currently crossing below EMA26"
                        )
                    elif ema12ltema26 is True and ema12ltema26co is False:
                        text_box.line(
                            "Condition",
                            "EMA12 is currently below EMA26 and has crossed over",
                        )
                    else:
                        text_box.line("Condition", "-")

                    text_box.line(
                        "SMA20", truncate(float(self.df_last["sma20"].values[0]))
                    )
                    text_box.line(
                        "SMA200", truncate(float(self.df_last["sma200"].values[0]))
                    )
                    text_box.singleLine()
                    text_box.line(
                        "MACD", truncate(float(self.df_last["macd"].values[0]))
                    )
                    text_box.line(
                        "Signal", truncate(float(self.df_last["signal"].values[0]))
                    )
                    text_box.line("Currently Above", str(macdgtsignal))
                    text_box.line("Currently Below", str(macdltsignal))

                    if macdgtsignal is True and macdgtsignalco is True:
                        text_box.line(
                            "Condition", "MACD is currently crossing above Signal"
                        )
                    elif macdgtsignal is True and macdgtsignalco is False:
                        text_box.line(
                            "Condition",
                            "MACD is currently above Signal and has crossed over",
                        )
                    elif macdltsignal is True and macdltsignalco is True:
                        text_box.line(
                            "Condition", "MACD is currently crossing below Signal"
                        )
                    elif macdltsignal is True and macdltsignalco is False:
                        text_box.line(
                            "Condition",
                            "MACD is currently below Signal and has crossed over",
                        )
                    else:
                        text_box.line("Condition", "-")

                    text_box.singleLine()
                    text_box.line("Action", self.state.action)
                    text_box.doubleLine()
                    if self.state.last_action == "BUY":
                        text_box.line("Margin", margin_text)
                        text_box.doubleLine()

                # if a buy signal
                if self.state.action == "BUY":
                    self.state.last_buy_price = self.price
                    self.state.last_buy_high = self.state.last_buy_price

                    # if live
                    if self.is_live:
                        ac = self.account.getBalance()
                        self.account.basebalance_before = 0.0
                        self.account.quotebalance_before = 0.0
                        try:
                            df_base = ac[ac["currency"] == self.base_currency][
                                "available"
                            ]
                            self.account.basebalance_before = (
                                0.0 if len(df_base) == 0 else float(df_base.values[0])
                            )

                            df_quote = ac[ac["currency"] == self.quote_currency][
                                "available"
                            ]
                            self.account.quotebalance_before = (
                                0.0 if len(df_quote) == 0 else float(df_quote.values[0])
                            )
                        except Exception:
                            pass

                        if (
                            not self.insufficientfunds
                            and self.buyminsize < self.account.quotebalance_before
                        ):
                            if not self.is_verbose:
                                if not self.is_sim or (
                                    self.is_sim and not self.simresultonly
                                ):
                                    Logger.info(
                                        f"{formatted_current_df_index} | {self.market} | {self.print_granularity()} | {self.price_text} | BUY"
                                    )
                            else:
                                text_box.singleLine()
                                text_box.center("*** Executing LIVE Buy Order ***")
                                text_box.singleLine()

                            # display balances
                            Logger.info(
                                f"{self.base_currency} balance before order: {str(self.account.basebalance_before)}"
                            )
                            Logger.info(
                                f"{self.quote_currency} balance before order: {str(self.account.quotebalance_before)}"
                            )

                            # execute a live market buy
                            self.state.last_buy_size = float(
                                self.account.quotebalance_before
                            )

                            if (
                                self.buymaxsize
                                and self.buylastsellsize
                                and self.state.minimumOrderQuote(
                                    quote=self.state.last_sell_size, balancechk=True
                                )
                            ):
                                self.state.last_buy_size = self.state.last_sell_size
                            elif (
                                self.buymaxsize
                                and self.state.last_buy_size > self.buymaxsize
                            ):
                                self.state.last_buy_size = self.buymaxsize

                            # place the buy order
                            try:
                                self.marketBuy(
                                    self.market,
                                    self.state.last_buy_size,
                                    self.getBuyPercent(),
                                )
                                resp_error = 0
                            except Exception as err:
                                Logger.warning(f"Trade Error: {err}")
                                resp_error = 1

                            if resp_error == 0:
                                self.account.basebalance_after = 0
                                self.account.quotebalance_after = 0
                                try:
                                    ac = self.account.getBalance()
                                    df_base = ac[ac["currency"] == self.base_currency][
                                        "available"
                                    ]
                                    self.account.basebalance_after = (
                                        0.0
                                        if len(df_base) == 0
                                        else float(df_base.values[0])
                                    )
                                    df_quote = ac[
                                        ac["currency"] == self.quote_currency
                                    ]["available"]

                                    self.account.quotebalance_after = (
                                        0.0
                                        if len(df_quote) == 0
                                        else float(df_quote.values[0])
                                    )
                                    bal_error = 0
                                except Exception as err:
                                    bal_error = 1
                                    Logger.warning(
                                        f"Error: Balance not retrieved after trade for {self.market}.\n"
                                        f"API Error Msg: {err}"
                                    )

                                if bal_error == 0:
                                    self.state.trade_error_cnt = 0
                                    self.state.trailing_buy = False
                                    self.state.last_action = "BUY"
                                    self.state.action = "DONE"
                                    self.state.trailing_buy_immediate = False
                                    self.telegram_bot.add_open_order()

                                    Logger.info(
                                        f"{self.base_currency} balance after order: {str(self.account.basebalance_after)}\n"
                                        f"{self.quote_currency} balance after order: {str(self.account.quotebalance_after)}"
                                    )

                                    self.notify_telegram(
                                        self.market
                                        + " ("
                                        + self.print_granularity()
                                        + ") - "
                                        + datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                                        + "\n"
                                        + "BUY at "
                                        + self.price_text
                                    )

                                else:
                                    # set variable to trigger to check trade on next iteration
                                    self.state.action = "check_action"
                                    Logger.info(
                                        f"{self.market} - Error occurred while checking balance after BUY. Last transaction check will happen shortly."
                                    )

                                    if not self.disabletelegramerrormsgs:
                                        self.notify_telegram(
                                            self.market
                                            + " - Error occurred while checking balance after BUY. Last transaction check will happen shortly."
                                        )

                            else:  # there was a response error
                                # only attempt BUY 3 times before exception to prevent continuous loop
                                self.state.trade_error_cnt += 1
                                if self.state.trade_error_cnt >= 2:  # 3 attempts made
                                    raise Exception(
                                        "Trade Error: BUY transaction attempted 3 times. Check log for errors"
                                    )

                                # set variable to trigger to check trade on next iteration
                                self.state.action = "check_action"
                                self.state.last_action = None

                                Logger.warning(
                                    f"API Error: Unable to place buy order for {self.market}."
                                )
                                if not self.disabletelegramerrormsgs:
                                    self.notify_telegram(
                                        f"API Error: Unable to place buy order for {self.market}"
                                    )
                                time.sleep(30)

                        else:
                            Logger.warning(
                                "Unable to place order, insufficient funds or buyminsize has not been reached. Check Logs."
                            )

                        self.state.last_api_call_datetime -= timedelta(seconds=60)

                    # if not live
                    else:
                        if (
                            self.state.last_buy_size == 0
                            and self.state.last_buy_filled == 0
                        ):
                            # Sim mode can now use buymaxsize as the amount used for a buy
                            if self.buymaxsize is not None:
                                self.state.last_buy_size = self.buymaxsize
                                self.state.first_buy_size = self.buymaxsize
                            else:
                                self.state.last_buy_size = 1000
                                self.state.first_buy_size = 1000
                        # add option for buy last sell size
                        elif (
                            self.buymaxsize is not None
                            and self.buylastsellsize
                            and self.state.last_sell_size
                            > self.state.minimumOrderQuote(
                                quote=self.state.last_sell_size, balancechk=True
                            )
                        ):
                            self.state.last_buy_size = self.state.last_sell_size

                        self.state.buy_count = self.state.buy_count + 1
                        self.state.buy_sum = (
                            self.state.buy_sum + self.state.last_buy_size
                        )
                        self.state.trailing_buy = False
                        self.state.action = "DONE"
                        self.state.trailing_buy_immediate = False

                        self.notify_telegram(
                            self.market
                            + " ("
                            + self.print_granularity()
                            + ") -  "
                            + str(current_sim_date)
                            + "\n - TEST BUY at "
                            + self.price_text
                            + "\n - Buy Size: "
                            + str(self.truncate(self.state.last_buy_size, 4))
                        )

                        if not self.is_verbose:
                            if not self.is_sim or (
                                self.is_sim and not self.simresultonly
                            ):
                                Logger.info(
                                    f"{formatted_current_df_index} | {self.market} | {self.print_granularity()} | {self.price_text} | BUY"
                                )

                            bands = _technical_analysis.getFibonacciRetracementLevels(
                                float(self.price)
                            )

                            if not self.is_sim or (
                                self.is_sim and not self.simresultonly
                            ):
                                _technical_analysis.printSupportResistanceLevel(
                                    float(self.price)
                                )

                            if not self.is_sim or (
                                self.is_sim and not self.simresultonly
                            ):
                                Logger.info(
                                    f" Fibonacci Retracement Levels:{str(bands)}"
                                )

                            if len(bands) >= 1 and len(bands) <= 2:
                                if len(bands) == 1:
                                    first_key = list(bands.keys())[0]
                                    if first_key == "ratio1":
                                        self.state.fib_low = 0
                                        self.state.fib_high = bands[first_key]
                                    if first_key == "ratio1_618":
                                        self.state.fib_low = bands[first_key]
                                        self.state.fib_high = bands[first_key] * 2
                                    else:
                                        self.state.fib_low = bands[first_key]

                                elif len(bands) == 2:
                                    first_key = list(bands.keys())[0]
                                    second_key = list(bands.keys())[1]
                                    self.state.fib_low = bands[first_key]
                                    self.state.fib_high = bands[second_key]

                        else:
                            text_box.singleLine()
                            text_box.center("*** Executing TEST Buy Order ***")
                            text_box.singleLine()

                        self.trade_tracker = pd.concat(
                            [
                                self.trade_tracker,
                                pd.DataFrame(
                                    {
                                        "Datetime": str(current_sim_date),
                                        "Market": self.market,
                                        "Action": "BUY",
                                        "Price": self.price,
                                        "Quote": self.state.last_buy_size,
                                        "Base": float(self.state.last_buy_size)
                                        / float(self.price),
                                        "DF_High": df[df["date"] <= current_sim_date][
                                            "close"
                                        ].max(),
                                        "DF_Low": df[df["date"] <= current_sim_date][
                                            "close"
                                        ].min(),
                                    },
                                    index={0},
                                ),
                            ],
                            ignore_index=True,
                        )

                        self.state.in_open_trade = True
                        self.state.last_action = "BUY"
                        self.state.last_api_call_datetime -= timedelta(seconds=60)

                    if self.shouldSaveGraphs():
                        if self.adjust_total_periods < 200:
                            Logger.info(
                                "Trading Graphs can only be generated when dataframe has more than 200 periods."
                            )
                        else:
                            tradinggraphs = TradingGraphs(_technical_analysis)
                            ts = datetime.now().timestamp()
                            filename = f"{self.market}_{self.print_granularity()}_buy_{str(ts)}.png"
                            # This allows graphs to be used in sim mode using the correct DF
                            if self.isSimulation:
                                tradinggraphs.renderEMAandMACD(
                                    len(trading_dataCopy), "graphs/" + filename, True
                                )
                            else:
                                tradinggraphs.renderEMAandMACD(
                                    len(trading_data), "graphs/" + filename, True
                                )

    def run(self):
        try:
            message = "Starting "
            if self.exchange == Exchange.COINBASEPRO:
                message += "Coinbase Pro bot"
                if self.websocket and not self.is_sim:
                    print("Opening websocket to Coinbase Pro...")
                    self.websocket = CWebSocketClient([self.market], self.granularity)
                    self.websocket.start()
            elif self.exchange == Exchange.BINANCE:
                message += "Binance bot"
                if self.websocket and not self.is_sim:
                    print("Opening websocket to Binance...")
                    self.websocket = BWebSocketClient([self.market], self.granularity)
                    self.websocket.start()
            elif self.exchange == Exchange.KUCOIN:
                message += "Kucoin bot"
                if self.websocket and not self.is_sim:
                    print("Opening websocket to Kucoin...")
                    self.websocket = KWebSocketClient([self.market], self.granularity)
                    self.websocket.start()

            smartswitchstatus = "enabled" if self.smart_switch else "disabled"
            message += f" for {self.market} using granularity {self.print_granularity()}. Smartswitch {smartswitchstatus}"

            if self.startmethod in ("standard", "telegram"):
                self.notify_telegram(message)

            # initialise and start application
            self.initialise()

            if self.is_sim and self.simend_date:
                try:
                    # if simend_date is set, then remove trailing data points
                    self.trading_data = self.trading_data[
                        self.trading_data["date"] <= self.simend_date
                    ]
                except Exception:
                    pass

            try:
                self.execute_job()
                self.s.run()

            except (KeyboardInterrupt, SystemExit):
                raise
            except (BaseException, Exception) as e:  # pylint: disable=broad-except
                if self.autorestart:
                    # Wait 30 second and try to relaunch application
                    time.sleep(30)
                    Logger.critical(
                        f"Restarting application after exception: {repr(e)}"
                    )

                    if not self.disabletelegramerrormsgs:
                        self.notify_telegram(
                            f"Auto restarting bot for {self.market} after exception: {repr(e)}"
                        )

                    # Cancel the events queue
                    map(self.s.cancel, self.s.queue)

                    # Restart the app
                    self.execute_job()
                    self.s.run()
                else:
                    raise

        # catches a keyboard break of app, exits gracefully
        except (KeyboardInterrupt, SystemExit):
            if self.websocket and not self.is_sim:
                signal.signal(signal.SIGINT, signal_handler)  # disable ctrl/cmd+c
                Logger.warning(
                    f"{str(datetime.now())} bot is closing via keyboard interrupt,"
                )
                Logger.warning("Please wait while threads complete gracefully....")
            else:
                Logger.warning(
                    f"{str(datetime.now())} bot is closed via keyboard interrupt..."
                )
            try:
                try:
                    self.telegram_bot.removeactivebot()
                except Exception:
                    pass
                if self.websocket and not self.is_sim:
                    self.websocket.close()
                sys.exit(0)
            except SystemExit:
                # pylint: disable=protected-access
                os._exit(0)
        except (BaseException, Exception) as e:  # pylint: disable=broad-except
            # catch all not managed exceptions and send a Telegram message if configured
            if not self.disabletelegramerrormsgs:
                self.notify_telegram(
                    f"Bot for {self.market} got an exception: {repr(e)}"
                )
                try:
                    self.telegram_bot.removeactivebot()
                except Exception:
                    pass
            Logger.critical(repr(e))
            # pylint: disable=protected-access
            os._exit(0)
            # raise

    def notify_telegram(self, msg: str) -> None:
        """
        Send a given message to preconfigured Telegram. If the telegram isn't enabled, e.g. via `--disabletelegram`,
        this method does nothing and returns immediately.
        """

        if self.disabletelegram or not self.telegram:
            return

        assert self._chat_client is not None

        self._chat_client.send(msg)

    def initialise(self, banner=True):
        self.account = TradingAccount(self)
        Stats(self, self.account).show()
        self.state = AppState(self, self.account)

        if banner and not self.is_sim or (self.is_sim and not self.simresultonly):
            self._generate_banner()

        self.app_started = True
        # run the first job immediately after starting
        if self.is_sim:
            if self.sim_speed in ["fast-sample", "slow-sample"]:
                attempts = 0

                if self.simstart_date is not None and self.simend_date is not None:

                    start_date = self.get_date_from_iso8601_str(self.simstart_date)

                    if self.simend_date == "now":
                        end_date = self.get_date_from_iso8601_str(str(datetime.now()))
                    else:
                        end_date = self.get_date_from_iso8601_str(self.simend_date)

                elif self.simstart_date is not None and self.simend_date is None:
                    # date = self.simstart_date.split('-')
                    start_date = self.get_date_from_iso8601_str(self.simstart_date)
                    end_date = start_date + timedelta(
                        minutes=(self.granularity.to_integer / 60)
                        * self.adjust_total_periods
                    )

                elif self.simend_date is not None and self.simstart_date is None:
                    if self.simend_date == "now":
                        end_date = self.get_date_from_iso8601_str(str(datetime.now()))
                    else:
                        end_date = self.get_date_from_iso8601_str(self.simend_date)

                    start_date = end_date - timedelta(
                        minutes=(self.granularity.to_integer / 60)
                        * self.adjust_total_periods
                    )

                else:
                    end_date = self.get_date_from_iso8601_str(
                        str(pd.Series(datetime.now()).dt.round(freq="H")[0])
                    )
                    if self.exchange == Exchange.COINBASEPRO:
                        end_date -= timedelta(
                            hours=random.randint(0, 8760 * 3)
                        )  # 3 years in hours
                    else:
                        end_date -= timedelta(hours=random.randint(0, 8760 * 1))

                    start_date = self.get_date_from_iso8601_str(str(end_date))
                    start_date -= timedelta(
                        minutes=(self.granularity.to_integer / 60)
                        * self.adjust_total_periods
                    )

                while (
                    len(self.trading_data) < self.adjust_total_periods and attempts < 10
                ):
                    if end_date.isoformat() > datetime.now().isoformat():
                        end_date = datetime.now()
                    if self.smart_switch == 1:
                        trading_data = self.get_smart_switch_historical_data_chained(
                            self.market,
                            self.granularity,
                            str(start_date),
                            str(end_date),
                        )

                    else:
                        trading_data = self.get_smart_switch_df(
                            trading_data,
                            self.market,
                            self.granularity,
                            start_date.isoformat(),
                            end_date.isoformat(),
                        )

                    attempts += 1

                if self.extra_candles_found:
                    self.simstart_date = str(start_date)
                    self.simend_date = str(end_date)

                self.extra_candles_found = True

                if len(self.trading_data) < self.adjust_total_periods:
                    raise Exception(
                        f"Unable to retrieve {str(self.adjust_total_periods)} random sets of data between {start_date} and {end_date} in 10 attempts."
                    )

                if banner:
                    text_box = TextBox(80, 26)
                    start_date = str(start_date.isoformat())
                    end_date = str(end_date.isoformat())
                    text_box.line("Sampling start", str(start_date))
                    text_box.line("Sampling end", str(end_date))
                    if (
                        self.simstart_date is None
                        and len(self.trading_data) < self.adjust_total_periods
                    ):
                        text_box.center(
                            f"WARNING: Using less than {str(self.adjust_total_periods)} intervals"
                        )
                        text_box.line("Interval size", str(len(self.trading_data)))
                    text_box.doubleLine()

            else:
                start_date = self.get_date_from_iso8601_str(str(datetime.now()))
                start_date -= timedelta(minutes=(self.granularity.to_integer / 60) * 2)
                end_date = start_date
                start_date = pd.Series(start_date).dt.round(freq="H")[0]
                end_date = pd.Series(end_date).dt.round(freq="H")[0]
                start_date -= timedelta(
                    minutes=(self.granularity.to_integer / 60)
                    * self.adjust_total_periods
                )

                if end_date.isoformat() > datetime.now().isoformat():
                    end_date = datetime.now()

                if self.smart_switch == 1:
                    self.trading_data = self.get_smart_switch_historical_data_chained(
                        self.market,
                        self.granularity,
                        str(start_date),
                        str(end_date),
                    )
                else:
                    self.trading_data = self.get_smart_switch_df(
                        self.trading_data,
                        self.market,
                        self.granularity,
                        self.get_date_from_iso8601_str(str(start_date)).isoformat(),
                        end_date.isoformat(),
                    )

    def _generate_banner(self) -> None:
        text_box = TextBox(80, 26)
        text_box.singleLine()
        text_box.center("Python Crypto Bot")
        text_box.singleLine()
        text_box.line("Release", self.get_version_from_readme())
        text_box.singleLine()

        if self.is_verbose:
            text_box.line("Market", self.market)
            text_box.line("Granularity", str(self.granularity) + " seconds")
            text_box.singleLine()

        if self.is_live:
            text_box.line("Bot Mode", "LIVE - live trades using your funds!")
        else:
            text_box.line("Bot Mode", "TEST - test trades using dummy funds :)")

        text_box.line("Bot Started", str(datetime.now()))
        text_box.line("Exchange", str(self.exchange.value))
        text_box.doubleLine()

        if self.sell_upper_pcnt is not None:
            text_box.line(
                "Sell Upper", str(self.sell_upper_pcnt) + "%  --sellupperpcnt  <pcnt>"
            )

        if self.sell_lower_pcnt is not None:
            text_box.line(
                "Sell Lower", str(self.sell_lower_pcnt) + "%  --selllowerpcnt  <pcnt>"
            )

        if self.no_sell_max_pcnt is not None:
            text_box.line(
                "No Sell Max",
                str(self.no_sell_max_pcnt) + "%  --no_sell_max_pcnt  <pcnt>",
            )

        if self.no_sell_min_pcnt is not None:
            text_box.line(
                "No Sell Min",
                str(self.no_sell_min_pcnt) + "%  --no_sell_min_pcnt  <pcnt>",
            )

        if self.trailing_stop_loss is not None:
            text_box.line(
                "Trailing Stop Loss",
                str(self.trailing_stop_loss) + "%  --trailingstoploss  <pcnt>",
            )

        if self.trailing_stop_loss_trigger != 0:
            text_box.line(
                "Trailing Stop Loss Trg",
                str(self.trailing_stop_loss_trigger) + "%  --trailingstoplosstrigger",
            )

        if self.dynamic_tsl is True:
            text_box.line(
                "Dynamic Trailing Stop Loss",
                str(self.dynamic_tsl) + "  --dynamictsl",
            )

        if self.dynamic_tsl is True and self.tsl_multiplier > 0:
            text_box.line(
                "Trailing Stop Loss Multiplier",
                str(self.tsl_multiplier) + "%  --tslmultiplier  <pcnt>",
            )

        if self.dynamic_tsl is True and self.tsl_trigger_multiplier > 0:
            text_box.line(
                "Stop Loss Trigger Multiplier",
                str(self.tsl_trigger_multiplier) + "%  --tsltriggermultiplier  <pcnt>",
            )

        if self.dynamic_tsl is True and self.tsl_max_pcnt > 0:
            text_box.line(
                "Stop Loss Maximum Percent",
                str(self.tsl_max_pcnt) + "%  --tslmaxpcnt  <pcnt>",
            )

        if self.preventloss is True:
            text_box.line(
                "Prevent Loss",
                str(self.preventloss) + "  --preventloss",
            )

        if self.preventloss is True and self.preventlosstrigger is not None:
            text_box.line(
                "Prevent Loss Trigger",
                str(self.preventlosstrigger) + "%  --preventlosstrigger",
            )

        if self.preventloss is True and self.preventlossmargin is not None:
            text_box.line(
                "Prevent Loss Margin",
                str(self.preventlossmargin) + "%  --preventlossmargin",
            )

        text_box.line("Sell At Loss", str(self.sell_at_loss) + "  --sellatloss ")
        text_box.line(
            "Sell At Resistance", str(self.sellatresistance) + "  --sellatresistance"
        )
        text_box.line(
            "Trade Bull Only", str(not self.disablebullonly) + "  --disablebullonly"
        )
        text_box.line(
            "Allow Buy Near High",
            str(not self.disablebuynearhigh) + "  --disablebuynearhigh",
        )
        if self.disablebuynearhigh:
            text_box.line(
                "No Buy Near High Pcnt",
                str(self.nobuynearhighpcnt) + "%  --nobuynearhighpcnt <pcnt>",
            )
        text_box.line(
            "Use Buy MACD", str(not self.disablebuymacd) + "  --disablebuymacd"
        )
        text_box.line("Use Buy EMA", str(not self.disablebuyema) + "  --disablebuyema")
        text_box.line("Use Buy OBV", str(not self.disablebuyobv) + "  --disablebuyobv")
        text_box.line(
            "Use Buy Elder-Ray",
            str(not self.disablebuyelderray) + "  --disablebuyelderray",
        )
        text_box.line(
            "Sell Fibonacci Low",
            str(not self.disablefailsafefibonaccilow)
            + "  --disablefailsafefibonaccilow",
        )

        if self.sell_lower_pcnt is not None:
            text_box.line(
                "Sell Lower Pcnt",
                str(not self.disablefailsafelowerpcnt) + "  --disablefailsafelowerpcnt",
            )

        if self.sell_upper_pcnt is not None:
            text_box.line(
                "Sell Upper Pcnt",
                str(not self.disablefailsafelowerpcnt)
                + "  --disableprofitbankupperpcnt",
            )

        text_box.line(
            "Candlestick Reversal",
            str(not self.disableprofitbankreversal) + "  --disableprofitbankreversal",
        )
        text_box.line("Telegram", str(not self.disabletelegram) + "  --disabletelegram")

        if not self.disabletelegram:
            text_box.line(
                "Telegram trades only",
                str(self.telegramtradesonly) + " --telegramtradesonly",
            )

        if not self.disabletelegram:
            text_box.line(
                "Telegram error msgs",
                str(not self.disabletelegramerrormsgs) + " --disabletelegramerrormsgs",
            )

        text_box.line(
            "Enable Pandas-ta", str(self.enable_pandas_ta) + "  --enable_pandas_ta"
        )
        text_box.line(
            "EnableCustom Strategy",
            str(self.enable_custom_strategy) + "  --enable_custom_strategy",
        )
        text_box.line("Log", str(not self.disablelog) + "  --disablelog")
        text_box.line("Tracker", str(not self.disabletracker) + "  --disabletracker")
        text_box.line("Auto restart Bot", str(self.autorestart) + "  --autorestart")
        text_box.line("Web Socket", str(self.websocket) + "  --websocket")
        text_box.line(
            "Insufficient Funds Logging",
            str(self.enableinsufficientfundslogging)
            + "  --enableinsufficientfundslogging",
        )
        text_box.line(
            "Log Buy and Sell orders in JSON",
            str(self.logbuysellinjson) + "  --logbuysellinjson",
        )

        if self.buymaxsize:
            text_box.line(
                "Max Buy Size", str(self.buymaxsize) + "  --buymaxsize <size>"
            )

        if self.buyminsize:
            text_box.line(
                "Min Buy Size", str(self.buyminsize) + "  --buyminsize <size>"
            )

        if self.buylastsellsize:
            text_box.line(
                "Buy Last Sell Size",
                str(self.buylastsellsize) + "  --buylastsellsize",
            )

        if self.trailingbuypcnt:
            text_box.line(
                "Trailing Buy Percent",
                str(self.trailingbuypcnt) + "  --trailingbuypcnt <size>",
            )

        if self.trailingimmediatebuy:
            text_box.line(
                "Immediate buy for trailingbuypcnt",
                str(self.trailingimmediatebuy) + "  --trailingImmediateBuy",
            )

        if self.trailingbuyimmediatepcnt:
            text_box.line(
                "Trailing Buy Immediate Percent",
                str(self.trailingbuyimmediatepcnt)
                + "  --trailingbuyimmediatepcnt <size>",
            )

        if self.trailingsellpcnt:
            text_box.line(
                "Trailing Sell Percent",
                str(self.trailingsellpcnt) + "  --trailingsellpcnt <size>",
            )

        if self.trailingimmediatesell:
            text_box.line(
                "Immediate sell for trailingsellpcnt",
                str(self.trailingimmediatesell) + "  --trailingimmediatesell",
            )

        if self.trailingsellimmediatepcnt:
            text_box.line(
                "Trailing Sell Immediate Percent",
                str(self.trailingsellimmediatepcnt)
                + "  --trailingsellimmediatepcnt <size>",
            )

        if self.trailingsellbailoutpcnt:
            text_box.line(
                "Trailing Sell Bailout Percent",
                str(self.trailingsellbailoutpcnt)
                + "  --trailingsellbailoutpcnt <size>",
            )

        if self.sell_trigger_override:
            text_box.line(
                "Override SellTrigger if STRONG buy",
                str(self.sell_trigger_override) + "  --trailingImmediateSell",
            )

        if self.marketmultibuycheck:
            text_box.line(
                "Check for Market Multiple Buys",
                str(self.marketmultibuycheck) + "  --marketmultibuycheck",
            )

        if self.adjust_total_periods is not None:
            text_box.line(
                "Adjust Total Periods for Market ",
                str(self.adjust_total_periods) + " --adjust_total_periods  <size>",
            )

        if self.manual_trades_only:
            text_box.line(
                "Manual Trading Only (HODL)",
                str(self.manual_trades_only) + "  --manual_trades_only",
            )

        if (
            self.disablebuyema
            and self.disablebuymacd
            and self.enable_custom_strategy is False
        ):
            text_box.center(
                "WARNING : EMA and MACD indicators disabled, no buy events will happen"
            )

        text_box.doubleLine()

    def get_date_from_iso8601_str(self, date: str):
        # if date passed from datetime.now() remove milliseconds
        if date.find(".") != -1:
            dt = date.split(".")[0]
            date = dt

        date = date.replace("T", " ") if date.find("T") != -1 else date
        # add time in case only a date is passed in
        new_date_str = f"{date} 00:00:00" if len(date) == 10 else date
        return datetime.strptime(new_date_str, "%Y-%m-%d %H:%M:%S")

    # getters

    def get_market(self):
        if self.exchange == Exchange.BINANCE:
            formatCheck = self.market.split("-") if self.market.find("-") != -1 else ""
            if not formatCheck == "":
                self.base_currency = formatCheck[0]
                self.quote_currency = formatCheck[1]
            self.market = self.base_currency + self.quote_currency

        return self.market

    def print_granularity(self) -> str:
        if self.exchange == Exchange.KUCOIN:
            return self.granularity.to_medium
        if self.exchange == Exchange.BINANCE:
            return self.granularity.to_short
        if self.exchange == Exchange.COINBASEPRO:
            return str(self.granularity.to_integer)
        if self.exchange == Exchange.DUMMY:
            return str(self.granularity.to_integer)
        raise TypeError(f'Unknown exchange "{self.exchange.name}"')

    def get_smart_switch_df(
        self,
        df: pd.DataFrame,
        market,
        granularity: Granularity,
        simstart: str = "",
        simend: str = "",
    ) -> pd.DataFrame:
        if self.is_sim:
            df_first = None
            df_last = None

            result_df_cache = df

            simstart = self.get_date_from_iso8601_str(simstart)
            simend = self.get_date_from_iso8601_str(simend)

            try:
                # if df already has data get first and last record date
                if len(df) > 0:
                    df_first = self.get_date_from_iso8601_str(
                        str(df.head(1).index.format()[0])
                    )
                    df_last = self.get_date_from_iso8601_str(
                        str(df.tail(1).index.format()[0])
                    )
                else:
                    result_df_cache = pd.DataFrame()

            except Exception:  # pylint: disable=broad-except
                # if df = None create a new data frame
                result_df_cache = pd.DataFrame()

            if df_first is None and df_last is None:
                text_box = TextBox(80, 26)

                if not self.is_sim or (self.is_sim and not self.simresultonly):
                    text_box.singleLine()
                    if self.smart_switch:
                        text_box.center(
                            f"*** Getting smartswitch ({granularity.to_short}) market data ***"
                        )
                    else:
                        text_box.center(
                            f"*** Getting ({granularity.to_short}) market data ***"
                        )

                df_first = simend
                df_first -= timedelta(minutes=((granularity.to_integer / 60) * 200))
                df1 = self.get_historical_data(
                    market,
                    granularity,
                    None,
                    str(df_first.isoformat()),
                    str(simend.isoformat()),
                )

                result_df_cache = df1
                originalSimStart = self.get_date_from_iso8601_str(str(simstart))
                adding_extra_candles = False
                while df_first.isoformat(timespec="milliseconds") > simstart.isoformat(
                    timespec="milliseconds"
                ) or df_first.isoformat(
                    timespec="milliseconds"
                ) > originalSimStart.isoformat(
                    timespec="milliseconds"
                ):
                    end_date = df_first
                    df_first -= timedelta(
                        minutes=(
                            self.adjust_total_periods * (granularity.to_integer / 60)
                        )
                    )

                    if df_first.isoformat(timespec="milliseconds") < simstart.isoformat(
                        timespec="milliseconds"
                    ):
                        df_first = self.get_date_from_iso8601_str(str(simstart))

                    df2 = self.get_historical_data(
                        market,
                        granularity,
                        None,
                        str(df_first.isoformat()),
                        str(end_date.isoformat()),
                    )

                    # check to see if there are an extra 300 candles available to be used, if not just use the original starting point
                    if (
                        self.adjust_total_periods >= 300
                        and adding_extra_candles is True
                        and len(df2) <= 0
                    ):
                        self.extra_candles_found = False
                        simstart = originalSimStart
                    else:
                        result_df_cache = pd.concat(
                            [df2.copy(), df1.copy()]
                        ).drop_duplicates()
                        df1 = result_df_cache

                    # create df with 300 candles or adjusted total periods before the required start_date to match live
                    if df_first.isoformat(
                        timespec="milliseconds"
                    ) == simstart.isoformat(timespec="milliseconds"):
                        if adding_extra_candles is False:
                            simstart -= timedelta(
                                minutes=(
                                    self.adjust_total_periods
                                    * (granularity.to_integer / 60)
                                )
                            )
                        adding_extra_candles = True
                        self.extra_candles_found = True

                if not self.is_sim or (self.is_sim and not self.simresultonly):
                    text_box.doubleLine()

            if len(result_df_cache) > 0 and "morning_star" not in result_df_cache:
                result_df_cache.sort_values(by=["date"], ascending=True, inplace=True)

            if self.smart_switch is False:
                if self.extra_candles_found is False:
                    text_box = TextBox(80, 26)
                    text_box.singleLine()
                    text_box.center(
                        f"{str(self.exchange.value)} is not returning data for the requested start date."
                    )
                    text_box.center(
                        f"Switching to earliest start date: {str(result_df_cache.head(1).index.format()[0])}"
                    )
                    text_box.singleLine()
                    self.simstart_date = str(result_df_cache.head(1).index.format()[0])

            return result_df_cache.copy()

    def get_smart_switch_historical_data_chained(
        self,
        market,
        granularity: Granularity,
        start: str = "",
        end: str = "",
    ) -> pd.DataFrame:
        if self.is_sim:
            if self.sell_smart_switch == 1:
                self.ema1226_5m_cache = self.get_smart_switch_df(
                    self.ema1226_5m_cache, market, Granularity.FIVE_MINUTES, start, end
                )
            self.ema1226_15m_cache = self.get_smart_switch_df(
                self.ema1226_15m_cache, market, Granularity.FIFTEEN_MINUTES, start, end
            )
            self.ema1226_1h_cache = self.get_smart_switch_df(
                self.ema1226_1h_cache, market, Granularity.ONE_HOUR, start, end
            )
            self.ema1226_6h_cache = self.get_smart_switch_df(
                self.ema1226_6h_cache, market, Granularity.SIX_HOURS, start, end
            )

            if len(self.ema1226_15m_cache) == 0:
                raise Exception(
                    f"No data return for selected date range {start} - {end}"
                )

            if not self.extra_candles_found:
                if granularity == Granularity.FIVE_MINUTES:
                    if (
                        self.get_date_from_iso8601_str(
                            str(self.ema1226_5m_cache.index.format()[0])
                        ).isoformat()
                        != self.get_date_from_iso8601_str(start).isoformat()
                    ):
                        text_box = TextBox(80, 26)
                        text_box.singleLine()
                        text_box.center(
                            f"{str(self.exchange.value)}is not returning data for the requested start date."
                        )
                        text_box.center(
                            f"Switching to earliest start date: {str(self.ema1226_5m_cache.head(1).index.format()[0])}"
                        )
                        text_box.singleLine()
                        self.simstart_date = str(
                            self.ema1226_5m_cache.head(1).index.format()[0]
                        )
                elif granularity == Granularity.FIFTEEN_MINUTES:
                    if (
                        self.get_date_from_iso8601_str(
                            str(self.ema1226_15m_cache.index.format()[0])
                        ).isoformat()
                        != self.get_date_from_iso8601_str(start).isoformat()
                    ):
                        text_box = TextBox(80, 26)
                        text_box.singleLine()
                        text_box.center(
                            f"{str(self.exchange.value)}is not returning data for the requested start date."
                        )
                        text_box.center(
                            f"Switching to earliest start date: {str(self.ema1226_15m_cache.head(1).index.format()[0])}"
                        )
                        text_box.singleLine()
                        self.simstart_date = str(
                            self.ema1226_15m_cache.head(1).index.format()[0]
                        )
                else:
                    if (
                        self.get_date_from_iso8601_str(
                            str(self.ema1226_1h_cache.index.format()[0])
                        ).isoformat()
                        != self.get_date_from_iso8601_str(start).isoformat()
                    ):
                        text_box = TextBox(80, 26)
                        text_box.singleLine()
                        text_box.center(
                            f"{str(self.exchange.value)} is not returning data for the requested start date."
                        )
                        text_box.center(
                            f"Switching to earliest start date: {str(self.ema1226_1h_cache.head(1).index.format()[0])}"
                        )
                        text_box.singleLine()
                        self.simstart_date = str(
                            self.ema1226_1h_cache.head(1).index.format()[0]
                        )

            if granularity == Granularity.FIFTEEN_MINUTES:
                return self.ema1226_15m_cache
            elif granularity == Granularity.FIVE_MINUTES:
                return self.ema1226_5m_cache
            else:
                return self.ema1226_1h_cache

    def get_historical_data_chained(
        self, market, granularity: Granularity, max_iterations: int = 1
    ) -> pd.DataFrame:
        df1 = self.get_historical_data(market, granularity, None)

        if max_iterations == 1:
            return df1

        def getPreviousDateRange(df: pd.DataFrame = None) -> tuple:
            end_date = df["date"].min() - timedelta(
                seconds=(granularity.to_integer / 60)
            )
            new_start = df["date"].min() - timedelta(hours=self.adjust_total_periods)
            return (str(new_start).replace(" ", "T"), str(end_date).replace(" ", "T"))

        iterations = 0
        result_df = pd.DataFrame()
        while iterations < (max_iterations - 1):
            start_date, end_date = getPreviousDateRange(df1)
            df2 = self.get_historical_data(
                market, granularity, None, start_date, end_date
            )
            result_df = pd.concat([df2, df1]).drop_duplicates()
            df1 = result_df
            iterations = iterations + 1

        if "date" in result_df:
            result_df.sort_values(by=["date"], ascending=True, inplace=True)

        return result_df

    def get_historical_data(
        self,
        market,
        granularity: Granularity,
        websocket,
        iso8601start="",
        iso8601end="",
    ):
        if self.exchange == Exchange.BINANCE:
            api = BPublicAPI(api_url=self.api_url)

        elif (
            self.exchange == Exchange.KUCOIN
        ):  # returns data from coinbase if not specified
            api = KPublicAPI(api_url=self.api_url)

            # Kucoin only returns 100 rows if start not specified, make sure we get the right amount
            if not self.is_sim and iso8601start == "":
                start = datetime.now() - timedelta(
                    minutes=(granularity.to_integer / 60) * self.adjust_total_periods
                )
                iso8601start = str(start.isoformat()).split(".")[0]

        else:  # returns data from coinbase if not specified
            api = CBPublicAPI()

        if (
            iso8601start != ""
            and iso8601end == ""
            and self.exchange != Exchange.BINANCE
        ):
            return api.get_historical_data(
                market,
                granularity,
                None,
                iso8601start,
            )
        elif iso8601start != "" and iso8601end != "":
            return api.get_historical_data(
                market,
                granularity,
                None,
                iso8601start,
                iso8601end,
            )
        else:
            return api.get_historical_data(market, granularity, websocket)

    def get_ticker(self, market, websocket):
        if self.exchange == Exchange.BINANCE:
            api = BPublicAPI(api_url=self.api_url)
            return api.get_ticker(market, websocket)

        elif self.exchange == Exchange.KUCOIN:
            api = KPublicAPI(api_url=self.api_url)
            return api.get_ticker(market, websocket)
        else:  # returns data from coinbase if not specified
            api = CBPublicAPI()
            return api.get_ticker(market, websocket)

    def get_time(self):
        if self.exchange == Exchange.COINBASEPRO:
            return CBPublicAPI().get_time()
        elif self.exchange == Exchange.KUCOIN:
            return KPublicAPI().get_time()
        elif self.exchange == Exchange.BINANCE:
            try:
                return BPublicAPI().get_time()
            except ReadTimeoutError:
                return ""
        else:
            return ""

    def get_interval(
        self, df: pd.DataFrame = pd.DataFrame(), iterations: int = 0
    ) -> pd.DataFrame:
        if len(df) == 0:
            return df

        if self.is_sim and iterations > 0:
            # with a simulation iterate through data
            return df.iloc[iterations - 1 : iterations]
        else:
            # most recent entry
            return df.tail(1)

    def is_1h_ema1226_bull(self, iso8601end: str = ""):
        try:
            if self.is_sim and isinstance(self.ema1226_1h_cache, pd.DataFrame):
                df_data = self.ema1226_1h_cache.loc[
                    self.ema1226_1h_cache["date"] <= iso8601end
                ].copy()
            elif self.exchange != Exchange.DUMMY:
                df_data = self.get_additional_df("1h", self.websocket).copy()
                self.ema1226_1h_cache = df_data
            else:
                return False

            ta = TechnicalAnalysis(df_data)

            if "ema12" not in df_data:
                ta.addEMA(12)

            if "ema26" not in df_data:
                ta.addEMA(26)

            df_last = ta.getDataFrame().copy().iloc[-1, :]
            df_last["bull"] = df_last["ema12"] > df_last["ema26"]

            return bool(df_last["bull"])
        except Exception:
            return False

    def is_6h_ema1226_bull(self, iso8601end: str = ""):
        try:
            if self.is_sim and isinstance(self.ema1226_1h_cache, pd.DataFrame):
                df_data = self.ema1226_6h_cache.loc[
                    self.ema1226_6h_cache["date"] <= iso8601end
                ].copy()
            elif self.exchange != Exchange.DUMMY:
                df_data = self.get_additional_df("6h", self.websocket).copy()
                self.ema1226_6h_cache = df_data
            else:
                return False

            ta = TechnicalAnalysis(df_data)

            if "ema12" not in df_data:
                ta.addEMA(12)

            if "ema26" not in df_data:
                ta.addEMA(26)

            df_last = ta.getDataFrame().copy().iloc[-1, :]
            df_last["bull"] = df_last["ema12"] > df_last["ema26"]

            return bool(df_last["bull"])
        except Exception:
            return False

    def is_1h_sma50200_bull(self, iso8601end: str = ""):
        # if periods adjusted and less than 200
        if self.adjust_total_periods < 200:
            return False

        try:
            if self.is_sim and isinstance(self.sma50200_1h_cache, pd.DataFrame):
                df_data = self.sma50200_1h_cache.loc[
                    self.sma50200_1h_cache["date"] <= iso8601end
                ].copy()
            elif self.exchange != Exchange.DUMMY:
                df_data = self.get_additional_df("1h", self.websocket).copy()
                self.sma50200_1h_cache = df_data
            else:
                return False

            ta = TechnicalAnalysis(df_data)

            if "sma50" not in df_data:
                ta.addSMA(50)

            if "sma200" not in df_data:
                ta.addSMA(200)

            df_last = ta.getDataFrame().copy().iloc[-1, :]
            df_last["bull"] = df_last["sma50"] > df_last["sma200"]

            return bool(df_last["bull"])
        except Exception:
            return False

    def get_additional_df(self, short_granularity, websocket) -> pd.DataFrame:
        granularity = Granularity.convert_to_enum(short_granularity)

        idx, next_idx = (None, 0)
        for i in range(len(self.df_data)):
            if (
                isinstance(self.df_data[i], list)
                and self.df_data[i][0] == short_granularity
            ):
                idx = i
            elif isinstance(self.df_data[i], list):
                next_idx = i + 1
            else:
                break

        # idx list:
        # 0 = short_granularity (1h, 6h, 1d, 5m, 15m, etc.)
        # 1 = granularity (ONE_HOUR, SIX_HOURS, FIFTEEN_MINUTES, etc.)
        # 2 = df row (for last candle date)
        # 3 = DataFrame
        if idx is None:
            idx = next_idx
            self.df_data[idx] = [short_granularity, granularity, -1, pd.DataFrame()]

        df = self.df_data[idx][3]
        row = self.df_data[idx][2]

        try:
            if len(df) == 0 or (  # empty dataframe
                len(df) > 0
                and (  # if exists, only refresh at candleclose
                    datetime.timestamp(datetime.utcnow()) - granularity.to_integer
                    >= datetime.timestamp(df["date"].iloc[row])
                )
            ):
                df = self.get_historical_data(
                    self.market, self.granularity, self.websocket
                )
                row = -1
            else:
                # if ticker hasn't run yet or hasn't updated, return the original df
                if websocket is not None and self.ticker_date is None:
                    return df
                elif self.ticker_date is None or datetime.timestamp(  # if calling API multiple times, per iteration, ticker may not be updated yet
                    datetime.utcnow()
                ) - 60 <= datetime.timestamp(
                    df["date"].iloc[row]
                ):
                    return df
                elif row == -2:  # update the new row added for ticker if it is there
                    df.iloc[-1, df.columns.get_loc("low")] = (
                        self.ticker_price
                        if self.ticker_price < df["low"].iloc[-1]
                        else df["low"].iloc[-1]
                    )
                    df.iloc[-1, df.columns.get_loc("high")] = (
                        self.ticker_price
                        if self.ticker_price > df["high"].iloc[-1]
                        else df["high"].iloc[-1]
                    )
                    df.iloc[-1, df.columns.get_loc("close")] = self.ticker_price
                    df.iloc[-1, df.columns.get_loc("date")] = datetime.strptime(
                        self.ticker_date, "%Y-%m-%d %H:%M:%S"
                    )
                    tsidx = pd.DatetimeIndex(df["date"])
                    df.set_index(tsidx, inplace=True)
                    df.index.name = "ts"
                else:  # else we are adding a new row for the ticker data
                    new_row = pd.DataFrame(
                        columns=[
                            "date",
                            "market",
                            "granularity",
                            "open",
                            "high",
                            "close",
                            "low",
                            "volume",
                        ],
                        data=[
                            [
                                datetime.strptime(
                                    self.ticker_date, "%Y-%m-%d %H:%M:%S"
                                ),
                                df["market"].iloc[-1],
                                df["granularity"].iloc[-1],
                                (
                                    self.ticker_price
                                    if self.ticker_price < df["close"].iloc[-1]
                                    else df["close"].iloc[-1]
                                ),
                                (
                                    self.ticker_price
                                    if self.ticker_price > df["close"].iloc[-1]
                                    else df["close"].iloc[-1]
                                ),
                                df["close"].iloc[-1],
                                self.ticker_price,
                                df["volume"].iloc[-1],
                            ]
                        ],
                    )
                    df = pd.concat([df, new_row], ignore_index=True)

                    tsidx = pd.DatetimeIndex(df["date"])
                    df.set_index(tsidx, inplace=True)
                    df.index.name = "ts"
                    row = -2

            self.df_data[idx][3] = df
            self.df_data[idx][2] = row
            return df
        except Exception as err:
            raise Exception(f"Additional DF Error: {err}")

    def get_last_buy(self) -> dict:
        """Retrieves the last exchange buy order and returns a dictionary"""

        try:
            if self.exchange == Exchange.COINBASEPRO:
                api = CBAuthAPI(
                    self.api_key,
                    self.api_secret,
                    self.api_passphrase,
                    self.api_url,
                )
                orders = api.get_orders(self.market, "", "done")

                if len(orders) == 0:
                    return None

                last_order = orders.tail(1)
                if last_order["action"].values[0] != "buy":
                    return None

                return {
                    "side": "buy",
                    "market": self.market,
                    "size": float(last_order["size"]),
                    "filled": float(last_order["filled"]),
                    "price": float(last_order["price"]),
                    "fee": float(last_order["fees"]),
                    "date": str(
                        pd.DatetimeIndex(
                            pd.to_datetime(last_order["created_at"]).dt.strftime(
                                "%Y-%m-%dT%H:%M:%S.%Z"
                            )
                        )[0]
                    ),
                }
            elif self.exchange == Exchange.KUCOIN:
                api = KAuthAPI(
                    self.api_key,
                    self.api_secret,
                    self.api_passphrase,
                    self.api_url,
                    use_cache=self.usekucoincache,
                )
                orders = api.get_orders(self.market, "", "done")

                if len(orders) == 0:
                    return None

                last_order = orders.tail(1)
                if last_order["action"].values[0] != "buy":
                    return None

                return {
                    "side": "buy",
                    "market": self.market,
                    "size": float(last_order["size"]),
                    "filled": float(last_order["filled"]),
                    "price": float(last_order["price"]),
                    "fee": float(last_order["fees"]),
                    "date": str(
                        pd.DatetimeIndex(
                            pd.to_datetime(last_order["created_at"]).dt.strftime(
                                "%Y-%m-%dT%H:%M:%S.%Z"
                            )
                        )[0]
                    ),
                }
            elif self.exchange == Exchange.BINANCE:
                api = BAuthAPI(
                    self.api_key,
                    self.api_secret,
                    self.api_url,
                    recv_window=self.recv_window,
                )
                orders = api.get_orders(self.market)

                if len(orders) == 0:
                    return None

                last_order = orders.tail(1)
                if last_order["action"].values[0] != "buy":
                    return None

                return {
                    "side": "buy",
                    "market": self.market,
                    "size": float(last_order["size"]),
                    "filled": float(last_order["filled"]),
                    "price": float(last_order["price"]),
                    "fees": float(last_order["size"] * 0.001),
                    "date": str(
                        pd.DatetimeIndex(
                            pd.to_datetime(last_order["created_at"]).dt.strftime(
                                "%Y-%m-%dT%H:%M:%S.%Z"
                            )
                        )[0]
                    ),
                }
            else:
                return None
        except Exception:
            return None

    def get_taker_fee(self):
        if self.is_sim is True and self.exchange == Exchange.COINBASEPRO:
            return 0.005  # default lowest fee tier
        elif self.is_sim is True and self.exchange == Exchange.BINANCE:
            return 0.001  # default lowest fee tier
        elif self.is_sim is True and self.exchange == Exchange.KUCOIN:
            return 0.0015  # default lowest fee tier
        elif self.takerfee > 0.0:
            return self.takerfee
        elif self.exchange == Exchange.COINBASEPRO:
            api = CBAuthAPI(
                self.api_key,
                self.api_secret,
                self.api_passphrase,
                self.api_url,
            )
            self.takerfee = api.get_taker_fee()
            return self.takerfee
        elif self.exchange == Exchange.BINANCE:
            api = BAuthAPI(
                self.api_key,
                self.api_secret,
                self.api_url,
                recv_window=self.recv_window,
            )
            self.takerfee = api.get_taker_fee()
            return self.takerfee
        elif self.exchange == Exchange.KUCOIN:
            api = KAuthAPI(
                self.api_key,
                self.api_secret,
                self.api_passphrase,
                self.api_url,
                use_cache=self.usekucoincache,
            )
            self.takerfee = api.get_taker_fee()
            return self.takerfee
        else:
            return 0.005

    def get_maker_fee(self):
        if self.exchange == Exchange.COINBASEPRO:
            api = CBAuthAPI(
                self.api_key,
                self.api_secret,
                self.api_passphrase,
                self.api_url,
            )
            return api.get_maker_fee()
        elif self.exchange == Exchange.BINANCE:
            api = BAuthAPI(
                self.api_key,
                self.api_secret,
                self.api_url,
                recv_window=self.recv_window,
            )
            return api.get_maker_fee()
        elif self.exchange == Exchange.KUCOIN:
            api = KAuthAPI(
                self.api_key,
                self.api_secret,
                self.api_passphrase,
                self.api_url,
                use_cache=self.usekucoincache,
            )
            return api.get_maker_fee()
        else:
            return 0.005

    def truncate(self, f: Union[int, float], n: Union[int, float]) -> str:
        """
        Format a given number ``f`` with a given precision ``n``.
        """

        if not isinstance(f, int) and not isinstance(f, float):
            return "0.0"

        if not isinstance(n, int) and not isinstance(n, float):
            return "0.0"

        if (f < 0.0001) and n >= 5:
            return f"{f:.5f}"

        # `{n}` inside the actual format honors the precision
        return f"{math.floor(f * 10 ** n) / 10 ** n:.{n}f}"

    def compare(self, val1, val2, label="", precision=2):
        if val1 > val2:
            if label == "":
                return f"{self.truncate(val1, precision)} > {self.truncate(val2, precision)}"
            else:
                return f"{label}: {self.truncate(val1, precision)} > {self.truncate(val2, precision)}"
        if val1 < val2:
            if label == "":
                return f"{self.truncate(val1, precision)} < {self.truncate(val2, precision)}"
            else:
                return f"{label}: {self.truncate(val1, precision)} < {self.truncate(val2, precision)}"
        else:
            if label == "":
                return f"{self.truncate(val1, precision)} = {self.truncate(val2, precision)}"
            else:
                return f"{label}: {self.truncate(val1, precision)} = {self.truncate(val2, precision)}"
