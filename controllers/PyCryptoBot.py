import os
import sys
import time
import json
import random
import sched
import signal
import functools
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.table import Text
from rich import box
from datetime import datetime, timedelta
from os.path import exists as file_exists
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
from models.Strategy import Strategy
from views.TradingGraphs import TradingGraphs
from views.PyCryptoBot import RichText
from utils.PyCryptoBot import truncate as _truncate
from utils.PyCryptoBot import compare as _compare

try:
    # pyright: reportMissingImports=false
    if file_exists("models/Trading_myPta.py"):
        from models.Trading_myPta import TechnicalAnalysis

        trading_myPta = True
        pandas_ta_enabled = True
    else:
        from models.Trading import TechnicalAnalysis

        trading_myPta = False
        pandas_ta_enabled = False
except ModuleNotFoundError:
    from models.Trading import TechnicalAnalysis

    trading_myPta = False
    pandas_ta_enabled = False
except ImportError:
    from models.Trading import TechnicalAnalysis

    trading_myPta = False
    pandas_ta_enabled = False

pd.set_option("display.float_format", "{:.8f}".format)


def signal_handler(signum):
    if signum == 2:
        print("Please be patient while websockets terminate!")
        return


class PyCryptoBot(BotConfig):
    def __init__(self, config_file: str = None, exchange: Exchange = None):
        self.config_file = config_file or "config.json"
        self.exchange = exchange
        super(PyCryptoBot, self).__init__(
            filename=self.config_file, exchange=self.exchange
        )

        self.console_term = Console()  # logs to the screen
        self.console_log = Console(file=open(self.logfile, "w"))   # logs to file

        self.table_console = Table(title=" ", box=box.MINIMAL, show_header=False)

        self.s = sched.scheduler(time.time, time.sleep)

        self.price = 0
        self.is_live = 0
        self.takerfee = 0.0
        self.makerfee = 0.0
        self.account = None
        self.state = None
        self.technical_analysis = None
        self.websocket_connection = None
        self.ticker_self = None
        self.df_last = pd.DataFrame()
        self.trading_data = pd.DataFrame()
        self.telegram_bot = TelegramBotHelper(self)

        self.trade_tracker = pd.DataFrame(
            columns=[
                "Datetime",
                "Market",
                "Action",
                "Price",
                "Base",
                "Quote",
                "Margin",
                "Profit",
                "Fee",
                "DF_High",
                "DF_Low",
            ]
        )

        # variables that need defining
        self.nosellminpcnt = None

        if trading_myPta is True and pandas_ta_enabled is True:
            self.enable_pandas_ta = True
        else:
            self.enable_pandas_ta = False

    def execute_job(self):
        """Trading bot job which runs at a scheduled interval"""

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
            control_status = self.telegram_bot.check_bot_control_status()
            while control_status == "pause" or control_status == "paused":
                if control_status == "pause":
                    text_box = TextBox(80, 22)
                    text_box.singleLine()
                    text_box.center(f"Pausing Bot {self.market}")
                    text_box.singleLine()
                    Logger.debug("Pausing Bot.")
                    print(str(datetime.now()).format() + " - Bot is paused")
                    self.notify_telegram(f"{self.market} bot is paused")
                    self.telegram_bot.update_bot_status("paused")
                    if self.websocket:
                        Logger.info("Closing websocket...")
                        self.websocket_connection.close()

                time.sleep(30)
                control_status = self.telegram_bot.check_bot_control_status()

            if control_status == "start":
                text_box = TextBox(80, 22)
                text_box.singleLine()
                text_box.center(f"Restarting Bot {self.market}")
                text_box.singleLine()
                Logger.debug("Restarting Bot.")
                self.notify_telegram(f"{self.market} bot has restarted")
                self.telegram_bot.update_bot_status("active")
                self.read_config(self.exchange)
                if self.websocket:
                    Logger.info("Starting websocket...")
                    self.websocket_connection.start()

            if control_status == "exit":
                text_box = TextBox(80, 22)
                text_box.singleLine()
                text_box.center(f"Closing Bot {self.market}")
                text_box.singleLine()
                Logger.debug("Closing Bot.")
                self.notify_telegram(f"{self.market} bot is stopping")
                self.telegram_bot.remove_active_bot()
                sys.exit(0)

            if control_status == "reload":
                text_box = TextBox(80, 22)
                text_box.singleLine()
                text_box.center(f"Reloading config parameters {self.market}")
                text_box.singleLine()
                Logger.debug("Reloading config parameters.")
                self.read_config(self.exchange)
                if self.websocket:
                    self.websocket_connection.close()
                    if self.exchange == Exchange.BINANCE:
                        self.websocket_connection = BWebSocketClient(
                            [self.market], self.granularity
                        )
                    elif self.exchange == Exchange.COINBASEPRO:
                        self.websocket_connection = CWebSocketClient(
                            [self.market], self.granularity
                        )
                    elif self.exchange == Exchange.KUCOIN:
                        self.websocket_connection = KWebSocketClient(
                            [self.market], self.granularity
                        )
                    self.websocket_connection.start()

                list(map(self.s.cancel, self.s.queue))
                self.s.enter(
                    5,
                    1,
                    self.execute_job,
                    (),
                )
                # self.read_config(self.exchange)
                self.telegram_bot.update_bot_status("active")
        else:
            # runs once at the start of a simulation
            if self.app_started:
                if self.simstart_date is not None:
                    self.state.iterations = self.trading_data.index.get_loc(
                        str(self.get_date_from_iso8601_str(self.simstart_date))
                    )

                self.app_started = False

        # reset self.websocket_connection every 23 hours if applicable
        if self.websocket and not self.is_sim:
            if self.websocket_connection.time_elapsed > 82800:
                Logger.info("Websocket requires a restart every 23 hours!")
                Logger.info("Stopping self.websocket_connection...")
                self.websocket_connection.close()
                Logger.info("Starting self.websocket_connection...")
                self.websocket_connection.start()
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
                    self.market, self.granularity, self.websocket_connection
                )
                self.state.closed_candle_row = -1
                self.price = float(
                    self.trading_data.iloc[
                        -1, self.trading_data.columns.get_loc("close")
                    ]
                )

            else:
                # set time and price with ticker data and add/update current candle
                ticker = self.get_ticker(self.market, self.websocket_connection)
                # if 0, use last close value as self.price
                self.price = (
                    self.trading_data["close"].iloc[-1] if ticker[1] == 0 else ticker[1]
                )
                self.ticker_date = ticker[0]
                self.ticker_price = ticker[1]

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

                    self.telegram_bot.close_trade(
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
                ema12ltema26co = bool(self.df_last["ema12ltema26co"].values[0])
                macdltsignal = bool(self.df_last["macdltsignal"].values[0])
                macdltsignalco = bool(self.df_last["macdltsignalco"].values[0])
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
            self.telegram_bot.add_indicators("EMA", ema12gtema26 or ema12gtema26co)
            if not self.disablebuyelderray:
                self.telegram_bot.add_indicators("ERI", elder_ray_buy)
            if self.disablebullonly:
                self.telegram_bot.add_indicators("BULL", goldencross)
            if not self.disablebuymacd:
                self.telegram_bot.add_indicators("MACD", macdgtsignal or macdgtsignalco)
            if not self.disablebuyobv:
                self.telegram_bot.add_indicators("OBV", float(obv_pc) > 0)

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
            self.state.action, indicatorvalues = strategy.get_action(
                self.state, self.price, current_sim_date, self.websocket_connection
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
                    sell_percent=self.get_sell_percent(),
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

            if not self.is_sim and self.enable_telegram_bot_control:
                manual_buy_sell = self.telegram_bot.check_manual_buy_sell()
                if not manual_buy_sell == "WAIT":
                    self.state.action = manual_buy_sell
                    immediate_action = True

            # polling is every 5 minutes (even for hourly intervals), but only process once per interval
            # Logger.debug("DateCheck: " + str(immediate_action) + ' ' + str(self.state.last_df_index) + ' ' + str(current_df_index))
            if immediate_action is True or self.state.last_df_index != current_df_index:
                text_box = TextBox(80, 22)

                precision = 4

                if self.price < 0.01:
                    precision = 8

                # Since precision does not change after this point, it is safe to prepare a tailored `truncate()` that would
                # work with this precision. It should save a couple of `precision` uses, one for each `truncate()` call.
                truncate = functools.partial(_truncate, n=precision)

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

                if log_text != "" and (
                    not self.is_sim or (self.is_sim and not self.simresultonly)
                ):
                    Logger.info(log_text)

                if not self.is_sim:
                    df_high = df[df["date"] <= current_sim_date]["close"].max()
                    df_low = df[df["date"] <= current_sim_date]["close"].min()
                    range_start = str(df.iloc[0, 0])
                    range_end = str(df.iloc[len(df) - 1, 0])
                    iteration_text = ""
                else:
                    df_high = df['close'].max()
                    df_low = df['close'].min()
                    range_start = str(df.iloc[self.state.iterations - self.adjust_total_periods, 0])
                    range_end = str(df.iloc[self.state.iterations - 1, 0])

                    iteration_text = str(df.iloc[self.state.iterations - 1, 0])

                df_swing = round(((df_high - df_low) / df_low) * 100, 2)
                df_near_high = round(((self.price - df_high) / df_high) * 100, 2)

                args = [
                    arg
                    for arg in [
                        RichText.styled_text("Bot1", "magenta"),
                        RichText.styled_text(formatted_current_df_index, "white"),
                        RichText.styled_text(self.market, "yellow"),
                        RichText.styled_text(self.print_granularity(), "yellow"),
                        RichText.styled_text(str(self.price), "white"),
                        RichText.bull_bear(goldencross),
                        RichText.number_comparison(
                            "EMA12/26:",
                            round(self.df_last["ema12"].values[0], 2),
                            round(self.df_last["ema26"].values[0], 2),
                            ema12gtema26co or ema12ltema26co,
                            self.disablebuyema,
                        ),
                        RichText.number_comparison(
                            "MACD:",
                            round(self.df_last["macd"].values[0], 2),
                            round(self.df_last["signal"].values[0], 2),
                            macdgtsignalco or macdltsignalco,
                            self.disablebuymacd,
                        ),
                        RichText.styled_text(trailing_action_logtext),
                        RichText.on_balance_volume(self.df_last["obv"].values[0], self.df_last["obv_pc"].values[0], self.disablebuyobv),
                        RichText.elder_ray(elder_ray_buy, elder_ray_sell, self.disablebuyelderray),
                        RichText.action_text(self.state.action),
                        RichText.last_action_text(self.state.last_action),
                        RichText.styled_text(f"DF-H/L: {str(df_high)} / {str(df_low)} ({df_swing}%)", "white"),
                        RichText.styled_text(f"Near-High: {df_near_high}%", "white"),  # price near high
                        RichText.styled_text(f"Range: {range_start} <-> {range_end}", "white"),
                        RichText.styled_text(f"{iteration_text}", "white"),
                    ]
                    if arg
                ]

                output_text = ""

                if self.state.last_action != "":
                    self.table_console.add_row(*args)
                    self.console_term.print(self.table_console)
                    if self.disablelog is False:
                        self.console_log.print(self.table_console)
                    self.table_console = Table(title=" ", box=box.MINIMAL, show_header=False)  # clear table

                    if self.state.last_action == "BUY":
                        if self.state.last_buy_size > 0:
                            margin_text = truncate(margin) + "%"
                        else:
                            margin_text = "0%"

                        output_text = (
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

                # if a buy signal
                if self.state.action == "BUY":
                    self.state.last_buy_price = self.price
                    self.state.last_buy_high = self.state.last_buy_price

                    # if live
                    if self.is_live:
                        ac = self.account.get_balance()
                        self.account.base_balance_before = 0.0
                        self.account.quote_balance_before = 0.0
                        try:
                            df_base = ac[ac["currency"] == self.base_currency][
                                "available"
                            ]
                            self.account.base_balance_before = (
                                0.0 if len(df_base) == 0 else float(df_base.values[0])
                            )

                            df_quote = ac[ac["currency"] == self.quote_currency][
                                "available"
                            ]
                            self.account.quote_balance_before = (
                                0.0 if len(df_quote) == 0 else float(df_quote.values[0])
                            )
                        except Exception:
                            pass

                        if (
                            not self.insufficientfunds
                            and self.buyminsize < self.account.quote_balance_before
                        ):
                            if not self.is_verbose:
                                if not self.is_sim or (
                                    self.is_sim and not self.simresultonly
                                ):
                                    Logger.info(
                                        f"{formatted_current_df_index} | {self.market} | {self.print_granularity()} | {str(self.price)} | BUY"
                                    )
                            else:
                                text_box.singleLine()
                                text_box.center("*** Executing LIVE Buy Order ***")
                                text_box.singleLine()

                            # display balances
                            Logger.info(
                                f"{self.base_currency} balance before order: {str(self.account.base_balance_before)}"
                            )
                            Logger.info(
                                f"{self.quote_currency} balance before order: {str(self.account.quote_balance_before)}"
                            )

                            # execute a live market buy
                            self.state.last_buy_size = float(
                                self.account.quote_balance_before
                            )

                            if (
                                self.buymaxsize
                                and self.buylastsellsize
                                and self.state.minimum_order_quote(
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
                                    self.get_buy_percent(),
                                )
                                resp_error = 0
                            except Exception as err:
                                Logger.warning(f"Trade Error: {err}")
                                resp_error = 1

                            if resp_error == 0:
                                self.account.base_balance_after = 0
                                self.account.quote_balance_after = 0
                                try:
                                    ac = self.account.get_balance()
                                    df_base = ac[ac["currency"] == self.base_currency][
                                        "available"
                                    ]
                                    self.account.base_balance_after = (
                                        0.0
                                        if len(df_base) == 0
                                        else float(df_base.values[0])
                                    )
                                    df_quote = ac[
                                        ac["currency"] == self.quote_currency
                                    ]["available"]

                                    self.account.quote_balance_after = (
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
                                        f"{self.base_currency} balance after order: {str(self.account.base_balance_after)}\n"
                                        f"{self.quote_currency} balance after order: {str(self.account.quote_balance_after)}"
                                    )

                                    self.notify_telegram(
                                        self.market
                                        + " ("
                                        + self.print_granularity()
                                        + ") - "
                                        + datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                                        + "\n"
                                        + "BUY at "
                                        + str(self.price)
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
                            > self.state.minimum_order_quote(
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

                        if not self.disabletelegram:
                            self.notify_telegram(
                                self.market
                                + " ("
                                + self.print_granularity()
                                + ") -  "
                                + str(current_sim_date)
                                + "\n - TEST BUY at "
                                + str(self.price)
                                + "\n - Buy Size: "
                                + str(_truncate(self.state.last_buy_size, 4))
                            )

                        if not self.is_verbose:
                            if not self.is_sim or (
                                self.is_sim and not self.simresultonly
                            ):
                                Logger.info(
                                    f"{formatted_current_df_index} | {self.market} | {self.print_granularity()} | {str(self.price)} | BUY"
                                )

                            bands = _technical_analysis.get_fib_ret_levels(
                                float(self.price)
                            )

                            if not self.is_sim or (
                                self.is_sim and not self.simresultonly
                            ):
                                _technical_analysis.print_sup_res_level(
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

                    if self.save_graphs:
                        if self.adjust_total_periods < 200:
                            Logger.info(
                                "Trading Graphs can only be generated when dataframe has more than 200 periods."
                            )
                        else:
                            tradinggraphs = TradingGraphs(_technical_analysis)
                            ts = datetime.now().timestamp()
                            filename = f"{self.market}_{self.print_granularity()}_buy_{str(ts)}.png"
                            # This allows graphs to be used in sim mode using the correct DF
                            if self.is_sim:
                                tradinggraphs.render_ema_and_macd(
                                    len(trading_dataCopy), "graphs/" + filename, True
                                )
                            else:
                                tradinggraphs.render_ema_and_macd(
                                    len(trading_data), "graphs/" + filename, True
                                )

                # if a sell signal
                elif self.state.action == "SELL":
                    # if live
                    if self.is_live:
                        if self.is_verbose:

                            bands = _technical_analysis.get_fib_ret_levels(
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

                            text_box.singleLine()
                            text_box.center("*** Executing LIVE Sell Order ***")
                            text_box.singleLine()

                        else:
                            Logger.info(
                                f"{formatted_current_df_index} | {self.market} | {self.print_granularity()} | {str(self.price)} | SELL"
                            )

                        # check balances before and display
                        self.account.base_balance_before = 0
                        self.account.quote_balance_before = 0
                        try:
                            self.account.base_balance_before = float(
                                self.account.get_balance(self.base_currency)
                            )
                            self.account.quote_balance_before = float(
                                self.account.get_balance(self.quote_currency)
                            )
                        except Exception:
                            pass

                        Logger.info(
                            f"{self.base_currency} balance before order: {str(self.account.base_balance_before)}\n"
                            f"{self.quote_currency} balance before order: {str(self.account.quote_balance_before)}"
                        )

                        # execute a live market sell
                        baseamounttosell = (
                            float(self.account.base_balance_before)
                            if self.sellfullbaseamount is True
                            else float(self.state.last_buy_filled)
                        )

                        self.account.base_balance_after = 0
                        self.account.quote_balance_after = 0
                        # place the sell order
                        try:
                            self.marketSell(
                                self.market,
                                baseamounttosell,
                                self.get_sell_percent(),
                            )
                            resp_error = 0
                        except Exception as err:
                            Logger.warning(f"Trade Error: {err}")
                            resp_error = 1

                        if resp_error == 0:
                            try:
                                self.account.base_balance_after = float(
                                    self.account.get_balance(self.base_currency)
                                )
                                self.account.quote_balance_after = float(
                                    self.account.get_balance(self.quote_currency)
                                )
                                bal_error = 0
                            except Exception as err:
                                bal_error = 1
                                Logger.warning(
                                    f"Error: Balance not retrieved after trade for {self.market}.\n"
                                    f"API Error Msg: {err}"
                                )

                            if bal_error == 0:
                                Logger.info(
                                    f"{self.base_currency} balance after order: {str(self.account.base_balance_after)}\n"
                                    f"{self.quote_currency} balance after order: {str(self.account.quote_balance_after)}"
                                )
                                self.state.prevent_loss = False
                                self.state.trailing_sell = False
                                self.state.trailing_sell_immediate = False
                                self.state.tsl_triggered = False
                                self.state.tsl_pcnt = float(self.trailing_stop_loss)
                                self.state.tsl_trigger = float(
                                    self.trailing_stop_loss_trigger
                                )
                                self.state.tsl_max = False
                                self.state.trade_error_cnt = 0
                                self.state.last_action = "SELL"
                                self.state.action = "DONE"

                                self.notify_telegram(
                                    self.market
                                    + " ("
                                    + self.print_granularity()
                                    + ") - "
                                    + datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                                    + "\n"
                                    + "SELL at "
                                    + str(self.price)
                                    + " (margin: "
                                    + margin_text
                                    + ", delta: "
                                    + str(
                                        round(
                                            self.price - self.state.last_buy_price,
                                            precision,
                                        )
                                    )
                                    + ")"
                                )

                                self.telegram_bot.close_trade(
                                    str(
                                        self.get_date_from_iso8601_str(
                                            str(datetime.now())
                                        )
                                    ),
                                    str(self.price),
                                    margin_text,
                                )

                                if (
                                    self.enableexitaftersell
                                    and self.startmethod
                                    not in (
                                        "standard",
                                        "telegram",
                                    )
                                ):
                                    sys.exit(0)

                            else:
                                # set variable to trigger to check trade on next iteration
                                self.state.action = "check_action"

                                Logger.info(
                                    self.market
                                    + " - Error occurred while checking balance after SELL. Last transaction check will happen shortly."
                                )

                                if not self.disabletelegramerrormsgs:
                                    self.notify_telegram(
                                        self.market
                                        + " - Error occurred while checking balance after SELL. Last transaction check will happen shortly."
                                    )

                        else:  # there was an error
                            # only attempt SELL 3 times before exception to prevent continuous loop
                            self.state.trade_error_cnt += 1
                            if self.state.trade_error_cnt >= 2:  # 3 attempts made
                                raise Exception(
                                    "Trade Error: SELL transaction attempted 3 times. Check log for errors."
                                )
                            # set variable to trigger to check trade on next iteration
                            self.state.action = "check_action"
                            self.state.last_action = None

                            Logger.warning(
                                f"API Error: Unable to place SELL order for {self.market}."
                            )
                            if not self.disabletelegramerrormsgs:
                                self.notify_telegram(
                                    f"API Error: Unable to place SELL order for {self.market}"
                                )
                            time.sleep(30)

                        self.state.last_api_call_datetime -= timedelta(seconds=60)

                    # if not live
                    else:
                        margin, profit, sell_fee = calculate_margin(
                            buy_size=self.state.last_buy_size,
                            buy_filled=self.state.last_buy_filled,
                            buy_price=self.state.last_buy_price,
                            buy_fee=self.state.last_buy_fee,
                            sell_percent=self.get_sell_percent(),
                            sell_price=self.price,
                            sell_taker_fee=self.get_taker_fee(),
                        )

                        if self.state.last_buy_size > 0:
                            margin_text = truncate(margin) + "%"
                        else:
                            margin_text = "0%"

                        # save last buy before this sell to use in Sim Summary
                        self.state.previous_buy_size = self.state.last_buy_size
                        # preserve next sell values for simulator
                        self.state.sell_count = self.state.sell_count + 1
                        sell_size = (self.get_sell_percent() / 100) * (
                            (self.price / self.state.last_buy_price)
                            * (self.state.last_buy_size - self.state.last_buy_fee)
                        )
                        self.state.last_sell_size = sell_size - sell_fee
                        self.state.sell_sum = (
                            self.state.sell_sum + self.state.last_sell_size
                        )

                        # added to track profit and loss margins during sim runs
                        self.state.margintracker += float(margin)
                        self.state.profitlosstracker += float(profit)
                        self.state.feetracker += float(sell_fee)
                        self.state.buy_tracker += float(self.state.last_buy_size)

                        if not self.disabletelegram:
                            self.notify_telegram(
                                self.market
                                + " ("
                                + self.print_granularity()
                                + ") "
                                + str(current_sim_date)
                                + "\n - TEST SELL at "
                                + str(str(self.price))
                                + " (margin: "
                                + margin_text
                                + ", delta: "
                                + str(
                                    round(
                                        self.price - self.state.last_buy_price,
                                        precision,
                                    )
                                )
                                + ")"
                            )

                        if not self.is_verbose:
                            if self.price > 0:
                                margin_text = truncate(margin) + "%"
                            else:
                                margin_text = "0%"

                            if not self.is_sim or (
                                self.is_sim and not self.simresultonly
                            ):
                                Logger.info(
                                    formatted_current_df_index
                                    + " | "
                                    + self.market
                                    + " | "
                                    + self.print_granularity()
                                    + " | SELL | "
                                    + str(self.price)
                                    + " | BUY | "
                                    + str(self.state.last_buy_price)
                                    + " | DIFF | "
                                    + str(self.price - self.state.last_buy_price)
                                    + " | DIFF | "
                                    + str(profit)
                                    + " | MARGIN NO FEES | "
                                    + margin_text
                                    + " | MARGIN FEES | "
                                    + str(round(sell_fee, precision))
                                )

                        else:
                            text_box.singleLine()
                            text_box.center("*** Executing TEST Sell Order ***")
                            text_box.singleLine()

                        self.trade_tracker = pd.concat(
                            [
                                self.trade_tracker,
                                pd.DataFrame(
                                    {
                                        "Datetime": str(current_sim_date),
                                        "Market": self.market,
                                        "Action": "SELL",
                                        "Price": self.price,
                                        "Quote": self.state.last_sell_size,
                                        "Base": self.state.last_buy_filled,
                                        "Margin": margin,
                                        "Profit": profit,
                                        "Fee": sell_fee,
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

                        self.state.in_open_trade = False
                        self.state.last_api_call_datetime -= timedelta(seconds=60)
                        self.state.last_action = "SELL"
                        self.state.prevent_loss = False
                        self.state.trailing_sell = False
                        self.state.trailing_sell_immediate = False
                        self.state.tsl_triggered = False

                        if self.trailing_stop_loss:
                            self.state.tsl_pcnt = float(self.trailing_stop_loss)

                        if self.trailing_stop_loss_trigger:
                            self.state.tsl_trigger = float(
                                self.trailing_stop_loss_trigger
                            )

                        self.state.tsl_max = False
                        self.state.action = "DONE"

                    if self.save_graphs:
                        tradinggraphs = TradingGraphs(_technical_analysis)
                        ts = datetime.now().timestamp()
                        filename = f"{self.market}_{self.print_granularity()}_sell_{str(ts)}.png"
                        # This allows graphs to be used in sim mode using the correct DF
                        if self.is_sim:
                            tradinggraphs.render_ema_and_macd(
                                len(trading_dataCopy), "graphs/" + filename, True
                            )
                        else:
                            tradinggraphs.render_ema_and_macd(
                                len(trading_data), "graphs/" + filename, True
                            )

            self.state.last_df_index = str(self.df_last.index.format()[0])

            if (
                self.logbuysellinjson is True
                and self.state.action == "DONE"
                and len(self.trade_tracker) > 0
            ):
                Logger.info(
                    self.trade_tracker.loc[len(self.trade_tracker) - 1].to_json()
                )

            if self.state.action == "DONE" and indicatorvalues != "":
                self.notify_telegram(indicatorvalues)

            if not self.is_live and self.state.iterations == len(df):
                simulation = {
                    "config": {},
                    "data": {
                        "open_buy_excluded": 1,
                        "buy_count": 0,
                        "sell_count": 0,
                        "first_trade": {"size": 0},
                        "last_trade": {"size": 0},
                        "margin": 0.0,
                    },
                    "exchange": self.exchange,
                }

                if self.get_config() != "":
                    simulation["config"] = self.get_config()

                if not self.simresultonly:
                    Logger.info(f"\nSimulation Summary: {self.market}")

                tradesfile = self.tradesfile

                if self.is_verbose:
                    Logger.info("\n" + str(self.trade_tracker))
                    start = str(df.head(1).index.format()[0]).replace(":", ".")
                    end = str(df.tail(1).index.format()[0]).replace(":", ".")
                    filename = f"{self.market} {str(start)} - {str(end)}_{tradesfile}"

                else:
                    filename = tradesfile
                try:
                    if not os.path.isabs(filename):
                        if not os.path.exists("csv"):
                            os.makedirs("csv")
                        filename = os.path.join(os.curdir, "csv", filename)
                    self.trade_tracker.to_csv(filename)
                except OSError:
                    Logger.critical(f"Unable to save: {filename}")

                if self.state.buy_count == 0:
                    self.state.last_buy_size = 0
                    self.state.sell_sum = 0
                else:
                    self.state.sell_sum = (
                        self.state.sell_sum + self.state.last_sell_size
                    )

                remove_last_buy = False
                if self.state.buy_count > self.state.sell_count:
                    remove_last_buy = True
                    self.state.buy_count -= 1  # remove last buy as there has not been a corresponding sell yet
                    self.state.last_buy_size = self.state.previous_buy_size
                    simulation["data"]["open_buy_excluded"] = 1

                    if not self.simresultonly:
                        Logger.info(
                            "\nWarning: simulation ended with an open trade and it will be excluded from the margin calculation."
                        )
                        Logger.info(
                            "         (it is not realistic to hard sell at the end of a simulation without a sell signal)"
                        )
                else:
                    simulation["data"]["open_buy_excluded"] = 0

                if not self.simresultonly:
                    Logger.info("\n")

                if remove_last_buy is True:
                    if not self.simresultonly:
                        Logger.info(
                            f"   Buy Count : {str(self.state.buy_count)} (open buy excluded)"
                        )
                    else:
                        simulation["data"]["buy_count"] = self.state.buy_count
                else:
                    if not self.simresultonly:
                        Logger.info(f"   Buy Count : {str(self.state.buy_count)}")
                    else:
                        simulation["data"]["buy_count"] = self.state.buy_count

                if not self.simresultonly:
                    Logger.info(f"  Sell Count : {str(self.state.sell_count)}")
                    Logger.info(f"   First Buy : {str(self.state.first_buy_size)}")
                    Logger.info(
                        f"   Last Buy : {str(_truncate(self.state.last_buy_size, 4))}"
                    )
                else:
                    simulation["data"]["sell_count"] = self.state.sell_count
                    simulation["data"]["first_trade"] = {}
                    simulation["data"]["first_trade"][
                        "size"
                    ] = self.state.first_buy_size

                if self.state.sell_count > 0:
                    if not self.simresultonly:
                        Logger.info(
                            f"   Last Sell : {_truncate(self.state.last_sell_size, 4)}\n"
                        )
                    else:
                        simulation["data"]["last_trade"] = {}
                        simulation["data"]["last_trade"]["size"] = float(
                            _truncate(self.state.last_sell_size, 2)
                        )
                else:
                    if not self.simresultonly:
                        Logger.info("\n")
                        Logger.info("      Margin : 0.00%")
                        Logger.info("\n")
                        Logger.info(
                            "  ** margin is nil as a sell has not occurred during the simulation\n"
                        )
                    else:
                        simulation["data"]["margin"] = 0.0

                    self.notify_telegram(
                        "      Margin: 0.00%\n  ** margin is nil as a sell has not occurred during the simulation\n"
                    )

                self.notify_telegram(
                    "Simulation Summary\n"
                    + f"   Market: {self.market}\n"
                    + f"   Buy Count: {self.state.buy_count}\n"
                    + f"   Sell Count: {self.state.sell_count}\n"
                    + f"   First Buy: {self.state.first_buy_size}\n"
                    + f"   Last Buy: {str(_truncate(self.state.last_buy_size, 4))}\n"
                    + f"   Last Sell: {str(_truncate(self.state.last_sell_size, 4))}\n"
                )

                if self.state.sell_count > 0:
                    _last_trade_margin = _truncate(
                        (
                            (
                                (self.state.last_sell_size - self.state.last_buy_size)
                                / self.state.last_buy_size
                            )
                            * 100
                        ),
                        4,
                    )

                    if not self.simresultonly:
                        Logger.info(
                            "   Last Trade Margin : " + _last_trade_margin + "%"
                        )
                        if remove_last_buy:
                            Logger.info(
                                f"\n   Open Trade Margin at end of simulation: {self.state.open_trade_margin}"
                            )
                        Logger.info("\n")
                        Logger.info(
                            f"   All Trades Buys ({self.quote_currency}): {_truncate(self.state.buy_tracker, 2)}"
                        )
                        Logger.info(
                            f"   All Trades Profit/Loss ({self.quote_currency}): {_truncate(self.state.profitlosstracker, 2)} ({_truncate(self.state.feetracker,2)} in fees)"
                        )
                        Logger.info(
                            f"   All Trades Margin : {_truncate(self.state.margintracker, 4)}%"
                        )
                        Logger.info("\n")
                        Logger.info("  ** non-live simulation, assuming highest fees")
                        Logger.info(
                            "  ** open trade excluded from margin calculation\n"
                        )
                    else:
                        simulation["data"]["last_trade"]["margin"] = _last_trade_margin
                        simulation["data"]["all_trades"] = {}
                        simulation["data"]["all_trades"][
                            "quote_currency"
                        ] = self.quote_currency
                        simulation["data"]["all_trades"]["value_buys"] = float(
                            _truncate(self.state.buy_tracker, 2)
                        )
                        simulation["data"]["all_trades"]["profit_loss"] = float(
                            _truncate(self.state.profitlosstracker, 2)
                        )
                        simulation["data"]["all_trades"]["fees"] = float(
                            _truncate(self.state.feetracker, 2)
                        )
                        simulation["data"]["all_trades"]["margin"] = float(
                            _truncate(self.state.margintracker, 4)
                        )

                    ## Revised telegram Summary notification to give total margin in addition to last trade margin.
                    self.notify_telegram(
                        f"      Last Trade Margin: {_last_trade_margin}%\n\n"
                    )
                    if remove_last_buy:
                        self.notify_telegram(
                            f"\nOpen Trade Margin at end of simulation: {self.state.open_trade_margin}\n"
                        )
                    self.notify_telegram(
                        f"      All Trades Margin: {_truncate(self.state.margintracker, 4)}%\n  ** non-live simulation, assuming highest fees\n  ** open trade excluded from margin calculation\n"
                    )
                    self.telegram_bot.remove_active_bot()

                if self.simresultonly:
                    Logger.info(json.dumps(simulation, sort_keys=True, indent=4))

        else:
            if (
                self.state.last_buy_size > 0
                and self.state.last_buy_price > 0
                and self.price > 0
                and self.state.last_action == "BUY"
            ):
                # show profit and margin if already bought
                Logger.info(
                    f"{now} | {self.market} TODO: BULL/BEAR | {self.print_granularity()} | Current self.price: {str(self.price)} {trailing_action_logtext} | Margin: {str(margin)} | Profit: {str(profit)}"
                )
            else:
                Logger.info(
                    f'{now} | {self.market} TODO: BULL/BEAR | {self.print_granularity()} | Current self.price: {str(self.price)}{trailing_action_logtext} | {str(round(((self.price-df["close"].max()) / df["close"].max())*100, 2))}% from DF HIGH'
                )
                self.telegram_bot.add_info(
                    f'{now} | {self.market} TODO: BULL/BEAR | {self.print_granularity()} | Current self.price: {str(self.price)}{trailing_action_logtext} | {str(round(((self.price-df["close"].max()) / df["close"].max())*100, 2))}% from DF HIGH',
                    round(self.price, 4),
                    str(round(df["close"].max(), 4)),
                    str(
                        round(
                            ((self.price - df["close"].max()) / df["close"].max())
                            * 100,
                            2,
                        )
                    )
                    + "%",
                    self.state.action,
                )

            if (
                self.state.last_action == "BUY"
                and self.state.in_open_trade
                and last_api_call_datetime.seconds > 60
            ):
                # update margin for telegram bot
                self.telegram_bot.add_margin(
                    str(_truncate(margin, 4) + "%")
                    if self.state.in_open_trade is True
                    else " ",
                    str(_truncate(profit, 2))
                    if self.state.in_open_trade is True
                    else " ",
                    self.price,
                    change_pcnt_high,
                    self.state.action,
                )

            # Update the watchdog_ping
            self.telegram_bot.update_watch_dog_ping()

            # decrement ignored iteration
            if self.is_sim and self.smart_switch:
                self.state.iterations = self.state.iterations - 1

        # if live but not websockets
        if not self.disabletracker and self.is_live and not self.websocket_connection:
            # update order tracker csv
            if self.exchange == Exchange.BINANCE:
                self.account.saveTrackerCSV(self.market)
            elif (
                self.exchange == Exchange.COINBASEPRO
                or self.exchange == Exchange.KUCOIN
            ):
                self.account.saveTrackerCSV()

        if self.is_sim:
            if self.state.iterations < len(df):
                if self.sim_speed in ["fast", "fast-sample"]:
                    # fast processing
                    list(map(self.s.cancel, self.s.queue))
                    self.s.enter(
                        0,
                        1,
                        self.execute_job,
                        (),
                    )
                else:
                    # slow processing
                    list(map(self.s.cancel, self.s.queue))
                    self.s.enter(
                        1,
                        1,
                        self.execute_job,
                        (),
                    )

        else:
            list(map(self.s.cancel, self.s.queue))
            if (
                self.websocket_connection
                and self.websocket_connection is not None
                and (
                    isinstance(self.websocket_connection.tickers, pd.DataFrame)
                    and len(self.websocket_connection.tickers) == 1
                )
                and (
                    isinstance(self.websocket_connection.candles, pd.DataFrame)
                    and len(self.websocket_connection.candles)
                    == self.adjust_total_periods
                )
            ):
                # poll every 5 seconds (self.websocket_connection)
                self.s.enter(
                    5,
                    1,
                    self.execute_job,
                    (),
                )
            else:
                if self.websocket and not self.is_sim:
                    # poll every 15 seconds (waiting for self.websocket_connection)
                    self.s.enter(
                        15,
                        1,
                        self.execute_job,
                        (),
                    )
                else:
                    # poll every 1 minute (no self.websocket_connection)
                    self.s.enter(
                        60,
                        1,
                        self.execute_job,
                        (),
                    )

    def run(self):
        try:
            message = "Starting "
            if self.exchange == Exchange.COINBASEPRO:
                message += "Coinbase Pro bot"
                if self.websocket and not self.is_sim:
                    print("Opening websocket to Coinbase Pro...")
                    self.websocket_connection = CWebSocketClient(
                        [self.market], self.granularity
                    )
                    self.websocket_connection.start()
            elif self.exchange == Exchange.BINANCE:
                message += "Binance bot"
                if self.websocket and not self.is_sim:
                    print("Opening websocket to Binance...")
                    self.websocket_connection = BWebSocketClient(
                        [self.market], self.granularity
                    )
                    self.websocket_connection.start()
            elif self.exchange == Exchange.KUCOIN:
                message += "Kucoin bot"
                if self.websocket and not self.is_sim:
                    print("Opening websocket to Kucoin...")
                    self.websocket_connection = KWebSocketClient(
                        [self.market], self.granularity
                    )
                    self.websocket_connection.start()

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
                    self.telegram_bot.remove_active_bot()
                except Exception:
                    pass
                if self.websocket and self.websocket_connection and not self.is_sim:
                    try:
                        self.websocket_connection.close()
                    except Exception:
                        pass
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
                    self.telegram_bot.remove_active_bot()
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

        self.state.init_last_action()

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
        table = Table(title=f"Python Crypto Bot {self.get_version_from_readme()}")

        table.add_column("Item", justify="right", style="cyan", no_wrap=True)
        table.add_column("Value", justify="left", style="green")
        table.add_column("Description", justify="left", style="magenta")
        table.add_column("Option", justify="left", style="white")

        table.add_row("Start", str(datetime.now()), "Bot start time")

        table.add_row("", "", "")

        table.add_row(
            "Exchange",
            str(self.exchange.value),
            "Crypto currency exchange",
            "--exchange",
        )
        table.add_row("Market", self.market, "Market to trade on", "--market")
        table.add_row(
            "Granularity",
            str(self.granularity).replace("Granularity.", ""),
            "Granularity of the data",
            "--granularity",
        )

        table.add_row("", "", "")

        if self.is_live:
            table.add_row("Bot Mode", "LIVE", "Live trades using your funds!", "--live")
        else:
            if self.is_sim:
                table.add_row(
                    "Bot Mode", "SIMULATION", "Back testing using simulations", "--live"
                )
            else:
                table.add_row(
                    "Bot Mode", "TEST", "Test trades using dummy funds :)", "--live"
                )

        table.add_row("", "", "")

        if self.disabletelegram is False:
            table.add_row(
                "Telegram Notifications",
                str(not self.disabletelegram),
                "Disable Telegram notifications",
                "--disabletelegram",
            )
        else:
            table.add_row(
                "Telegram Notifications",
                str(not self.disabletelegram),
                "Disable Telegram notifications",
                "--disabletelegram",
                style="grey62",
            )

        if self.disabletelegram is False and self.disable_telegram_error_msg is False:
            table.add_row(
                "Telegram Error Messages",
                str(not self.disabletelegramerrormsgs),
                "Disable Telegram error messages",
                "--disabletelegramerrormsgs",
            )
        else:
            table.add_row(
                "Telegram Error Messages",
                str(not self.disabletelegramerrormsgs),
                "Disable Telegram error messages",
                "--disabletelegramerrormsgs",
                style="grey62",
            )

        table.add_row("", "", "")

        if self.enable_pandas_ta is True:
            table.add_row(
                "Enable Pandas-ta",
                str(self.enable_pandas_ta),
                "Enable Pandas Technical Analysis",
                "--enable_pandas_ta",
            )
        else:
            table.add_row(
                "Enable Pandas-ta",
                str(self.enable_pandas_ta),
                "Enable Pandas Technical Analysis",
                "--enable_pandas_ta",
                style="grey62",
            )

        if self.enable_custom_strategy is True:
            table.add_row(
                "Enable Custom Strategy",
                str(self.enable_custom_strategy),
                "Enable Custom Strategy",
                "--enable_custom_strategy",
            )
        else:
            table.add_row(
                "Enable Custom Strategy",
                str(self.enable_custom_strategy),
                "Enable Custom Strategy",
                "--enable_custom_strategy",
                style="grey62",
            )

        table.add_row("", "", "")

        if self.disablelog is False:
            table.add_row(
                "Enable Log",
                str(not self.disablelog),
                "Enable Log File",
                "--disablelog",
            )
        else:
            table.add_row(
                "Enable Log",
                str(not self.disablelog),
                "Enable Log File",
                "--disablelog",
                style="grey62",
            )

        if self.disabletracker is False:
            table.add_row(
                "Enable Tracker",
                str(not self.disabletracker),
                "Enable Trade Reporting",
                "--disabletracker",
            )
        else:
            table.add_row(
                "Enable Tracker",
                str(not self.disabletracker),
                "Enable Trade Reporting",
                "--disabletracker",
                style="grey62",
            )

        if self.autorestart is True:
            table.add_row(
                "Auto Restart Bot",
                str(self.autorestart),
                "Auto restart bot on failure",
                "--autorestart",
            )
        else:
            table.add_row(
                "Auto Restart Bot",
                str(self.autorestart),
                "Auto restart bot on failure",
                "--autorestart",
                style="grey62",
            )

        if self.websocket is True:
            table.add_row(
                "Enable Websocket",
                str(self.websocket),
                "Enable websockets for data retrieval",
                "--websocket",
            )
        else:
            table.add_row(
                "Enable Websocket",
                str(self.websocket),
                "Enable websockets for data retrieval",
                "--websocket",
                style="grey62",
            )

        if self.enableinsufficientfundslogging is True:
            table.add_row(
                "Insufficient Funds Log",
                str(self.enableinsufficientfundslogging),
                "Enable insufficient funds logging",
                "--enableinsufficientfundslogging",
            )
        else:
            table.add_row(
                "Insufficient Funds Log",
                str(self.enableinsufficientfundslogging),
                "Enable insufficient funds logging",
                "--enableinsufficientfundslogging",
                style="grey62",
            )

        if self.logbuysellinjson is True:
            table.add_row(
                "JSON Log Trades",
                str(self.logbuysellinjson),
                "Log buy and sell orders in a JSON file",
                "--logbuysellinjson",
            )
        else:
            table.add_row(
                "JSON Log Trades",
                str(self.logbuysellinjson),
                "Log buy and sell orders in a JSON file",
                "--logbuysellinjson",
                style="grey62",
            )

        if self.manual_trades_only is True:
            table.add_row(
                "Manual Trading Only",
                str(self.manual_trades_only),
                "Manual Trading Only (HODL)",
                "--manual_trades_only",
            )
        else:
            table.add_row(
                "Manual Trading Only",
                str(self.manual_trades_only),
                "Manual Trading Only (HODL)",
                "--manual_trades_only",
                style="grey62",
            )

        table.add_row("", "", "")

        if self.buyminsize:
            table.add_row(
                "Buy Min Size",
                str(self.buyminsize),
                "Minimum buy order size in quote currency",
                "--buyminsize",
            )
        else:
            table.add_row(
                "Buy Min Size",
                str(self.buyminsize),
                "Minimum buy order size in quote currency",
                "--buyminsize",
                style="grey62",
            )

        if self.buymaxsize is not None:
            table.add_row(
                "Buy Max Size",
                str(self.buymaxsize),
                "Maximum buy order size in quote currency",
                "--buymaxsize",
            )
        else:
            table.add_row(
                "Buy Max Size",
                str(self.buymaxsize),
                "Maximum buy order size in quote currency",
                "--buymaxsize",
                style="grey62",
            )

        if self.buylastsellsize is True:
            table.add_row(
                "Buy Last Sell Size",
                str(self.buylastsellsize),
                "Next buy order will match last sell order",
                "--buylastsellsize",
            )
        else:
            table.add_row(
                "Buy Last Sell Size",
                str(self.buylastsellsize),
                "Next buy order will match last sell order",
                "--buylastsellsize",
                style="grey62",
            )

        if self.trailingbuypcnt:
            table.add_row(
                "Trailing Buy Percent",
                str(self.trailingbuypcnt),
                "Please refer to the detailed explanation in the README.md",
                "--trailingbuypcnt",
            )
        else:
            table.add_row(
                "Trailing Buy Percent",
                str(self.trailingbuypcnt),
                "Please refer to the detailed explanation in the README.md",
                "--trailingbuypcnt",
                style="grey62",
            )

        if self.trailingimmediatebuy is True:
            table.add_row(
                "Immediate Trailing Buy",
                str(self.trailingimmediatebuy),
                "Please refer to the detailed explanation in the README.md",
                "--trailingimmediatebuy",
            )
        else:
            table.add_row(
                "Immediate Trailing Buy",
                str(self.trailingimmediatebuy),
                "Please refer to the detailed explanation in the README.md",
                "--trailingimmediatebuy",
                style="grey62",
            )

        if self.trailingbuyimmediatepcnt is not None:
            table.add_row(
                "Immediate Trailing Buy Percent",
                str(self.trailingbuyimmediatepcnt),
                "Please refer to the detailed explanation in the README.md",
                "--trailingbuyimmediatepcnt",
            )
        else:
            table.add_row(
                "Immediate Trailing Buy Percent",
                str(self.trailingbuyimmediatepcnt),
                "Please refer to the detailed explanation in the README.md",
                "--trailingbuyimmediatepcnt",
                style="grey62",
            )

        if self.marketmultibuycheck is True:
            table.add_row(
                "Multiple Buy Check",
                str(self.marketmultibuycheck),
                "Please refer to the detailed explanation in the README.md",
                "--marketmultibuycheck",
            )
        else:
            table.add_row(
                "Multiple Buy Check",
                str(self.marketmultibuycheck),
                "Please refer to the detailed explanation in the README.md",
                "--marketmultibuycheck",
                style="grey62",
            )

        table.add_row("", "", "")

        if self.sell_upper_pcnt is not None:
            table.add_row(
                "Sell Upper Percent",
                str(self.sell_upper_pcnt),
                "Upper trade margin to sell at",
                "--sellupperpcnt",
            )
        else:
            table.add_row(
                "Sell Upper Percent",
                str(self.sell_upper_pcnt),
                "Upper trade margin to sell at",
                "--sellupperpcnt",
                style="grey62",
            )

        if self.sell_lower_pcnt is not None:
            table.add_row(
                "Sell Upper Percent",
                str(self.sell_lower_pcnt),
                "Lower trade margin to force sell at",
                "--selllowerpcnt",
            )
        else:
            table.add_row(
                "Sell Lower Percent",
                str(self.sell_lower_pcnt),
                "Lower trade margin to force sell at",
                "--selllowerpcnt",
                style="grey62",
            )

        if self.nosellmaxpcnt is not None:
            table.add_row(
                "No Sell Max",
                str(self.nosellmaxpcnt),
                "Do not sell while trade margin is below this level",
                "--nosellmaxpcnt",
            )
        else:
            table.add_row(
                "No Sell Max",
                str(self.nosellmaxpcnt),
                "Do not sell while trade margin is below this level",
                "--nosellmaxpcnt",
                style="grey62",
            )

        if self.nosellminpcnt is not None:
            table.add_row(
                "No Sell Min",
                str(self.nosellminpcnt),
                "Do not sell while trade margin is above this level",
                "--nosellminpcnt",
            )
        else:
            table.add_row(
                "No Sell Min",
                str(self.nosellminpcnt),
                "Do not sell while trade margin is above this level",
                "--nosellminpcnt",
                style="grey62",
            )

        table.add_row("", "", "")

        if self.trailing_stop_loss is not None:
            table.add_row(
                "Trailing Stop Loss",
                str(self.trailing_stop_loss),
                "Percentage below the trade margin high to sell at",
                "--trailing_stop_loss",
            )
        else:
            table.add_row(
                "Trailing Stop Loss",
                str(self.trailing_stop_loss),
                "Percentage below the trade margin high to sell at",
                "--trailing_stop_loss",
                style="grey62",
            )

        if self.trailing_stop_loss is not None and self.trailing_stop_loss_trigger != 0:
            table.add_row(
                "Trailing Stop Loss Trigger",
                str(self.trailing_stop_loss_trigger),
                "Trade margin percentage to enable the trailing stop loss",
                "--trailingstoplosstrigger",
            )
        else:
            table.add_row(
                "Trailing Stop Loss Trigger",
                str(self.trailing_stop_loss_trigger),
                "Trade margin percentage to enable the trailing stop loss",
                "--trailingstoplosstrigger",
                style="grey62",
            )

        if self.trailingsellpcnt:
            table.add_row(
                "Trailing Sell Percent",
                str(self.trailingsellpcnt),
                "Please refer to the detailed explanation in the README.md",
                "--trailingsellpcnt",
            )
        else:
            table.add_row(
                "Trailing Sell Percent",
                str(self.trailingsellpcnt),
                "Please refer to the detailed explanation in the README.md",
                "--trailingsellpcnt",
                style="grey62",
            )

        if self.trailingimmediatesell is True:
            table.add_row(
                "Immediate Trailing Sell",
                str(self.trailingimmediatesell),
                "Please refer to the detailed explanation in the README.md",
                "--trailingimmediatesell",
            )
        else:
            table.add_row(
                "Immediate Trailing Sell",
                str(self.trailingimmediatesell),
                "Please refer to the detailed explanation in the README.md",
                "--trailingimmediatesell",
                style="grey62",
            )

        if self.trailingsellimmediatepcnt is not None:
            table.add_row(
                "Immediate Trailing Sell Percent",
                str(self.trailingsellimmediatepcnt),
                "Please refer to the detailed explanation in the README.md",
                "--trailingsellimmediatepcnt",
            )
        else:
            table.add_row(
                "Immediate Trailing Sell Percent",
                str(self.trailingsellimmediatepcnt),
                "Please refer to the detailed explanation in the README.md",
                "--trailingsellimmediatepcnt",
                style="grey62",
            )

        if self.trailingsellbailoutpcnt is not None:
            table.add_row(
                "Trailing Sell Bailout Percent",
                str(self.trailingsellbailoutpcnt),
                "Please refer to the detailed explanation in the README.md",
                "--trailingsellbailoutpcnt",
            )
        else:
            table.add_row(
                "Trailing Sell Bailout Percent",
                str(self.trailingsellbailoutpcnt),
                "Please refer to the detailed explanation in the README.md",
                "--trailingsellbailoutpcnt",
                style="grey62",
            )

        table.add_row("", "", "")

        if self.dynamic_tsl is not False:
            table.add_row(
                "Dynamic Trailing Stop Loss",
                str(self.dynamic_tsl),
                "Please refer to the detailed explanation in the README.md",
                "--dynamictsl",
            )
        else:
            table.add_row(
                "Dynamic Trailing Stop Loss",
                str(self.dynamic_tsl),
                "Please refer to the detailed explanation in the README.md",
                "--dynamictsl",
                style="grey62",
            )

        if self.dynamic_tsl is True and self.tsl_multiplier > 0:
            table.add_row(
                "Trailing Stop Loss Multiplier",
                str(self.tsl_multiplier),
                "Please refer to the detailed explanation in the README.md",
                "--tslmultiplier",
            )
        else:
            table.add_row(
                "Trailing Stop Loss Multiplier",
                str(self.tsl_multiplier),
                "Please refer to the detailed explanation in the README.md",
                "--tslmultiplier",
                style="grey62",
            )

        if self.dynamic_tsl is True and self.tsl_trigger_multiplier > 0:
            table.add_row(
                "Stop Loss Trigger Multiplier",
                str(self.tsl_trigger_multiplier),
                "Please refer to the detailed explanation in the README.md",
                "--tsltriggermultiplier",
            )
        else:
            table.add_row(
                "Stop Loss Trigger Multiplier",
                str(self.tsl_trigger_multiplier),
                "Please refer to the detailed explanation in the README.md",
                "--tsltriggermultiplier",
                style="grey62",
            )

        if self.dynamic_tsl is True and self.tsl_max_pcnt > 0:
            table.add_row(
                "Stop Loss Trigger Multiplier",
                str(self.tsl_max_pcnt),
                "Please refer to the detailed explanation in the README.md",
                "--tslmaxpcnt",
            )
        else:
            table.add_row(
                "Stop Loss Trigger Multiplier",
                str(self.tsl_max_pcnt),
                "Please refer to the detailed explanation in the README.md",
                "--tslmaxpcnt",
                style="grey62",
            )

        table.add_row("", "", "")

        if self.preventloss is True:
            table.add_row(
                "Prevent Loss",
                str(self.preventloss),
                "Force a sell before margin is negative",
                "--preventloss",
            )
        else:
            table.add_row(
                "Prevent Loss",
                str(self.preventloss),
                "Force a sell before margin is negative",
                "--preventloss",
                style="grey62",
            )

        if self.preventloss is True and self.preventlosstrigger is not None:
            table.add_row(
                "Prevent Loss Trigger",
                str(self.preventlosstrigger),
                "Margin set point that will trigge the prevent loss",
                "--preventlosstrigger",
            )
        else:
            table.add_row(
                "Prevent Loss Trigger",
                str(self.preventlosstrigger),
                "Margin set point that will trigge the prevent loss",
                "--preventlosstrigger",
                style="grey62",
            )

        if self.preventloss is True and self.preventlossmargin is not None:
            table.add_row(
                "Prevent Loss Margin",
                str(self.preventlossmargin),
                "Margin set point that will cause an immediate sell to prevent loss",
                "--preventlossmargin",
            )
        else:
            table.add_row(
                "Prevent Loss Margin",
                str(self.preventlossmargin),
                "Margin set point that will cause an immediate sell to prevent loss",
                "--preventlossmargin",
                style="grey62",
            )

        table.add_row("", "", "")

        if self.sell_at_loss is True:
            table.add_row(
                "Sell At Loss",
                str(self.sell_at_loss),
                "The bot will be able to sell at a loss",
                "--sellatloss",
            )
        else:
            table.add_row(
                "Sell At Loss",
                str(self.sell_at_loss),
                "The bot will be able to sell at a loss",
                "--sellatloss",
                style="grey62",
            )

        if self.sellatresistance is True:
            table.add_row(
                "Sell At Resistance",
                str(self.sellatresistance),
                "Trigger a sell if the price hits a resistance level",
                "--sellatresistance",
            )
        else:
            table.add_row(
                "Sell At Resistance",
                str(self.sellatresistance),
                "Trigger a sell if the price hits a resistance level",
                "--sellatresistance",
                style="grey62",
            )

        if self.disablefailsafefibonaccilow is False:
            table.add_row(
                "Sell Fibonacci Low",
                str(not self.disablefailsafefibonaccilow),
                "Trigger a sell if the price hits a fibonacci lower level",
                "--disablefailsafefibonaccilow",
            )
        else:
            table.add_row(
                "Sell Fibonacci Low",
                str(not self.disablefailsafefibonaccilow),
                "Trigger a sell if the price hits a fibonacci lower level",
                "--disablefailsafefibonaccilow",
                style="grey62",
            )

        if self.sellatresistance is True:
            table.add_row(
                "Trade Bull Only",
                str(not self.disablebullonly),
                "Only trade in a bull market SMA50 > SMA200",
                "--disablebullonly",
            )
        else:
            table.add_row(
                "Trade Bull Only",
                str(not self.disablebullonly),
                "Only trade in a bull market SMA50 > SMA200",
                "--disablebullonly",
                style="grey62",
            )

        if self.disableprofitbankreversal is False:
            table.add_row(
                "Candlestick Reversal",
                str(not self.disableprofitbankreversal),
                "Trigger a sell at candlestick strong reversal pattern",
                "--disableprofitbankreversal",
            )
        else:
            table.add_row(
                "Candlestick Reversal",
                str(not self.disableprofitbankreversal),
                "Trigger a sell at candlestick strong reversal pattern",
                "--disableprofitbankreversal",
                style="grey62",
            )

        table.add_row("", "", "")

        if self.disablebuynearhigh:
            table.add_row(
                "Allow Buy Near High",
                str(not self.disablebuynearhigh),
                "Prevent the bot from buying at a recent high",
                "--disablebuynearhigh",
            )
        else:
            table.add_row(
                "Allow Buy Near High",
                str(not self.disablebuynearhigh),
                "Prevent the bot from buying at a recent high",
                "--disablebuynearhigh",
                style="grey62",
            )

        if self.disablebuynearhigh and self.nobuynearhighpcnt:
            table.add_row(
                "No Buy Near High Percent",
                str(self.nobuynearhighpcnt),
                "Prevent the bot from buying near a recent high",
                "--nobuynearhighpcnt",
            )
        else:
            table.add_row(
                "No Buy Near High Percent",
                str(self.nobuynearhighpcnt),
                "Prevent the bot from buying near a recent high",
                "--nobuynearhighpcnt",
                style="grey62",
            )

        if self.adjust_total_periods != 300:
            table.add_row(
                "Adjust Total Periods",
                str(self.adjust_total_periods),
                "Adjust data points in historical trading data",
                "--adjust_total_periods",
            )
        else:
            table.add_row(
                "Adjust Total Periods",
                str(self.adjust_total_periods),
                "Adjust data points in historical trading data",
                "--adjust_total_periods",
                style="grey62",
            )

        table.add_row("", "", "")

        if self.sell_trigger_override:
            table.add_row(
                "Override Sell Trigger",
                str(self.sell_trigger_override),
                "Override sell trigger if strong buy",
                "--sell_trigger_override",
            )
        else:
            table.add_row(
                "Override Sell Trigger",
                str(self.sell_trigger_override),
                "Override sell trigger if strong buy",
                "--sell_trigger_override",
                style="grey62",
            )

        table.add_row("", "", "")

        if self.disablebuyema is False:
            table.add_row(
                "Use EMA12/26",
                str(not self.disablebuyema),
                "Exponential Moving Average (EMA)",
                "--disablebuyema",
            )
        else:
            table.add_row(
                "Use EMA12/26",
                str(not self.disablebuyema),
                "Exponential Moving Average (EMA)",
                "--disablebuyema",
                style="grey62",
            )

        if self.disablebuymacd is False:
            table.add_row(
                "Use MACD/Signal",
                str(not self.disablebuymacd),
                "Moving Average Convergence Divergence (MACD)",
                "--disablebuymacd",
            )
        else:
            table.add_row(
                "Use MACD/Signal",
                str(not self.disablebuymacd),
                "Moving Average Convergence Divergence (MACD)",
                "--disablebuymacd",
                style="grey62",
            )

        if self.disablebuyobv is False:
            table.add_row(
                "Use OBV",
                str(not self.disablebuyobv),
                "On-Balance Volume (OBV)",
                "--disablebuyobv",
            )
        else:
            table.add_row(
                "Use OBV",
                str(not self.disablebuyobv),
                "On-Balance Volume (OBV)",
                "--disablebuyobv",
                style="grey62",
            )

        if self.disablebuyelderray is False:
            table.add_row(
                "Use Elder-Ray",
                str(not self.disablebuyelderray),
                "Elder-Ray Index",
                "--disablebuyelderray",
            )
        else:
            table.add_row(
                "Use Elder-Ray",
                str(not self.disablebuyelderray),
                "Elder-Ray Index (Elder-Ray)",
                "--disablebuyelderray",
                style="grey62",
            )

        self.console_term.print(table)
        if self.disablelog is False:
            self.console_log.print(table)

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
                df_data = self.get_additional_df("1h", self.websocket_connection).copy()
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
                df_data = self.get_additional_df("6h", self.websocket_connection).copy()
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
                df_data = self.get_additional_df("1h", self.websocket_connection).copy()
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
                    self.market, self.granularity, self.websocket_connection
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
        if self.is_sim and self.exchange == Exchange.COINBASEPRO:
            return 0.005  # default lowest fee tier
        elif self.is_sim and self.exchange == Exchange.BINANCE:
            return 0.001  # default lowest fee tier
        elif self.is_sim and self.exchange == Exchange.KUCOIN:
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

    def get_buy_percent(self):
        try:
            return int(self.buypercent)
        except Exception:  # pylint: disable=broad-except
            return 100

    def get_sell_percent(self):
        try:
            return int(self.sellpercent)
        except Exception:  # pylint: disable=broad-except
            return 100

    def get_config(self) -> dict:
        try:
            config = json.loads(open(self.config_file, "r", encoding="utf8").read())

            if self.exchange.value in config:
                if "config" in config[self.exchange.value]:
                    return config[self.exchange.value]["config"]
                else:
                    return {}
            else:
                return {}
        except IOError:
            return {}
