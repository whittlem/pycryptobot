import os
import sys
import time
import json
import random
import sched
import signal
import functools
import pandas as pd
import numpy as np
from regex import R
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box
from datetime import datetime, timedelta
from os.path import exists as file_exists
from urllib3.exceptions import ReadTimeoutError

from models.BotConfig import BotConfig
from models.exchange.ExchangesEnum import Exchange
from models.exchange.Granularity import Granularity
from models.exchange.coinbase_pro import WebSocketClient as CWebSocketClient
from models.exchange.coinbase_pro import AuthAPI as CAuthAPI, PublicAPI as CPublicAPI
from models.exchange.kucoin import AuthAPI as KAuthAPI, PublicAPI as KPublicAPI
from models.exchange.kucoin import WebSocketClient as KWebSocketClient
from models.exchange.binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI
from models.exchange.binance import WebSocketClient as BWebSocketClient
from models.exchange.coinbase import AuthAPI as CBAuthAPI
from models.exchange.coinbase import WebSocketClient as CBWebSocketClient
from models.helper.TelegramBotHelper import TelegramBotHelper
from models.helper.MarginHelper import calculate_margin
from models.TradingAccount import TradingAccount
from models.Stats import Stats
from models.AppState import AppState
from models.helper.TextBoxHelper import TextBox
from models.Strategy import Strategy
from views.TradingGraphs import TradingGraphs
from views.PyCryptoBot import RichText
from utils.PyCryptoBot import truncate as _truncate
from utils.PyCryptoBot import compare as _compare

try:
    if file_exists("models/Trading_myPta.py"):
        from models.Trading_myPta import TechnicalAnalysis  # pyright: ignore[reportMissingImports]

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
        super(PyCryptoBot, self).__init__(filename=self.config_file, exchange=exchange)

        self.console_term = Console(no_color=(not self.term_color), width=self.term_width)  # logs to the screen
        self.console_log = Console(file=open(self.logfile, "w"), no_color=True, width=self.log_width)  # logs to file

        self.table_console = Table(title=None, box=None, show_header=False, show_footer=False)

        self.s = sched.scheduler(time.time, time.sleep)

        self.price = 0
        self.takerfee = -1.0
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
        if not self.is_sim and not self.disabletelegram:
            control_status = self.telegram_bot.check_bot_control_status()
            while control_status == "pause" or control_status == "paused":
                if control_status == "pause":
                    RichText.notify("Pausing bot", self, "normal")
                    self.notify_telegram(f"{self.market} bot is paused")
                    self.telegram_bot.update_bot_status("paused")
                    if self.websocket:
                        RichText.notify("Closing websocket...", self, "normal")
                        self.websocket_connection.close()

                time.sleep(30)
                control_status = self.telegram_bot.check_bot_control_status()

            if control_status == "start":
                RichText.notify("Restarting bot", self, "normal")
                self.notify_telegram(f"{self.market} bot has restarted")
                self.telegram_bot.update_bot_status("active")
                self.read_config(self.exchange)
                if self.websocket:
                    RichText.notify("Starting websocket...", self, "normal")
                    self.websocket_connection.start()

            if control_status == "exit":
                RichText.notify("Closing Bot {self.market}", self, "normal")
                self.notify_telegram(f"{self.market} bot is stopping")
                self.telegram_bot.remove_active_bot()
                sys.exit(0)

            if control_status == "reload":
                RichText.notify(f"Reloading config parameters {self.market}", self, "normal")
                self.read_config(self.exchange)
                if self.websocket:
                    self.websocket_connection.close()
                    if self.exchange == Exchange.BINANCE:
                        self.websocket_connection = BWebSocketClient([self.market], self.granularity, app=self)
                    elif self.exchange == Exchange.COINBASE:
                        self.websocket_connection = CBWebSocketClient([self.market], self.granularity, app=self)
                    elif self.exchange == Exchange.COINBASEPRO:
                        self.websocket_connection = CWebSocketClient([self.market], self.granularity, app=self)
                    elif self.exchange == Exchange.KUCOIN:
                        self.websocket_connection = KWebSocketClient([self.market], self.granularity, app=self)
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
                if self.simstartdate is not None:
                    try:
                        self.state.iterations = self.trading_data.index.get_loc(str(self.get_date_from_iso8601_str(self.simstartdate)))
                    except KeyError:
                        RichText.notify("Simulation data is invalid, unable to locate interval using date key.", self, "error")
                        sys.exit(0)

                self.app_started = False

        # reset self.websocket_connection every 23 hours if applicable
        if self.websocket and not self.is_sim:
            if self.websocket_connection.time_elapsed > 82800:
                RichText.notify("Websocket requires a restart every 23 hours!", self, "normal")
                RichText.notify("Stopping websocket...", self, "normal")
                self.websocket_connection.close()
                RichText.notify("Starting websocket...", self, "normal")
                self.websocket_connection.start()
                RichText.notify("Restarting job in 30 seconds...", self, "normal")
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
                self.trading_data = self.get_historical_data(self.market, self.granularity, self.websocket_connection)
                self.state.closed_candle_row = -1
                self.price = float(self.trading_data.iloc[-1, self.trading_data.columns.get_loc("close")])

            else:
                # set time and price with ticker data and add/update current candle
                ticker = self.get_ticker(self.market, self.websocket_connection)
                # if 0, use last close value as self.price
                self.price = self.trading_data["close"].iloc[-1] if ticker[1] == 0 else ticker[1]
                self.ticker_date = ticker[0]
                self.ticker_price = ticker[1]

                if self.state.closed_candle_row == -2:
                    self.trading_data.iloc[-1, self.trading_data.columns.get_loc("low")] = (
                        self.price if self.price < self.trading_data["low"].iloc[-1] else self.trading_data["low"].iloc[-1]
                    )
                    self.trading_data.iloc[-1, self.trading_data.columns.get_loc("high")] = (
                        self.price if self.price > self.trading_data["high"].iloc[-1] else self.trading_data["high"].iloc[-1]
                    )
                    self.trading_data.iloc[-1, self.trading_data.columns.get_loc("close")] = self.price
                    self.trading_data.iloc[-1, self.trading_data.columns.get_loc("date")] = datetime.strptime(ticker[0], "%Y-%m-%d %H:%M:%S")
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
                                (self.price if self.price < self.trading_data["close"].iloc[-1] else self.trading_data["close"].iloc[-1]),
                                (self.price if self.price > self.trading_data["close"].iloc[-1] else self.trading_data["close"].iloc[-1]),
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
                    if self.simstartdate is not None:
                        start_date = self.get_date_from_iso8601_str(self.simstartdate)
                    else:
                        start_date = self.get_date_from_iso8601_str(str(df.head(1).index.format()[0]))

                    if self.simenddate is not None:
                        if self.simenddate == "now":
                            end_date = self.get_date_from_iso8601_str(str(datetime.now()))
                        else:
                            end_date = self.get_date_from_iso8601_str(self.simenddate)
                    else:
                        end_date = self.get_date_from_iso8601_str(str(df.tail(1).index.format()[0]))

                    simDate = self.get_date_from_iso8601_str(str(self.state.last_df_index))

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
                            self.state.iterations = trading_data.index.get_loc(str(simDate)) + 1
                            dateFound = True
                        except Exception:
                            simDate += timedelta(seconds=self.granularity.value[0])

                    if self.get_date_from_iso8601_str(str(simDate)).isoformat() == self.get_date_from_iso8601_str(str(self.state.last_df_index)).isoformat():
                        self.state.iterations += 1

                    if self.state.iterations == 0:
                        self.state.iterations = 1

                    trading_dataCopy = trading_data.copy()
                    _technical_analysis = TechnicalAnalysis(trading_dataCopy, self.adjusttotalperiods, app=self)

                    # if 'bool(self.df_last["morning_star"].values[0])' not in df:
                    _technical_analysis.add_all()

                    df = _technical_analysis.get_df()

                    self.sim_smartswitch = False

            elif self.smart_switch == 1 and _technical_analysis is None:
                trading_dataCopy = trading_data.copy()
                _technical_analysis = TechnicalAnalysis(trading_dataCopy, self.adjusttotalperiods, app=self)

                if "morning_star" not in df:
                    _technical_analysis.add_all()

                df = _technical_analysis.get_df()

        else:
            _technical_analysis = TechnicalAnalysis(self.trading_data, len(self.trading_data), app=self)
            _technical_analysis.add_all()
            df = _technical_analysis.get_df()

        if self.is_sim:
            self.df_last = self.get_interval(df, self.state.iterations)
        else:
            self.df_last = self.get_interval(df)

        # Don't want index of new, unclosed candle, use the historical row setting to set index to last closed candle
        if self.state.closed_candle_row != -2 and len(self.df_last.index.format()) > 0:
            current_df_index = str(self.df_last.index.format()[0])
        else:
            current_df_index = self.state.last_df_index

        formatted_current_df_index = f"{current_df_index} 00:00:00" if len(current_df_index) == 10 else current_df_index

        current_sim_date = formatted_current_df_index

        if self.state.iterations == 2:
            # check if bot has open or closed order
            # update data.json "opentrades"
            if not self.disabletelegram:
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
                RichText.notify(
                    "Open order detected smart switching to 300 (5 min) granularity.",
                    self,
                    "normal",
                )

            if not self.telegramtradesonly:
                self.notify_telegram(self.market + " open order detected smart switching to 300 (5 min) granularity")

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
                RichText.notify(
                    "Sell detected smart switching to 3600 (1 hour) granularity.",
                    self,
                    "normal",
                )
            if not self.telegramtradesonly:
                self.notify_telegram(self.market + " sell detected smart switching to 3600 (1 hour) granularity")
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
                RichText.notify(
                    "Smart switch from granularity 3600 (1 hour) to 900 (15 min).",
                    self,
                    "normal",
                )

            if self.is_sim:
                self.sim_smartswitch = True

            if not self.telegramtradesonly:
                self.notify_telegram(self.market + " smart switch from granularity 3600 (1 hour) to 900 (15 min)")

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
                RichText.notify(
                    "Smart switch from granularity 900 (15 min) to 3600 (1 hour).",
                    self,
                    "normal",
                )

            if self.is_sim:
                self.sim_smartswitch = True

            if not self.telegramtradesonly:
                self.notify_telegram(f"{self.market} smart switch from granularity 900 (15 min) to 3600 (1 hour)")

            self.granularity = Granularity.ONE_HOUR
            list(map(self.s.cancel, self.s.queue))
            self.s.enter(5, 1, self.execute_job, ())

        if self.exchange == Exchange.BINANCE and self.granularity == Granularity.ONE_DAY:
            if len(df) < 250:
                # data frame should have 250 rows, if not retry
                RichText.notify(f"Data frame length is < 250 ({str(len(df))})", self, "error")
                list(map(self.s.cancel, self.s.queue))
                self.s.enter(300, 1, self.execute_job, ())
        else:
            # verify 300 rows - subtract 34% to allow small buffer if API is acting up.
            adjusted_periods = self.adjusttotalperiods - (self.adjusttotalperiods * 0.30)
            if len(df) < adjusted_periods:  # If 300 is required, set adjusttotalperiods in config to 300 * 30%.
                if not self.is_sim:
                    # data frame should have 300 rows or equal to adjusted total rows if set, if not retry
                    RichText.notify(
                        f"error: data frame length is < {str(int(adjusted_periods))} ({str(len(df))})",
                        self,
                        "error",
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
                    RichText.notify(
                        f"Last action change detected from {last_action_current} to {self.state.last_action}.",
                        self,
                        "normal",
                    )

                    if not self.telegramtradesonly:
                        self.notify_telegram(f"{self.market} last_action change detected from {last_action_current} to {self.state.last_action}")

                # this is used to reset variables if error occurred during trade process
                # make sure signals and telegram info is set correctly, close bot if needed on sell
                if self.state.action == "check_action" and self.state.last_action == "BUY":
                    self.state.trade_error_cnt = 0
                    self.state.trailing_buy = False
                    self.state.action = None
                    self.state.trailing_buy_immediate = False

                    if not self.disabletelegram:
                        self.telegram_bot.add_open_order()

                    if not self.ignorepreviousbuy:
                        RichText.notify(f"{self.market} ({self.print_granularity()}) - {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}", self, "warning")
                        RichText.notify("Catching BUY that occurred previously. Updating signal information.", self, "warning")

                        if not self.telegramtradesonly and not self.disabletelegram:
                            self.notify_telegram(
                                self.market
                                + " ("
                                + self.print_granularity()
                                + ") - "
                                + datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                                + "\n"
                                + "Catching BUY that occurred previously. Updating signal information."
                            )

                elif self.state.action == "check_action" and self.state.last_action == "SELL":
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

                    if not self.ignoreprevioussell:
                        RichText.notify(f"{self.market} ({self.print_granularity()}) - {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}", self, "warning")
                        RichText.notify("Catching SELL that occurred previously. Updating signal information.", self, "warning")

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

                    if self.exitaftersell:
                        RichText.notify("Exit after sell! (\"exitaftersell\" is enabled)", self, "warning")
                        sys.exit(0)

            if self.price < 0.000001:
                raise Exception(f"{self.market} is unsuitable for trading, quote self.price is less than 0.000001!")

            try:
                # technical indicators
                ema12gtema26 = bool(self.df_last["ema12gtema26"].values[0])
                ema12gtema26co = bool(self.df_last["ema12gtema26co"].values[0])
                goldencross = bool(self.df_last["goldencross"].values[0])
                macdgtsignal = bool(self.df_last["macdgtsignal"].values[0])
                macdgtsignalco = bool(self.df_last["macdgtsignalco"].values[0])
                ema12ltema26co = bool(self.df_last["ema12ltema26co"].values[0])
                macdltsignalco = bool(self.df_last["macdltsignalco"].values[0])
                obv_pc = float(self.df_last["obv_pc"].values[0])
                elder_ray_buy = bool(self.df_last["eri_buy"].values[0])
                elder_ray_sell = bool(self.df_last["eri_sell"].values[0])
                closegtbb20_upperco = bool(self.df_last["closegtbb20_upperco"].values[0])
                closeltbb20_lowerco = bool(self.df_last["closeltbb20_lowerco"].values[0])

                # if simulation, set goldencross based on actual sim date
                if self.is_sim:
                    if self.adjusttotalperiods < 200:
                        goldencross = False
                    else:
                        goldencross = self.is_1h_sma50200_bull(current_sim_date)

            except KeyError as err:
                RichText.notify(err, self, "error")
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
                sdf = df[df["date"] <= current_sim_date].tail(self.adjusttotalperiods)
                strategy = Strategy(self, self.state, sdf, sdf.index.get_loc(str(current_sim_date)) + 1)
            else:
                strategy = Strategy(self, self.state, df)

            trailing_action_logtext = ""

            # determine current action, indicatorvalues will be empty if custom Strategy are disabled or it's debug is False
            self.state.action, indicatorvalues = strategy.get_action(self.state, self.price, current_sim_date, self.websocket_connection)

            immediate_action = False
            margin, profit, sell_fee, change_pcnt_high = 0, 0, 0, 0

            # Reset the TA so that the last record is the current sim date
            # To allow for calculations to be done on the sim date being processed
            if self.is_sim:
                trading_dataCopy = self.trading_data[self.trading_data["date"] <= current_sim_date].tail(self.adjusttotalperiods).copy()
                _technical_analysis = TechnicalAnalysis(trading_dataCopy, self.adjusttotalperiods, app=self)

            if self.state.last_buy_size > 0 and self.state.last_buy_price > 0 and self.price > 0 and self.state.last_action == "BUY":
                # update last buy high
                if self.price > self.state.last_buy_high:
                    self.state.last_buy_high = self.price

                if self.state.last_buy_high > 0:
                    change_pcnt_high = ((self.price / self.state.last_buy_high) - 1) * 100
                else:
                    change_pcnt_high = 0

                # buy and sell calculations
                self.state.last_buy_fee = round(self.state.last_buy_size * self.get_taker_fee(), 8)
                self.state.last_buy_filled = round(
                    ((self.state.last_buy_size - self.state.last_buy_fee) / self.state.last_buy_price),
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

                        if self.exchange == Exchange.COINBASE or self.exchange == Exchange.COINBASEPRO or self.exchange == Exchange.KUCOIN:
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
                    app=self,
                )

                # handle immediate sell actions
                if self.manual_trades_only is False and strategy.is_sell_trigger(
                    self.state, self.price, _technical_analysis.get_trade_exit(self.price), margin, change_pcnt_high
                ):
                    self.state.action = "SELL"
                    immediate_action = True

            # handle overriding wait actions
            # (e.g. do not sell if sell at loss disabled!, do not buy in bull if bull only, manual trades only)
            if self.manual_trades_only is True or (self.state.action != "WAIT" and strategy.is_wait_trigger(margin, goldencross)):
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

            if not self.is_sim and self.telegrambotcontrol:
                manual_buy_sell = self.telegram_bot.check_manual_buy_sell()
                if not manual_buy_sell == "WAIT":
                    self.state.action = manual_buy_sell
                    immediate_action = True

            # polling is every 5 minutes (even for hourly intervals), but only process once per interval
            if immediate_action is True or self.state.last_df_index != current_df_index:
                precision = 4

                if self.price < 0.01:
                    precision = 8

                # Since precision does not change after this point, it is safe to prepare a tailored `truncate()` that would
                # work with this precision. It should save a couple of `precision` uses, one for each `truncate()` call.
                truncate = functools.partial(_truncate, n=precision)

                def _candlestick(candlestick_status: str = "") -> None:
                    if candlestick_status == "":
                        return

                    self.table_console = Table(title=None, box=None, show_header=False, show_footer=False)
                    self.table_console.add_row(
                        RichText.styled_text("Bot1", "magenta"),
                        RichText.styled_text(formatted_current_df_index, "white"),
                        RichText.styled_text(self.market, "yellow"),
                        RichText.styled_text(self.print_granularity(), "yellow"),
                        RichText.styled_text(candlestick_status, "violet"),
                    )
                    self.console_term.print(self.table_console)
                    if self.disablelog is False:
                        self.console_log.print(self.table_console)
                    self.table_console = Table(title=None, box=None, show_header=False, show_footer=False)  # clear table

                def _notify(notification: str = "", level: str = "normal") -> None:
                    if notification == "":
                        return

                    if level == "warning":
                        color = "dark_orange"
                    elif level == "error":
                        color = "red1"
                    elif level == "critical":
                        color = "red1 blink"
                    elif level == "info":
                        color = "yellow blink"
                    else:
                        color = "violet"

                    self.table_console = Table(title=None, box=None, show_header=False, show_footer=False)
                    self.table_console.add_row(
                        RichText.styled_text("Bot1", "magenta"),
                        RichText.styled_text(formatted_current_df_index, "white"),
                        RichText.styled_text(self.market, "yellow"),
                        RichText.styled_text(self.print_granularity(), "yellow"),
                        RichText.styled_text(notification, color),
                    )
                    self.console_term.print(self.table_console)
                    if self.disablelog is False:
                        self.console_log.print(self.table_console)
                    self.table_console = Table(title=None, box=None, show_header=False, show_footer=False)  # clear table

                if not self.is_sim:
                    df_high = df[df["date"] <= current_sim_date]["close"].max()
                    df_low = df[df["date"] <= current_sim_date]["close"].min()
                    range_start = str(df.iloc[0, 0])
                    range_end = str(df.iloc[len(df) - 1, 0])
                else:
                    df_high = df["close"].max()
                    df_low = df["close"].min()
                    if len(df) > self.adjusttotalperiods:
                        range_start = str(df.iloc[self.state.iterations - self.adjusttotalperiods, 0])  # noqa: F841
                    else:
                        # RichText.notify(f"Trading dataframe length {len(df)} is greater than expected {self.adjusttotalperiods}", self, "warning")
                        range_start = str(df.iloc[self.state.iterations - len(df), 0])  # noqa: F841

                    range_end = str(df.iloc[self.state.iterations - 1, 0])  # noqa: F841

                df_swing = round(((df_high - df_low) / df_low) * 100, 2)
                df_near_high = round(((self.price - df_high) / df_high) * 100, 2)

                if self.state.last_action == "BUY":
                    if self.state.last_buy_size > 0:
                        margin_text = truncate(margin) + "%"
                    else:
                        margin_text = "0%"

                    if self.is_sim:
                        # save margin for summary if open trade
                        self.state.open_trade_margin_float = margin
                        self.state.open_trade_margin = margin_text
                else:
                    margin_text = ""

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
                        RichText.on_balance_volume(
                            self.df_last["obv"].values[0],
                            self.df_last["obv_pc"].values[0],
                            self.disablebuyobv,
                        ),
                        RichText.elder_ray(elder_ray_buy, elder_ray_sell, self.disablebuyelderray),
                        RichText.number_comparison(
                            "BBU:",
                            round(self.df_last["close"].values[0], 2),
                            round(self.df_last["bb20_upper"].values[0], 2),
                            closegtbb20_upperco or closeltbb20_lowerco,
                            self.disablebuybbands_s1,
                        ),
                        RichText.number_comparison(
                            "BBL:",
                            round(self.df_last["bb20_lower"].values[0], 2),
                            round(self.df_last["close"].values[0], 2),
                            closegtbb20_upperco or closeltbb20_lowerco,
                            self.disablebuybbands_s1,
                        ),
                        RichText.action_text(self.state.action),
                        RichText.last_action_text(self.state.last_action),
                        RichText.styled_label_text(
                            "DF-H/L",
                            "white",
                            f"{str(df_high)} / {str(df_low)} ({df_swing}%)",
                            "cyan",
                        ),
                        RichText.styled_label_text("Near-High", "white", f"{df_near_high}%", "cyan"),  # price near high
                        RichText.styled_label_text("Range", "white", f"{range_start} <-> {range_end}", "cyan") if (self.term_width > 120) else None,
                        RichText.margin_text(margin_text, self.state.last_action),
                        RichText.delta_text(
                            self.price,
                            self.state.last_buy_price,
                            precision,
                            self.state.last_action,
                        ),
                    ]
                    if arg
                ]

                if not self.is_sim or (self.is_sim and not self.simresultonly):
                    self.table_console.add_row(*args)
                    self.console_term.print(self.table_console)
                    if self.disablelog is False:
                        self.console_log.print(self.table_console)
                    self.table_console = Table(title=None, box=None, show_header=False, show_footer=False)  # clear table

                    if self.state.last_action == "BUY":
                        # display support, resistance and fibonacci levels
                        if not self.is_sim:
                            _notify(_technical_analysis.print_support_resistance_fibonacci_levels(self.price))

                # if a buy signal
                if self.state.action == "BUY":
                    self.state.last_buy_price = self.price
                    self.state.last_buy_high = self.state.last_buy_price

                    # if live
                    if self.is_live:
                        self.insufficientfunds = False

                        try:
                            self.account.quote_balance_before = self.account.get_balance(self.quote_currency)
                            self.state.last_buy_size = float(self.account.quote_balance_before)

                            if self.buymaxsize and self.buylastsellsize and self.state.minimum_order_quote(quote=self.state.last_sell_size, balancechk=True):
                                self.state.last_buy_size = self.state.last_sell_size
                            elif self.buymaxsize and self.state.last_buy_size > self.buymaxsize:
                                self.state.last_buy_size = self.buymaxsize

                            if self.account.quote_balance_before < self.state.last_buy_size:
                                self.insufficientfunds = True
                        except Exception:
                            pass

                        if not self.insufficientfunds and self.buyminsize < self.account.quote_balance_before:
                            if not self.is_live:
                                if not self.is_sim or (self.is_sim and not self.simresultonly):
                                    _notify(f"*** Executing SIMULATION Buy Order at {str(self.price)} ***", "info")
                            else:
                                _notify("*** Executing LIVE Buy Order ***", "info")

                            # display balances
                            _notify(f"{self.base_currency} balance before order: {str(self.account.base_balance_before)}", "debug")
                            _notify(f"{self.quote_currency} balance before order: {str(self.account.quote_balance_before)}", "debug")

                            # place the buy order
                            resp_error = 0

                            try:
                                self.market_buy(
                                    self.market,
                                    self.state.last_buy_size,
                                    self.get_buy_percent(),
                                )

                            except Exception as err:
                                _notify(f"Trade Error: {err}", "error")
                                resp_error = 1

                            if resp_error == 0:
                                self.account.base_balance_after = 0
                                self.account.quote_balance_after = 0
                                try:
                                    ac = self.account.get_balance()
                                    df_base = ac[ac["currency"] == self.base_currency]["available"]
                                    self.account.base_balance_after = 0.0 if len(df_base) == 0 else float(df_base.values[0])
                                    df_quote = ac[ac["currency"] == self.quote_currency]["available"]

                                    self.account.quote_balance_after = 0.0 if len(df_quote) == 0 else float(df_quote.values[0])
                                    bal_error = 0
                                except Exception as err:
                                    bal_error = 1
                                    _notify(
                                        f"Error: Balance not retrieved after trade for {self.market}",
                                        "warning",
                                    )
                                    _notify(f"API Error Msg: {err}", "warning")

                                if bal_error == 0:
                                    self.state.trade_error_cnt = 0
                                    self.state.trailing_buy = False
                                    self.state.last_action = "BUY"
                                    self.state.action = "DONE"
                                    self.state.trailing_buy_immediate = False
                                    self.telegram_bot.add_open_order()

                                    if not self.disabletelegram:
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
                                    _notify(f"{self.market} - Error occurred while checking balance after BUY. Last transaction check will happen shortly.")

                                    if not self.disabletelegramerrormsgs:
                                        self.notify_telegram(
                                            self.market + " - Error occurred while checking balance after BUY. Last transaction check will happen shortly."
                                        )

                            else:  # there was a response error
                                # only attempt BUY 3 times before exception to prevent continuous loop
                                self.state.trade_error_cnt += 1
                                if self.state.trade_error_cnt >= 2:  # 3 attempts made
                                    raise Exception("Trade Error: BUY transaction attempted 3 times. Check log for errors")

                                # set variable to trigger to check trade on next iteration
                                self.state.action = "check_action"
                                self.state.last_action = None

                                _notify(
                                    f"API Error: Unable to place buy order for {self.market}.",
                                    "warning",
                                )

                                if not self.disabletelegramerrormsgs:
                                    self.notify_telegram(f"API Error: Unable to place buy order for {self.market}")

                                time.sleep(30)

                        else:
                            if not self.is_live:
                                if not self.is_sim or (self.is_sim and not self.simresultonly):
                                    _notify(f"*** Skipping SIMULATION Buy Order at {str(self.price)} -- Insufficient Funds ***", "warning")
                            else:
                                _notify("*** Skipping LIVE Buy Order -- Insufficient Funds ***", "warning")

                        self.state.last_api_call_datetime -= timedelta(seconds=60)

                    # if not live
                    else:
                        if self.state.last_buy_size == 0 and self.state.last_buy_filled == 0:
                            # sim mode can now use buymaxsize as the amount used for a buy
                            if self.buymaxsize > 0:
                                self.state.last_buy_size = self.buymaxsize
                                self.state.first_buy_size = self.buymaxsize
                            else:
                                # TODO: calculate correct buy amount based on quote currency balance
                                self.state.last_buy_size = 1
                                self.state.first_buy_size = 1
                        # add option for buy last sell size
                        elif (
                            self.buymaxsize > 0
                            and self.buylastsellsize
                            and self.state.last_sell_size > self.state.minimum_order_quote(quote=self.state.last_sell_size, balancechk=True)
                        ):
                            self.state.last_buy_size = self.state.last_sell_size

                        self.state.buy_count = self.state.buy_count + 1
                        self.state.buy_sum = self.state.buy_sum + self.state.last_buy_size
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

                        if not self.is_sim or (self.is_sim and not self.simresultonly):
                            _notify(f"*** Executing SIMULATION Buy Order at {str(self.price)} ***", "info")

                        bands = _technical_analysis.get_fibonacci_retracement_levels(float(self.price))

                        if not self.is_sim:
                            _notify(f"Fibonacci Retracement Levels: {str(bands)}")
                            _technical_analysis.print_support_resistance_levels_v2()

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
                                        "Base": float(self.state.last_buy_size) / float(self.price),
                                        "DF_High": df[df["date"] <= current_sim_date]["close"].max(),
                                        "DF_Low": df[df["date"] <= current_sim_date]["close"].min(),
                                    },
                                    index=[0],
                                ),
                            ],
                        )

                        self.state.in_open_trade = True
                        self.state.last_action = "BUY"
                        self.state.last_api_call_datetime -= timedelta(seconds=60)

                    if self.save_graphs:
                        if self.adjusttotalperiods < 200:
                            _notify("Trading Graphs can only be generated when dataframe has more than 200 periods.")
                        else:
                            tradinggraphs = TradingGraphs(_technical_analysis, self)
                            ts = datetime.now().timestamp()
                            filename = f"{self.market}_{self.print_granularity()}_buy_{str(ts)}.png"
                            # This allows graphs to be used in sim mode using the correct DF
                            if self.is_sim:
                                tradinggraphs.render_ema_and_macd(len(trading_dataCopy), "graphs/" + filename, True)
                            else:
                                tradinggraphs.render_ema_and_macd(len(self.trading_data), "graphs/" + filename, True)

                # if a sell signal
                elif self.state.action == "SELL":
                    # if live
                    if self.is_live:
                        if not self.is_live:
                            if not self.is_sim or (self.is_sim and not self.simresultonly):
                                _notify(f"*** Executing SIMULATION Sell Order at {str(self.price)} ***", "info")
                        else:
                            _notify("*** Executing LIVE Sell Order ***", "info")

                        # check balances before and display
                        self.account.base_balance_before = 0
                        self.account.quote_balance_before = 0
                        try:
                            self.account.base_balance_before = float(self.account.get_balance(self.base_currency))
                            self.account.quote_balance_before = float(self.account.get_balance(self.quote_currency))
                        except Exception:
                            pass

                        _notify(f"{self.base_currency} balance before order: {str(self.account.base_balance_before)}", "debug")
                        _notify(f"{self.quote_currency} balance before order: {str(self.account.quote_balance_before)}", "debug")

                        # execute a live market sell
                        baseamounttosell = float(self.account.base_balance_before) if self.sellfullbaseamount is True else float(self.state.last_buy_filled)

                        self.account.base_balance_after = 0
                        self.account.quote_balance_after = 0

                        # place the sell order
                        resp_error = 0

                        try:
                            self.market_sell(
                                self.market,
                                baseamounttosell,
                                self.get_sell_percent(),
                            )
                        except Exception as err:
                            _notify(f"Trade Error: {err}", "warning")
                            resp_error = 1

                        if resp_error == 0:
                            try:
                                self.account.base_balance_after = float(self.account.get_balance(self.base_currency))
                                self.account.quote_balance_after = float(self.account.get_balance(self.quote_currency))
                                bal_error = 0
                            except Exception as err:
                                bal_error = 1
                                _notify(
                                    f"Error: Balance not retrieved after trade for {self.market}.",
                                    "warning",
                                )
                                _notify(f"API Error Msg: {err}", "warning")

                            if bal_error == 0:
                                _notify(f"{self.base_currency} balance after order: {str(self.account.base_balance_after)}")
                                _notify(f"{self.quote_currency} balance after order: {str(self.account.quote_balance_after)}")

                                self.state.prevent_loss = False
                                self.state.trailing_sell = False
                                self.state.trailing_sell_immediate = False
                                self.state.tsl_triggered = False
                                self.state.tsl_pcnt = float(self.trailing_stop_loss)
                                self.state.tsl_trigger = float(self.trailing_stop_loss_trigger)
                                self.state.tsl_max = False
                                self.state.trade_error_cnt = 0
                                self.state.last_action = "SELL"
                                self.state.action = "DONE"

                                if not self.disabletelegram:
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
                                    str(self.get_date_from_iso8601_str(str(datetime.now()))),
                                    str(self.price),
                                    margin_text,
                                )

                                if self.exitaftersell and self.startmethod not in ("telegram"):
                                    RichText.notify("Exit after sell! (\"exitaftersell\" is enabled)", self, "warning")
                                    sys.exit(0)

                            else:
                                # set variable to trigger to check trade on next iteration
                                self.state.action = "check_action"

                                _notify(
                                    f"{self.market} - Error occurred while checking balance after SELL. Last transaction check will happen shortly.",
                                    "error",
                                )

                                if not self.disabletelegramerrormsgs:
                                    self.notify_telegram(
                                        self.market + " - Error occurred while checking balance after SELL. Last transaction check will happen shortly."
                                    )

                        else:  # there was an error
                            # only attempt SELL 3 times before exception to prevent continuous loop
                            self.state.trade_error_cnt += 1
                            if self.state.trade_error_cnt >= 2:  # 3 attempts made
                                raise Exception("Trade Error: SELL transaction attempted 3 times. Check log for errors.")
                            # set variable to trigger to check trade on next iteration
                            self.state.action = "check_action"
                            self.state.last_action = None

                            _notify(
                                f"API Error: Unable to place SELL order for {self.market}.",
                                "warning",
                            )

                            if not self.disabletelegramerrormsgs:
                                self.notify_telegram(f"API Error: Unable to place SELL order for {self.market}")
                            time.sleep(30)

                        self.state.last_api_call_datetime -= timedelta(seconds=60)

                    # if not live
                    else:
                        # TODO - improve and confirm logic to simulate sell

                        margin, profit, sell_fee = calculate_margin(
                            buy_size=self.state.last_buy_size,
                            buy_filled=self.state.last_buy_filled,
                            buy_price=self.state.last_buy_price,
                            buy_fee=self.state.last_buy_fee,
                            sell_percent=self.get_sell_percent(),
                            sell_price=self.price,
                            sell_taker_fee=self.get_taker_fee(),
                            app=self,
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
                            (self.price / self.state.last_buy_price) * (self.state.last_buy_size - self.state.last_buy_fee)
                        )
                        self.state.last_sell_size = sell_size - sell_fee
                        self.state.sell_sum = self.state.sell_sum + self.state.last_sell_size

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

                        if self.price > 0:
                            margin_text = truncate(margin) + "%"
                        else:
                            margin_text = "0%"

                        if not self.is_sim or (self.is_sim and not self.simresultonly):
                            _notify(
                                f"*** Executing SIMULATION Sell Order at {str(self.price)} | Buy: {str(self.state.last_buy_price)} ({str(self.price - self.state.last_buy_price)}) | Profit: {str(profit)} on {_truncate(self.state.last_buy_size, precision)} | Fees: {str(round(sell_fee, precision))} | Margin: {margin_text} ***",
                                "info",
                            )

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
                                        "DF_High": df[df["date"] <= current_sim_date]["close"].max(),
                                        "DF_Low": df[df["date"] <= current_sim_date]["close"].min(),
                                    },
                                    index=[0],
                                ),
                            ],
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
                            self.state.tsl_trigger = float(self.trailing_stop_loss_trigger)

                        # adjust the next simulation buy with the current balance
                        self.state.last_buy_size += profit

                        self.state.tsl_max = False
                        self.state.action = "DONE"

                    if self.save_graphs:
                        tradinggraphs = TradingGraphs(_technical_analysis, self)
                        ts = datetime.now().timestamp()
                        filename = f"{self.market}_{self.print_granularity()}_sell_{str(ts)}.png"
                        # This allows graphs to be used in sim mode using the correct DF
                        if self.is_sim:
                            tradinggraphs.render_ema_and_macd(len(trading_dataCopy), "graphs/" + filename, True)
                        else:
                            tradinggraphs.render_ema_and_macd(len(trading_data), "graphs/" + filename, True)

                    if self.exitaftersell:
                        RichText.notify("Exit after sell! (\"exitaftersell\" is enabled)", self, "warning")
                        sys.exit(0)

            self.state.last_df_index = str(self.df_last.index.format()[0])

            if self.logbuysellinjson is True and self.state.action == "DONE" and len(self.trade_tracker) > 0:
                _notify(self.trade_tracker.loc[len(self.trade_tracker) - 1].to_json())

            if self.state.action == "DONE" and indicatorvalues != "" and not self.disabletelegram:
                self.notify_telegram(indicatorvalues)

            # summary at the end of the simulation
            if self.is_sim and self.state.iterations == len(df):
                self._simulation_summary()
                self._simulation_save_orders()

        if self.state.last_buy_size <= 0 and self.state.last_buy_price <= 0 and self.state.last_action != "BUY":
            self.telegram_bot.add_info(
                f'Current price: {str(self.price)}{trailing_action_logtext} | {str(round(((self.price-df["close"].max()) / df["close"].max())*100, 2))}% from DF HIGH',
                round(self.price, 4),
                str(round(df["close"].max(), 4)),
                str(
                    round(
                        ((self.price - df["close"].max()) / df["close"].max()) * 100,
                        2,
                    )
                )
                + "%",
                self.state.action,
            )

        if self.state.last_action == "BUY" and self.state.in_open_trade and last_api_call_datetime.seconds > 60:
            # update margin for telegram bot
            self.telegram_bot.add_margin(
                str(_truncate(margin, 4) + "%") if self.state.in_open_trade is True else " ",
                str(_truncate(profit, 2)) if self.state.in_open_trade is True else " ",
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
                self.account.save_tracker_csv(self.market)
            elif self.exchange == Exchange.COINBASE or self.exchange == Exchange.COINBASEPRO or self.exchange == Exchange.KUCOIN:
                self.account.save_tracker_csv()

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
                and (isinstance(self.websocket_connection.tickers, pd.DataFrame) and len(self.websocket_connection.tickers) == 1)
                and (isinstance(self.websocket_connection.candles, pd.DataFrame) and len(self.websocket_connection.candles) == self.adjusttotalperiods)
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
            if self.exchange == Exchange.COINBASE:
                message += "Coinbase bot"
                if self.websocket and not self.is_sim:
                    RichText.notify("Opening websocket to Coinbase", self, "normal")
                    print("")
                    self.websocket_connection = CWebSocketClient([self.market], self.granularity, app=self)
                    self.websocket_connection.start()
            elif self.exchange == Exchange.COINBASEPRO:
                message += "Coinbase Pro bot"
                if self.websocket and not self.is_sim:
                    RichText.notify("Opening websocket to Coinbase Pro", self, "normal")
                    print("")
                    self.websocket_connection = CWebSocketClient([self.market], self.granularity, app=self)
                    self.websocket_connection.start()
            elif self.exchange == Exchange.BINANCE:
                message += "Binance bot"
                if self.websocket and not self.is_sim:
                    RichText.notify("Opening websocket to Binance", self, "normal")
                    print("")
                    self.websocket_connection = BWebSocketClient([self.market], self.granularity, app=self)
                    self.websocket_connection.start()
            elif self.exchange == Exchange.KUCOIN:
                message += "Kucoin bot"
                if self.websocket and not self.is_sim:
                    RichText.notify("Opening websocket to Kucoin", self, "normal")
                    print("")
                    self.websocket_connection = KWebSocketClient([self.market], self.granularit, app=self)
                    self.websocket_connection.start()

            smartswitchstatus = "enabled" if self.smart_switch else "disabled"
            message += f" for {self.market} using granularity {self.print_granularity()}. Smartswitch {smartswitchstatus}"

            if self.startmethod in ("standard", "telegram") and not self.disabletelegram:
                self.notify_telegram(message)

            # initialise and start application
            self.initialise()

            if self.is_sim and self.simenddate:
                try:
                    # if simenddate is set, then remove trailing data points
                    self.trading_data = self.trading_data[self.trading_data["date"] <= self.simenddate]
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
                    seconds = 30
                    RichText.notify(f"Restarting application in {seconds} seconds after exception: {repr(e)}", self, "critical")
                    time.sleep(seconds)

                    if not self.disabletelegram:
                        self.notify_telegram(f"Auto restarting bot for {self.market} after exception: {repr(e)}")

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
                RichText.notify("Shutting down bot...", self, "warning")
                RichText.notify("Please wait while threads complete gracefully....", self, "warning")
            # else:
            # RichText.notify("Shutting down bot...", self, "warning")
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
                self.notify_telegram(f"Bot for {self.market} got an exception: {repr(e)}")
                try:
                    self.telegram_bot.remove_active_bot()
                except Exception:
                    pass
            RichText.notify(repr(e), self, "critical")
            # pylint: disable=protected-access
            os._exit(0)
            # raise

    def market_buy(self, market, quote_currency, buy_percent=100):
        if self.is_live is True:
            if isinstance(buy_percent, int):
                if buy_percent > 0 and buy_percent < 100:
                    quote_currency = (buy_percent / 100) * quote_currency

            if self.exchange == Exchange.COINBASE:
                api = CBAuthAPI(self.api_key, self.api_secret, self.api_url, app=self)
                return api.market_buy(market, float(_truncate(quote_currency, 8)))
            elif self.exchange == Exchange.COINBASEPRO:
                api = CAuthAPI(self.api_key, self.api_secret, self.api_passphrase, self.api_url, app=self)
                return api.market_buy(market, float(_truncate(quote_currency, 8)))
            elif self.exchange == Exchange.KUCOIN:
                api = KAuthAPI(self.api_key, self.api_secret, self.api_passphrase, self.api_url, use_cache=self.usekucoincache, app=self)
                return api.market_buy(market, (float(quote_currency) - (float(quote_currency) * api.get_maker_fee())))
            elif self.exchange == Exchange.BINANCE:
                api = BAuthAPI(self.api_key, self.api_secret, self.api_url, recv_window=self.recv_window, app=self)
                return api.market_buy(market, quote_currency)
            else:
                return None

    def market_sell(self, market, base_currency, sell_percent=100):
        if self.is_live is True:
            if isinstance(sell_percent, int):
                if sell_percent > 0 and sell_percent < 100:
                    base_currency = (sell_percent / 100) * base_currency

                if self.exchange == Exchange.COINBASE:
                    api = CBAuthAPI(self.api_key, self.api_secret, self.api_url, app=self)
                    return api.market_sell(market, base_currency)
                elif self.exchange == Exchange.COINBASEPRO:
                    api = CAuthAPI(self.api_key, self.api_secret, self.api_passphrase, self.api_url, app=self)
                    return api.market_sell(market, base_currency)
                elif self.exchange == Exchange.BINANCE:
                    api = BAuthAPI(self.api_key, self.api_secret, self.api_url, recv_window=self.recv_window, app=self)
                    return api.market_sell(market, base_currency, use_fees=self.use_sell_fee)
                elif self.exchange == Exchange.KUCOIN:
                    api = KAuthAPI(self.api_key, self.api_secret, self.api_passphrase, self.api_url, use_cache=self.usekucoincache, app=self)
                    return api.market_sell(market, base_currency)
            else:
                return None

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

        if self.is_sim:
            # initial amounts for sims
            self.state.last_buy_size = 1000
            self.state.first_buy_size = 1000

        if banner and not self.is_sim or (self.is_sim and not self.simresultonly):
            self._generate_banner()

        self.app_started = True
        # run the first job immediately after starting
        if self.is_sim:
            if self.sim_speed in ["fast-sample", "slow-sample"]:
                attempts = 0

                if self.simstartdate is not None and self.simenddate is not None:
                    start_date = self.get_date_from_iso8601_str(self.simstartdate)

                    if self.simenddate == "now":
                        end_date = self.get_date_from_iso8601_str(str(datetime.now()))
                    else:
                        end_date = self.get_date_from_iso8601_str(self.simenddate)

                elif self.simstartdate is not None and self.simenddate is None:
                    start_date = self.get_date_from_iso8601_str(self.simstartdate)
                    end_date = start_date + timedelta(minutes=(self.granularity.to_integer / 60) * self.adjusttotalperiods)

                elif self.simenddate is not None and self.simstartdate is None:
                    if self.simenddate == "now":
                        end_date = self.get_date_from_iso8601_str(str(datetime.now()))
                    else:
                        end_date = self.get_date_from_iso8601_str(self.simenddate)

                    start_date = end_date - timedelta(minutes=(self.granularity.to_integer / 60) * self.adjusttotalperiods)

                else:
                    end_date = self.get_date_from_iso8601_str(str(pd.Series(datetime.now()).dt.round(freq="H")[0]))
                    if self.exchange == Exchange.COINBASE or self.exchange == Exchange.COINBASEPRO:
                        end_date -= timedelta(hours=random.randint(0, 8760 * 3))  # 3 years in hours
                    else:
                        end_date -= timedelta(hours=random.randint(0, 8760 * 1))

                    start_date = self.get_date_from_iso8601_str(str(end_date))
                    start_date -= timedelta(minutes=(self.granularity.to_integer / 60) * self.adjusttotalperiods)

                while len(self.trading_data) < self.adjusttotalperiods and attempts < 10:
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
                    self.simstartdate = str(start_date)
                    self.simenddate = str(end_date)

                self.extra_candles_found = True

                if len(self.trading_data) < self.adjusttotalperiods:
                    raise Exception(
                        f"Unable to retrieve {str(self.adjusttotalperiods)} random sets of data between {start_date} and {end_date} in 10 attempts."
                    )

                if banner:
                    text_box = TextBox(80, 26)
                    start_date = str(start_date.isoformat())
                    end_date = str(end_date.isoformat())
                    text_box.line("Sampling start", str(start_date))
                    text_box.line("Sampling end", str(end_date))
                    if self.simstartdate is None and len(self.trading_data) < self.adjusttotalperiods:
                        text_box.center(f"WARNING: Using less than {str(self.adjusttotalperiods)} intervals")
                        text_box.line("Interval size", str(len(self.trading_data)))
                    text_box.doubleLine()

            else:
                start_date = self.get_date_from_iso8601_str(str(datetime.now()))
                start_date -= timedelta(minutes=(self.granularity.to_integer / 60) * 2)
                end_date = start_date
                start_date = pd.Series(start_date).dt.round(freq="H")[0]
                end_date = pd.Series(end_date).dt.round(freq="H")[0]

                if self.is_sim and self.simstartdate:
                    start_date = self.simstartdate
                else:
                    start_date -= timedelta(minutes=(self.granularity.to_integer / 60) * self.adjusttotalperiods)

                if self.is_sim and self.simenddate:
                    end_date = self.simenddate
                else:
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
                        self.get_date_from_iso8601_str(str(end_date)).isoformat(),
                    )

    def _simulation_summary(self) -> dict:
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
            "exchange": str(self.exchange).replace("Exchange.", "").lower(),
        }

        if self.get_config() != "":
            simulation["config"] = self.get_config()

        if self.state.buy_count == 0:
            self.state.last_buy_size = 0
            self.state.sell_sum = 0
        else:
            self.state.sell_sum = self.state.sell_sum + self.state.last_sell_size

        table = Table(title=f"Simulation Summary: {self.market}", box=box.SQUARE, min_width=40, border_style="white", show_header=False)

        table.add_column("Item", justify="right", style="white", no_wrap=True)
        table.add_column("Value", justify="left", style="cyan")

        remove_last_buy = False
        if self.state.buy_count > self.state.sell_count:
            remove_last_buy = True
            self.state.buy_count -= 1  # remove last buy as there has not been a corresponding sell yet
            self.state.last_buy_size = self.state.previous_buy_size
            simulation["data"]["open_buy_excluded"] = 1

            if not self.simresultonly:
                table.add_row("Warning", Text("Simulation ended with an open trade and it will be excluded from the margin calculation.", style="orange1"))
                table.add_row("")
        else:
            simulation["data"]["open_buy_excluded"] = 0

        if remove_last_buy is True:
            if not self.simresultonly:
                table.add_row("Buy Count", Text(f"{str(self.state.buy_count)} (open buy order excluded)", "orange1"), style="white")
            else:
                simulation["data"]["buy_count"] = self.state.buy_count
        else:
            if not self.simresultonly:
                table.add_row("Buy Count", f"{str(self.state.buy_count)}", style="white")
            else:
                simulation["data"]["buy_count"] = self.state.buy_count

        if not self.simresultonly:
            table.add_row("Sell Count", str(self.state.sell_count), style="white")

            table.add_row("")
            table.add_row(f"First Buy Order ({self.quote_currency})", Text(str(self.state.first_buy_size), style="white"), style="white")

            table.add_row("")
            if self.state.last_sell_size > self.state.last_buy_size:
                table.add_row(f"Last Buy Order ({self.quote_currency})", Text(_truncate(self.state.last_buy_size, 4), style="bright_green"), style="white")
            elif self.state.last_buy_size == self.state.last_sell_size:
                table.add_row(f"Last Buy Order ({self.quote_currency})", Text(_truncate(self.state.last_buy_size, 4), style="orange1"), style="white")
            else:
                table.add_row(f"Last Buy Order ({self.quote_currency})", Text(_truncate(self.state.last_buy_size, 4), style="bright_red"), style="white")
        else:
            simulation["data"]["sell_count"] = self.state.sell_count
            simulation["data"]["first_trade"] = {}
            simulation["data"]["first_trade"]["size"] = self.state.first_buy_size

        if self.state.sell_count > 0:
            if not self.simresultonly:
                if self.state.last_sell_size > self.state.last_buy_size:
                    table.add_row(
                        f"Last Sell Order ({self.quote_currency})", Text(_truncate(self.state.last_sell_size, 4), style="bright_green"), style="white"
                    )
                elif self.state.last_buy_size == self.state.last_sell_size:
                    table.add_row(f"Last Sell Order ({self.quote_currency})", Text(_truncate(self.state.last_sell_size, 4), style="orange1"), style="white")
                else:
                    table.add_row(f"Last Sell Order ({self.quote_currency})", Text(_truncate(self.state.last_sell_size, 4), style="bright_red"), style="white")
            else:
                simulation["data"]["last_trade"] = {}
                simulation["data"]["last_trade"]["size"] = float(_truncate(self.state.last_sell_size, 2))
        else:
            if not self.simresultonly:
                table.add_row("")
                table.add_row("Margin", "0.00% (margin is nil as a sell has not occurred during the simulation)")
                table.add_row("")
            else:
                simulation["data"]["margin"] = 0.0

            if not self.disabletelegram:
                self.notify_telegram("      Margin: 0.00%\n  ** margin is nil as a sell has not occurred during the simulation\n")

        if not self.disabletelegram:
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
            _last_trade_margin = float(
                _truncate(
                    (((self.state.last_sell_size - self.state.last_buy_size) / self.state.last_buy_size) * 100),
                    4,
                )
            )

            if not self.simresultonly:
                if _last_trade_margin > 0:
                    table.add_row("Last Trade Margin", Text(f"{_last_trade_margin}%", style="bright_green"), style="white")
                elif _last_trade_margin < 0:
                    table.add_row("Last Trade Margin", Text(f"{_last_trade_margin}%", style="bright_red"), style="white")
                else:
                    table.add_row("Last Trade Margin", Text(f"{_last_trade_margin}%", style="orange1"), style="white")

                if remove_last_buy:
                    table.add_row("")
                    table.add_row(
                        "Open Trade Margin",
                        Text(f"{self.state.open_trade_margin} (open trade excluded from margin calculation)", style="orange1"),
                        style="white",
                    )

                table.add_row("")
                table.add_row(f"Total Buy Volume ({self.quote_currency})", Text(_truncate(self.state.buy_tracker, 2), style="white"), style="white")

                table.add_row("")
                if self.state.profitlosstracker > 0:
                    table.add_row(
                        f"All Trades Profit/Loss ({self.quote_currency})",
                        Text(f"{_truncate(self.state.profitlosstracker, 2)} ({_truncate(self.state.feetracker,2)} in fees)", style="bright_green"),
                        style="white",
                    )
                    table.add_row(
                        f"All Trades Margin ({self.quote_currency})",
                        Text(f"{_truncate(self.state.margintracker, 4)}% (non-live simulation, assuming highest fees)", style="bright_green"),
                        style="white",
                    )
                elif self.state.profitlosstracker < 0:
                    table.add_row(
                        f"All Trades Profit/Loss ({self.quote_currency})",
                        Text(f"{_truncate(self.state.profitlosstracker, 2)} ({_truncate(self.state.feetracker,2)} in fees)", style="bright_red"),
                        style="white",
                    )
                    table.add_row(
                        f"All Trades Margin ({self.quote_currency})",
                        Text(f"{_truncate(self.state.margintracker, 4)}% (non-live simulation, assuming highest fees)", style="bright_red"),
                        style="white",
                    )
                else:
                    table.add_row(
                        f"All Trades Profit/Loss ({self.quote_currency})",
                        Text(f"{_truncate(self.state.profitlosstracker, 2)} ({_truncate(self.state.feetracker,2)} in fees)", style="orange1"),
                        style="white",
                    )
                    table.add_row(
                        f"All Trades Margin ({self.quote_currency})",
                        Text(f"{_truncate(self.state.margintracker, 4)}% (non-live simulation, assuming highest fees)", style="orange1"),
                        style="white",
                    )
            else:
                simulation["data"]["last_trade"]["margin"] = _last_trade_margin
                simulation["data"]["all_trades"] = {}
                simulation["data"]["all_trades"]["quote_currency"] = self.quote_currency
                simulation["data"]["all_trades"]["value_buys"] = float(_truncate(self.state.buy_tracker, 2))
                simulation["data"]["all_trades"]["profit_loss"] = float(_truncate(self.state.profitlosstracker, 2))
                simulation["data"]["all_trades"]["fees"] = float(_truncate(self.state.feetracker, 2))
                simulation["data"]["all_trades"]["margin"] = float(_truncate(self.state.margintracker, 4))
                simulation["data"]["all_trades"]["open_trade_margin"] = float(_truncate(self.state.open_trade_margin_float, 4))

            ## revised telegram Summary notification to give total margin in addition to last trade margin.
            if not self.disabletelegram:
                self.notify_telegram(f"      Last Trade Margin: {_last_trade_margin}%\n\n")

            if remove_last_buy and not self.disabletelegram:
                self.notify_telegram(f"\nOpen Trade Margin at end of simulation: {self.state.open_trade_margin}\n")

            if not self.disabletelegram:
                self.notify_telegram(
                    f"      All Trades Margin: {_truncate(self.state.margintracker, 4)}%\n  ** non-live simulation, assuming highest fees\n  ** open trade excluded from margin calculation\n"
                )

            if not self.disabletelegram:
                self.telegram_bot.remove_active_bot()

        if self.simresultonly:
            print(json.dumps(simulation, sort_keys=True, indent=4))
        else:
            print("")  # blank line above table
            self.console_term.print(table)
            if self.disablelog is False:
                self.console_log.print(table)
            print("")  # blank line below table

        return simulation

    def _simulation_save_orders(self) -> None:
        if not self.disabletracker:
            start = str(self.trading_data.head(1).index.format()[0]).replace(":", ".")
            end = str(self.trading_data.tail(1).index.format()[0]).replace(":", ".")
            filename = f"{self.market} {str(self.granularity.to_integer)} {str(start)} - {str(end)}_{self.tradesfile}"

            try:
                if not os.path.isabs(filename):
                    if not os.path.exists("csv"):
                        os.makedirs("csv")
                self.trade_tracker.to_csv(os.path.join(os.curdir, "csv", filename))
            except OSError:
                RichText.notify(f"Unable to save: {filename}", "critical", self, "error")

    def _generate_banner(self) -> None:
        """
        Requirements for bot options:
        - Update _generate_banner() in controllers/PyCryptoBot.py
        - Update the command line arguments below
        - Update the config parser in models/config/default_parser.py
        """

        def config_option_row_int(
            item: str = None, store_name: str = None, description: str = None, break_below: bool = False, default_value: int = 0, arg_name: str = None
        ) -> bool:
            if item is None or store_name is None or description is None:
                return False

            if arg_name is None:
                arg_name = store_name

            if getattr(self, store_name) != default_value:
                table.add_row(item, str(getattr(self, store_name)), description, f"--{arg_name} <num>")
            else:
                table.add_row(item, str(getattr(self, store_name)), description, f"--{arg_name} <num>", style="grey62")

            if break_below is True:
                table.add_row("", "", "")

            return True

        def config_option_row_float(
            item: str = None, store_name: str = None, description: str = None, break_below: bool = False, default_value: float = 0, arg_name: str = None
        ) -> bool:
            if item is None or store_name is None or description is None:
                return False

            if arg_name is None:
                arg_name = store_name

            if getattr(self, store_name) != default_value:
                table.add_row(item, str(getattr(self, store_name)), description, f"--{arg_name} <num>")
            else:
                table.add_row(item, str(getattr(self, store_name)), description, f"--{arg_name} <num>", style="grey62")

            if break_below is True:
                table.add_row("", "", "")

            return True

        def config_option_row_bool(
            item: str = None,
            store_name: str = None,
            description: str = None,
            break_below: bool = False,
            store_invert: bool = False,
            default_value: bool = False,
            arg_name: str = None,
        ) -> bool:
            if item is None or store_name is None or description is None:
                return False

            if arg_name is None:
                arg_name = store_name

            if store_invert is True:
                if not getattr(self, store_name) is not default_value:
                    table.add_row(item, str(not getattr(self, store_name)), description, f"--{arg_name} <1|0>")
                else:
                    table.add_row(item, str(not getattr(self, store_name)), description, f"--{arg_name} <1|0>", style="grey62")
            else:
                if getattr(self, store_name) is not default_value:
                    table.add_row(item, str(getattr(self, store_name)), description, f"--{arg_name} <1|0>")
                else:
                    table.add_row(item, str(getattr(self, store_name)), description, f"--{arg_name} <1|0>", style="grey62")

            if break_below is True:
                table.add_row("", "", "")

            return True

        def config_option_row_str(
            item: str = None, store_name: str = None, description: str = None, break_below: bool = False, default_value: str = "", arg_name: str = None
        ) -> bool:
            if item is None or store_name is None or description is None:
                return False

            if arg_name is None:
                arg_name = store_name

            try:
                if getattr(self, store_name) != default_value:
                    table.add_row(item, str(getattr(self, store_name)), description, f"--{arg_name} <str>")
                else:
                    table.add_row(item, str(getattr(self, store_name)), description, f"--{arg_name} <str>", style="grey62")
            except AttributeError:
                pass  # ignore

            if break_below is True:
                table.add_row("", "", "")

            return True

        def config_option_row_enum(
            item: str = None, store_name: str = None, description: str = None, break_below: bool = False, default_value: str = "", arg_name: str = None
        ) -> bool:
            if item is None or store_name is None or description is None:
                return False

            if arg_name is None:
                arg_name = store_name

            if str(getattr(self, store_name)).replace(f"{item}.", "").lower() != default_value:
                table.add_row(item, str(getattr(self, store_name)).replace(f"{item}.", "").lower(), description, f"--{arg_name} <str>")
            else:
                table.add_row(item, str(getattr(self, store_name)).replace(f"{item}.", "").lower(), description, f"--{arg_name} <str>", style="grey62")

            if break_below is True:
                table.add_row("", "", "")

            return True

        table = Table(title=f"Python Crypto Bot {self.get_version_from_readme(self)}")

        table.add_column("Item", justify="right", style="cyan", no_wrap=True)
        table.add_column("Value", justify="left", style="green")
        table.add_column("Description", justify="left", style="magenta")
        table.add_column("Option", justify="left", style="white")

        table.add_row("Start", str(datetime.now()), "Bot start time")
        table.add_row("", "", "")

        config_option_row_bool(
            "Enable Terminal Color",
            "term_color",
            "Enable terminal UI color",
            store_invert=False,
            default_value=True,
            arg_name="termcolor",
        )
        config_option_row_int("Terminal UI Width", "term_width", "Set terminal UI width", default_value=self.term_width, arg_name="termwidth")
        config_option_row_int("Terminal Log Width", "log_width", "Set terminal log width", break_below=True, default_value=180, arg_name="logwidth")

        if self.is_live:
            table.add_row("Bot Mode", "LIVE", "Live trades using your funds!", "--live <1|0>")
        else:
            if self.is_sim:
                table.add_row("Bot Mode", "SIMULATION", "Back testing using simulations", "--sim <fast|slow>")
            else:
                table.add_row("Bot Mode", "TEST", "Test trades using dummy funds :)", "--live <1|0>")

        table.add_row("", "", "")

        config_option_row_enum("Exchange", "exchange", "Crypto currency exchange", default_value=None, arg_name="exchange")
        config_option_row_str(
            "Market", "market", "coinbase, coinbasepro and kucoin: BTC-GBP, binance: BTCGBP etc.", break_below=False, default_value=None, arg_name="market"
        )
        config_option_row_enum("Granularity", "granularity", "Granularity of the data", break_below=True, default_value="3600", arg_name="granularity")

        config_option_row_bool(
            "Enable Debugging",
            "debug",
            "Enable debug level logging",
            break_below=True,
            store_invert=False,
            default_value=False,
            arg_name="debug",
        )

        config_option_row_str(
            "Sim Start Date",
            "simstartdate",
            "Start date for sample simulation e.g '2021-01-15'",
            break_below=False,
            default_value=None,
            arg_name="simstartdate",
        )
        config_option_row_str(
            "Sim End Date",
            "simenddate",
            "End date for sample simulation e.g '2021-01-15' or 'now'",
            break_below=False,
            default_value=None,
            arg_name="simenddate",
        )
        config_option_row_bool(
            "Sim Results Only",
            "simresultonly",
            "Simulation returns only the results",
            break_below=True,
            store_invert=False,
            default_value=False,
            arg_name="simresultonly",
        )

        config_option_row_bool(
            "Telegram Notifications",
            "disabletelegram",
            "Enable Telegram notification messages",
            store_invert=True,
            default_value=False,
            arg_name="telegram",
        )
        config_option_row_bool(
            "Telegram Trades Only",
            "telegramtradesonly",
            "Telegram trades notifications only",
            store_invert=False,
            default_value=False,
            arg_name="telegramtradesonlys",
        )
        config_option_row_bool(
            "Telegram Error Messages",
            "disabletelegramerrormsgs",
            "Telegram error message notifications",
            break_below=False,
            store_invert=True,
            default_value=False,
            arg_name="telegramerrormsgs",
        )
        config_option_row_bool(
            "Telegram Bot Control",
            "telegrambotcontrol",
            "Control your bot(s) with Telegram",
            break_below=True,
            store_invert=False,
            default_value=False,
            arg_name="telegrambotcontrol",
        )

        config_option_row_str(
            "Config File", "config_file", "Use the config file at the given location", break_below=False, default_value="config.json", arg_name="configfile"
        )
        config_option_row_str(
            "API Key File", "api_key_file", "Use the API key file at the given location", break_below=False, default_value=None, arg_name="api_key_file"
        )
        config_option_row_str(
            "Log File", "logfile", "Use the log file at the given location", break_below=False, default_value="pycryptobot.log", arg_name="logfile"
        )
        config_option_row_str(
            "Trades File",
            "tradesfile",
            "Use the simulation log trades at the given location",
            break_below=True,
            default_value="trades.csv",
            arg_name="tradesfile",
        )

        config_option_row_bool("Enable Log", "disablelog", "Enable console logging", store_invert=True, default_value=True, arg_name="log")
        config_option_row_bool(
            "Enable Smart Switching", "smart_switch", "Enable switching between intervals", store_invert=False, default_value=False, arg_name="smartswitch"
        )
        config_option_row_bool(
            "Enable Tracker", "disabletracker", "Enable trade order logging", store_invert=True, default_value=False, arg_name="tradetracker"
        )
        config_option_row_bool(
            "Auto Restart Bot", "autorestart", "Auto restart the bot in case of exception", store_invert=False, default_value=False, arg_name="autorestart"
        )
        config_option_row_bool(
            "Enable Websocket", "websocket", "Enable websockets for data retrieval", store_invert=False, default_value=False, arg_name="websocket"
        )
        config_option_row_bool(
            "Insufficient Funds Log",
            "enableinsufficientfundslogging",
            "Enable insufficient funds logging",
            store_invert=False,
            default_value=False,
            arg_name="insufficientfundslogging",
        )
        config_option_row_bool(
            "JSON Log Trade", "logbuysellinjson", "Log buy and sell orders in a JSON file", store_invert=False, default_value=False, arg_name="logbuysellinjson"
        )
        config_option_row_bool(
            "Manual Trading Only",
            "manual_trades_only",
            "Manual Trading Only (HODL)",
            break_below=False,
            store_invert=False,
            default_value=False,
            arg_name="manualtradesonly",
        )
        config_option_row_str(
            "Start Method",
            "startmethod",
            "Bot start method ('scanner', 'standard', 'telegram')",
            break_below=False,
            default_value="standard",
            arg_name="startmethod",
        )
        config_option_row_bool(
            "Save Trading Graphs",
            "save_graphs",
            "Save graph images of trades",
            break_below=False,
            store_invert=False,
            default_value=False,
            arg_name="graphs",
        )
        config_option_row_float(
            "Binance recvWindow",
            "recv_window",
            "Binance exchange API recvwindow, integer between 5000 and 60000",
            break_below=False,
            default_value=5000,
            arg_name="recvwindow",
        )
        config_option_row_bool(
            "Exit After Sell",
            "exitaftersell",
            "Exit the bot after a sell order",
            break_below=False,
            store_invert=False,
            default_value=False,
            arg_name="exitaftersell",
        )
        config_option_row_bool(
            "Ignore Previous Buy",
            "ignorepreviousbuy",
            "Ignore previous buy failure",
            break_below=False,
            store_invert=False,
            default_value=True,
            arg_name="ignorepreviousbuy",
        )
        config_option_row_bool(
            "Ignore Previous Sell",
            "ignoreprevioussell",
            "Ignore previous sell failure",
            break_below=True,
            store_invert=False,
            default_value=True,
            arg_name="ignoreprevioussell",
        )

        config_option_row_int(
            "Adjust Total Periods", "adjusttotalperiods", "Adjust data points in historical trading data", break_below=True, default_value=300
        )

        config_option_row_float("Sell Upper Percent", "sell_upper_pcnt", "Upper trade margin to sell", default_value=None, arg_name="sellupperpcnt")
        config_option_row_float("Sell Lower Percent", "sell_lower_pcnt", "Lower trade margin to sell", default_value=None, arg_name="selllowerpcnt")
        config_option_row_float(
            "No Sell Max", "nosellmaxpcnt", "Do not sell while trade margin is below this level", default_value=None, arg_name="nosellmaxpcnt"
        )
        config_option_row_float(
            "No Sell Min", "nosellminpcnt", "Do not sell while trade margin is above this level", break_below=True, default_value=None, arg_name="nosellminpcnt"
        )

        config_option_row_bool(
            "Prevent Loss", "preventloss", "Force a sell before margin is negative", store_invert=False, default_value=False, arg_name="preventloss"
        )
        config_option_row_float(
            "Prevent Loss Trigger", "preventlosstrigger", "Margin that will trigger the prevent loss", default_value=1.0, arg_name="preventlosstrigger"
        )
        config_option_row_float(
            "Prevent Loss Margin",
            "preventlossmargin",
            "Margin that will cause an immediate sell to prevent loss",
            default_value=0.1,
            arg_name="preventlossmargin",
        )
        config_option_row_bool(
            "Sell At Loss",
            "sellatloss",
            "Allow a sell if the profit margin is negative",
            break_below=True,
            store_invert=False,
            default_value=True,
            arg_name="sellatloss",
        )

        config_option_row_bool(
            "Buy Bull Only",
            "disablebullonly",
            "Only trade in a bull market SMA50 > SMA200",
            break_below=True,
            store_invert=True,
            default_value=False,
            arg_name="bullonly",
        )

        config_option_row_bool(
            "Sell At Resistance",
            "sellatresistance",
            "Sell if the price hits a resistance level",
            store_invert=False,
            default_value=False,
            arg_name="sellatresistance",
        )
        config_option_row_bool(
            "Sell At Fibonacci Low",
            "disablefailsafefibonaccilow",
            "Sell if the price hits a fibonacci lower level",
            store_invert=True,
            default_value=False,
            arg_name="sellatfibonaccilow",
        )
        config_option_row_bool(
            "Sell Candlestick Reversal",
            "disableprofitbankreversal",
            "Sell at candlestick strong reversal pattern",
            break_below=True,
            store_invert=True,
            default_value=False,
            arg_name="profitbankreversal",
        )

        config_option_row_float(
            "Trailing Stop Loss (TSL)", "trailing_stop_loss", "Percentage below the trade margin high to sell", default_value=0.0, arg_name="trailingstoploss"
        )
        config_option_row_float(
            "Trailing Stop Loss Trigger",
            "trailing_stop_loss_trigger",
            "Trade margin percentage to enable the trailing stop loss",
            default_value=0.0,
            arg_name="trailingstoplosstrigger",
        )
        config_option_row_float(
            "Trailing Sell Percent", "trailingsellpcnt", "Percentage of decrease to wait before selling", default_value=0.0, arg_name="trailingsellpcnt"
        )
        config_option_row_bool(
            "Immediate Trailing Sell",
            "trailingimmediatesell",
            "Immediate sell if trailing sell percent is reached",
            store_invert=False,
            default_value=False,
            arg_name="trailingimmediatesell",
        )
        config_option_row_float(
            "Immediate Trailing Sell Percent",
            "trailingsellimmediatepcnt",
            "Percentage of decrease used with a strong sell signal",
            default_value=0.0,
            arg_name="trailingsellimmediatepcnt",
        )
        config_option_row_float(
            "Trailing Sell Bailout Percent",
            "trailingsellbailoutpcnt",
            "Percentage of decrease to bailout, sell immediately",
            break_below=True,
            default_value=0.0,
            arg_name="trailingsellbailoutpcnt",
        )

        config_option_row_bool(
            "Dynamic Trailing Stop Loss (TSL)",
            "dynamic_tsl",
            "Dynamic Trailing Stop Loss (TSL)",
            store_invert=False,
            default_value=False,
            arg_name="dynamictsl",
        )
        config_option_row_float(
            "TSL Multiplier", "tsl_multiplier", "Please refer to the detailed explanation in the README.md", default_value=1.1, arg_name="tslmultiplier"
        )
        config_option_row_float(
            "TSL Trigger Multiplier",
            "tsl_trigger_multiplier",
            "Please refer to the detailed explanation in the README.md",
            default_value=1.1,
            arg_name="tsltriggermultiplier",
        )
        config_option_row_float(
            "TSL Max Percent",
            "tsl_max_pcnt",
            "Please refer to the detailed explanation in the README.md",
            break_below=True,
            default_value=-5.0,
            arg_name="tslmaxpcnt",
        )

        config_option_row_float("Buy Percent", "buypercent", "Buy order size in quote currency as a percentage", default_value=100.0, arg_name="buypercent")
        config_option_row_float("Sell Percent", "sellpercent", "Sell order size in quote currency as a percentage", default_value=100.0, arg_name="sellpercent")

        config_option_row_float("Buy Min Size", "buyminsize", "Minimum buy order size in quote currency", default_value=0.0, arg_name="buyminsize")
        config_option_row_float("Buy Max Size", "buymaxsize", "Maximum buy order size in quote currency", default_value=0.0, arg_name="buymaxsize")
        config_option_row_bool(
            "Buy Last Sell Size",
            "buylastsellsize",
            "Next buy order will match last sell order",
            store_invert=False,
            default_value=False,
            arg_name="buylastsellsize",
        )
        config_option_row_bool(
            "Multiple Buy Check",
            "marketmultibuycheck",
            "Additional check for market multiple buys",
            store_invert=False,
            default_value=False,
            arg_name="marketmultibuycheck",
        )
        config_option_row_bool(
            "Allow Buy Near High",
            "disablebuynearhigh",
            "Prevent the bot from buying at a recent high",
            store_invert=True,
            default_value=True,
            arg_name="buynearhigh",
        )
        config_option_row_float(
            "No Buy Near High Percent",
            "nobuynearhighpcnt",
            "Percentage from the range high to not buy",
            break_below=True,
            default_value=3.0,
            arg_name="buynearhighpcnt",
        )

        config_option_row_float(
            "Trailing Buy Percent",
            "trailingbuypcnt",
            "Percentage of increase to wait before buying",
            default_value=0.0,
            arg_name="trailingbuypcnt",
        )
        config_option_row_bool(
            "Immediate Trailing Buy",
            "trailingimmediatebuy",
            "Immediate buy if trailing buy percent is reached",
            store_invert=False,
            default_value=False,
            arg_name="trailingimmediatebuy",
        )
        config_option_row_float(
            "Immediate Trailing Buy Percent",
            "trailingbuyimmediatepcnt",
            "Percent of increase to trigger immediate buy",
            break_below=True,
            default_value=0.0,
            arg_name="trailingbuyimmediatepcnt",
        )

        config_option_row_bool("Override Sell Trigger", "selltriggeroverride", "Override sell trigger if strong buy", break_below=True, default_value=False)

        config_option_row_bool("Use EMA12/26", "disablebuyema", "Exponential Moving Average (EMA)", store_invert=True, default_value=True, arg_name="ema1226")
        config_option_row_bool(
            "Use MACD/Signal", "disablebuymacd", "Moving Average Convergence Divergence (MACD)", store_invert=True, default_value=True, arg_name="macdsignal"
        )
        config_option_row_bool("On-Balance Volume (OBV)", "disablebuyobv", "On-Balance Volume (OBV)", store_invert=True, default_value=False, arg_name="obv")
        config_option_row_bool(
            "Use Elder-Ray", "disablebuyelderray", "Elder-Ray Index (Elder-Ray)", store_invert=True, default_value=False, arg_name="elderray"
        )
        config_option_row_bool(
            "Use Bollinger Bands", "disablebuybbands_s1", "Bollinger Bands - Strategy 1", store_invert=True, default_value=False, arg_name="bbands_s1"
        )
        config_option_row_bool(
            "Use Bollinger Bands",
            "disablebuybbands_s2",
            "Bollinger Bands - Strategy 2",
            break_below=True,
            store_invert=True,
            default_value=False,
            arg_name="bbands_s2",
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
        if self.exchange == Exchange.COINBASE:
            return str(self.granularity.to_integer)
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
        def _notify(notification: str = "", level: str = "normal") -> None:
            if notification == "":
                return

            if level == "warning":
                color = "dark_orange"
            elif level == "error":
                color = "red1"
            elif level == "critical":
                color = "red1 blink"
            else:
                color = "violet"

            self.table_console = Table(title=None, box=None, show_header=False, show_footer=False)
            self.table_console.add_row(
                RichText.styled_text("Bot1", "magenta"),
                RichText.styled_text(datetime.today().strftime("%Y-%m-%d %H:%M:%S"), "white"),
                RichText.styled_text(self.market, "yellow"),
                RichText.styled_text(self.print_granularity(), "yellow"),
                RichText.styled_text(notification, color),
            )
            self.console_term.print(self.table_console)
            if self.disablelog is False:
                self.console_log.print(self.table_console)
            self.table_console = Table(title=None, box=None, show_header=False, show_footer=False)  # clear table

        if self.is_sim:
            df_first = None
            df_last = None

            result_df_cache = df

            simstart = self.get_date_from_iso8601_str(simstart)
            simend = self.get_date_from_iso8601_str(simend)

            try:
                # if df already has data get first and last record date
                if len(df) > 0:
                    df_first = self.get_date_from_iso8601_str(str(df.head(1).index.format()[0]))
                    df_last = self.get_date_from_iso8601_str(str(df.tail(1).index.format()[0]))
                else:
                    result_df_cache = pd.DataFrame()

            except Exception:
                # if df = None create a new data frame
                result_df_cache = pd.DataFrame()

            if df_first is None and df_last is None:
                if not self.is_sim or (self.is_sim and not self.simresultonly):
                    if self.smart_switch:
                        _notify(f"Retrieving smart switch {granularity.to_short} market data from the exchange.")
                    else:
                        _notify(f"Retrieving {granularity.to_short} market data from the exchange.")

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
                while df_first.isoformat(timespec="milliseconds") > simstart.isoformat(timespec="milliseconds") or df_first.isoformat(
                    timespec="milliseconds"
                ) > originalSimStart.isoformat(timespec="milliseconds"):
                    end_date = df_first
                    df_first -= timedelta(minutes=(self.adjusttotalperiods * (granularity.to_integer / 60)))

                    if df_first.isoformat(timespec="milliseconds") < simstart.isoformat(timespec="milliseconds"):
                        df_first = self.get_date_from_iso8601_str(str(simstart))

                    df2 = self.get_historical_data(
                        market,
                        granularity,
                        None,
                        str(df_first.isoformat()),
                        str(end_date.isoformat()),
                    )

                    # check to see if there are an extra 300 candles available to be used, if not just use the original starting point
                    if self.adjusttotalperiods >= 300 and adding_extra_candles is True and len(df2) <= 0:
                        self.extra_candles_found = False
                        simstart = originalSimStart
                    else:
                        result_df_cache = pd.concat([df2.copy(), df1.copy()]).drop_duplicates()
                        df1 = result_df_cache

                    # create df with 300 candles or adjusted total periods before the required start_date to match live
                    if df_first.isoformat(timespec="milliseconds") == simstart.isoformat(timespec="milliseconds"):
                        if adding_extra_candles is False:
                            simstart -= timedelta(minutes=(self.adjusttotalperiods * (granularity.to_integer / 60)))
                        adding_extra_candles = True
                        self.extra_candles_found = True

            if len(result_df_cache) > 0 and "morning_star" not in result_df_cache:
                result_df_cache.sort_values(by=["date"], ascending=True, inplace=True)

            if self.smart_switch is False:
                if self.extra_candles_found is False:
                    _notify(f"{str(self.exchange.value)} is not returning data for the requested start date.")
                    _notify(f"Switching to earliest start date: {str(result_df_cache.head(1).index.format()[0])}.")
                    self.simstartdate = str(result_df_cache.head(1).index.format()[0])

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
                self.ema1226_5m_cache = self.get_smart_switch_df(self.ema1226_5m_cache, market, Granularity.FIVE_MINUTES, start, end)
            self.ema1226_15m_cache = self.get_smart_switch_df(self.ema1226_15m_cache, market, Granularity.FIFTEEN_MINUTES, start, end)
            self.ema1226_1h_cache = self.get_smart_switch_df(self.ema1226_1h_cache, market, Granularity.ONE_HOUR, start, end)
            self.ema1226_6h_cache = self.get_smart_switch_df(self.ema1226_6h_cache, market, Granularity.SIX_HOURS, start, end)

            if len(self.ema1226_15m_cache) == 0:
                raise Exception(f"No data return for selected date range {start} - {end}")

            if not self.extra_candles_found:
                if granularity == Granularity.FIVE_MINUTES:
                    if (
                        self.get_date_from_iso8601_str(str(self.ema1226_5m_cache.index.format()[0])).isoformat()
                        != self.get_date_from_iso8601_str(start).isoformat()
                    ):
                        text_box = TextBox(80, 26)
                        text_box.singleLine()
                        text_box.center(f"{str(self.exchange.value)}is not returning data for the requested start date.")
                        text_box.center(f"Switching to earliest start date: {str(self.ema1226_5m_cache.head(1).index.format()[0])}")
                        text_box.singleLine()
                        self.simstartdate = str(self.ema1226_5m_cache.head(1).index.format()[0])
                elif granularity == Granularity.FIFTEEN_MINUTES:
                    if (
                        self.get_date_from_iso8601_str(str(self.ema1226_15m_cache.index.format()[0])).isoformat()
                        != self.get_date_from_iso8601_str(start).isoformat()
                    ):
                        text_box = TextBox(80, 26)
                        text_box.singleLine()
                        text_box.center(f"{str(self.exchange.value)}is not returning data for the requested start date.")
                        text_box.center(f"Switching to earliest start date: {str(self.ema1226_15m_cache.head(1).index.format()[0])}")
                        text_box.singleLine()
                        self.simstartdate = str(self.ema1226_15m_cache.head(1).index.format()[0])
                else:
                    if (
                        self.get_date_from_iso8601_str(str(self.ema1226_1h_cache.index.format()[0])).isoformat()
                        != self.get_date_from_iso8601_str(start).isoformat()
                    ):
                        text_box = TextBox(80, 26)
                        text_box.singleLine()
                        text_box.center(f"{str(self.exchange.value)} is not returning data for the requested start date.")
                        text_box.center(f"Switching to earliest start date: {str(self.ema1226_1h_cache.head(1).index.format()[0])}")
                        text_box.singleLine()
                        self.simstartdate = str(self.ema1226_1h_cache.head(1).index.format()[0])

            if granularity == Granularity.FIFTEEN_MINUTES:
                return self.ema1226_15m_cache
            elif granularity == Granularity.FIVE_MINUTES:
                return self.ema1226_5m_cache
            else:
                return self.ema1226_1h_cache

    def get_historical_data_chained(self, market, granularity: Granularity, max_iterations: int = 1) -> pd.DataFrame:
        df1 = self.get_historical_data(market, granularity, None)

        if max_iterations == 1:
            return df1

        def get_previous_date_range(df: pd.DataFrame = None) -> tuple:
            end_date = df["date"].min() - timedelta(seconds=(granularity.to_integer / 60))
            new_start = df["date"].min() - timedelta(hours=self.adjusttotalperiods)
            return (str(new_start).replace(" ", "T"), str(end_date).replace(" ", "T"))

        iterations = 0
        result_df = pd.DataFrame()
        while iterations < (max_iterations - 1):
            start_date, end_date = get_previous_date_range(df1)
            df2 = self.get_historical_data(market, granularity, None, start_date, end_date)
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
        if self.exchange == Exchange.COINBASE:
            api = CBAuthAPI(self.api_key, self.api_secret, self.api_url, app=self)

        elif self.exchange == Exchange.BINANCE:
            api = BPublicAPI(api_url=self.api_url, app=self)

        elif self.exchange == Exchange.KUCOIN:  # returns data from coinbase if not specified
            api = KPublicAPI(api_url=self.api_url, app=self)

            # Kucoin only returns 100 rows if start not specified, make sure we get the right amount
            if not self.is_sim and iso8601start == "":
                start = datetime.now() - timedelta(minutes=(granularity.to_integer / 60) * self.adjusttotalperiods)
                iso8601start = str(start.isoformat()).split(".")[0]

        else:  # returns data from coinbase pro if not specified
            api = CPublicAPI(app=self)

        if iso8601start != "" and iso8601end == "" and self.exchange != Exchange.BINANCE:
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
        if self.exchange == Exchange.COINBASE:
            api = CBAuthAPI(self.api_key, self.api_secret, self.api_url, app=self)
            return api.get_ticker(market, websocket)
        if self.exchange == Exchange.BINANCE:
            api = BPublicAPI(api_url=self.api_url, app=self)
            return api.get_ticker(market, websocket)
        elif self.exchange == Exchange.KUCOIN:
            api = KPublicAPI(api_url=self.api_url, app=self)
            return api.get_ticker(market, websocket)
        else:  # returns data from coinbase pro if not specified
            api = CPublicAPI(app=self)
            return api.get_ticker(market, websocket)

    def get_time(self):
        if self.exchange == Exchange.COINBASE:
            return CPublicAPI(app=self).get_time()
        elif self.exchange == Exchange.COINBASEPRO:
            return CPublicAPI(app=self).get_time()
        elif self.exchange == Exchange.KUCOIN:
            return KPublicAPI(app=self).get_time()
        elif self.exchange == Exchange.BINANCE:
            try:
                return BPublicAPI(app=self).get_time()
            except ReadTimeoutError:
                return ""
        else:
            return ""

    def get_interval(self, df: pd.DataFrame = pd.DataFrame(), iterations: int = 0) -> pd.DataFrame:
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
                df_data = self.ema1226_1h_cache.loc[self.ema1226_1h_cache["date"] <= iso8601end].copy()
            elif self.exchange != Exchange.DUMMY:
                df_data = self.get_additional_df("1h", self.websocket_connection).copy()
                self.ema1226_1h_cache = df_data
            else:
                return False

            ta = TechnicalAnalysis(df_data, app=self)

            if "ema12" not in df_data:
                ta.add_ema(12)

            if "ema26" not in df_data:
                ta.add_ema(26)

            df_last = ta.get_df().copy().iloc[-1, :]
            df_last["bull"] = df_last["ema12"] > df_last["ema26"]

            return bool(df_last["bull"])
        except Exception:
            return False

    def is_6h_ema1226_bull(self, iso8601end: str = ""):
        try:
            if self.is_sim and isinstance(self.ema1226_1h_cache, pd.DataFrame):
                df_data = self.ema1226_6h_cache.loc[self.ema1226_6h_cache["date"] <= iso8601end].copy()
            elif self.exchange != Exchange.DUMMY:
                df_data = self.get_additional_df("6h", self.websocket_connection).copy()
                self.ema1226_6h_cache = df_data
            else:
                return False

            ta = TechnicalAnalysis(df_data, app=self)

            if "ema12" not in df_data:
                ta.add_ema(12)

            if "ema26" not in df_data:
                ta.add_ema(26)

            df_last = ta.get_df().copy().iloc[-1, :]
            df_last["bull"] = df_last["ema12"] > df_last["ema26"]

            return bool(df_last["bull"])
        except Exception:
            return False

    def is_1h_sma50200_bull(self, iso8601end: str = ""):
        # if periods adjusted and less than 200
        if self.adjusttotalperiods < 200:
            return False

        try:
            if self.is_sim and isinstance(self.sma50200_1h_cache, pd.DataFrame):
                df_data = self.sma50200_1h_cache.loc[self.sma50200_1h_cache["date"] <= iso8601end].copy()
            elif self.exchange != Exchange.DUMMY:
                df_data = self.get_additional_df("1h", self.websocket_connection).copy()
                self.sma50200_1h_cache = df_data
            else:
                return False

            ta = TechnicalAnalysis(df_data, app=self)

            if "sma50" not in df_data:
                ta.add_sma(50)

            if "sma200" not in df_data:
                ta.add_sma(200)

            df_last = ta.get_df().copy().iloc[-1, :]
            df_last["bull"] = df_last["sma50"] > df_last["sma200"]

            return bool(df_last["bull"])
        except Exception:
            return False

    def get_additional_df(self, short_granularity, websocket) -> pd.DataFrame:
        granularity = Granularity.convert_to_enum(short_granularity)

        idx, next_idx = (None, 0)
        for i in range(len(self.df_data)):
            if isinstance(self.df_data[i], list) and self.df_data[i][0] == short_granularity:
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
                    datetime.timestamp(datetime.utcnow()) - granularity.to_integer >= datetime.timestamp(df["date"].iloc[row])
                )
            ):
                df = self.get_historical_data(self.market, self.granularity, self.websocket_connection)
                row = -1
            else:
                # if ticker hasn't run yet or hasn't updated, return the original df
                if websocket is not None and self.ticker_date is None:
                    return df
                elif self.ticker_date is None or datetime.timestamp(  # if calling API multiple times, per iteration, ticker may not be updated yet
                    datetime.utcnow()
                ) - 60 <= datetime.timestamp(df["date"].iloc[row]):
                    return df
                elif row == -2:  # update the new row added for ticker if it is there
                    df.iloc[-1, df.columns.get_loc("low")] = self.ticker_price if self.ticker_price < df["low"].iloc[-1] else df["low"].iloc[-1]
                    df.iloc[-1, df.columns.get_loc("high")] = self.ticker_price if self.ticker_price > df["high"].iloc[-1] else df["high"].iloc[-1]
                    df.iloc[-1, df.columns.get_loc("close")] = self.ticker_price
                    df.iloc[-1, df.columns.get_loc("date")] = datetime.strptime(self.ticker_date, "%Y-%m-%d %H:%M:%S")
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
                                datetime.strptime(self.ticker_date, "%Y-%m-%d %H:%M:%S"),
                                df["market"].iloc[-1],
                                df["granularity"].iloc[-1],
                                (self.ticker_price if self.ticker_price < df["close"].iloc[-1] else df["close"].iloc[-1]),
                                (self.ticker_price if self.ticker_price > df["close"].iloc[-1] else df["close"].iloc[-1]),
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

        if not self.is_live:
            # not live, return None
            return None

        try:
            if self.exchange == Exchange.COINBASE:
                api = CBAuthAPI(self.api_key, self.api_secret, self.api_url, app=self)
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
                    "date": str(pd.DatetimeIndex(pd.to_datetime(last_order["created_at"]).dt.strftime("%Y-%m-%dT%H:%M:%S.%Z"))[0]),
                }
            elif self.exchange == Exchange.COINBASEPRO:
                api = CAuthAPI(self.api_key, self.api_secret, self.api_passphrase, self.api_url, app=self)
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
                    "date": str(pd.DatetimeIndex(pd.to_datetime(last_order["created_at"]).dt.strftime("%Y-%m-%dT%H:%M:%S.%Z"))[0]),
                }
            elif self.exchange == Exchange.KUCOIN:
                api = KAuthAPI(self.api_key, self.api_secret, self.api_passphrase, self.api_url, use_cache=self.usekucoincache, app=self)
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
                    "date": str(pd.DatetimeIndex(pd.to_datetime(last_order["created_at"]).dt.strftime("%Y-%m-%dT%H:%M:%S.%Z"))[0]),
                }
            elif self.exchange == Exchange.BINANCE:
                api = BAuthAPI(self.api_key, self.api_secret, self.api_url, recv_window=self.recv_window, app=self)
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
                    "date": str(pd.DatetimeIndex(pd.to_datetime(last_order["created_at"]).dt.strftime("%Y-%m-%dT%H:%M:%S.%Z"))[0]),
                }
            else:
                return None
        except Exception:
            return None

    def get_taker_fee(self):
        if not self.is_live and self.exchange == Exchange.COINBASE:
            return 0.006  # default lowest fee tier
        elif not self.is_live and self.exchange == Exchange.COINBASEPRO:
            return 0.005  # default lowest fee tier
        elif not self.is_live and self.exchange == Exchange.BINANCE:
            # https://www.binance.com/en/support/announcement/binance-launches-zero-fee-bitcoin-trading-10435147c55d4a40b64fcbf43cb46329
            # UPDATE: https://www.binance.com/en/support/announcement/updates-on-zero-fee-bitcoin-trading-busd-zero-maker-fee-promotion-be13a645cca643d28eab5b9b34f2dc36
            if self.get_market() in [
                "BTCTUSD"
            ]:
                return 0.0  # no fees for those pairs
            else:
                return 0.001  # default lowest fee tier
        elif not self.is_live and self.exchange == Exchange.KUCOIN:
            return 0.0015  # default lowest fee tier
        elif self.takerfee > -1.0:
            return self.takerfee
        elif self.exchange == Exchange.COINBASE:
            api = CBAuthAPI(self.api_key, self.api_secret, self.api_url, app=self)
            self.takerfee = api.get_taker_fee()
            return self.takerfee
        elif self.exchange == Exchange.COINBASEPRO:
            api = CAuthAPI(self.api_key, self.api_secret, self.api_passphrase, self.api_url, app=self)
            self.takerfee = api.get_taker_fee()
            return self.takerfee
        elif self.exchange == Exchange.BINANCE:
            api = BAuthAPI(self.api_key, self.api_secret, self.api_url, recv_window=self.recv_window, app=self)
            self.takerfee = api.get_taker_fee(self.get_market())
            return self.takerfee
        elif self.exchange == Exchange.KUCOIN:
            api = KAuthAPI(self.api_key, self.api_secret, self.api_passphrase, self.api_url, use_cache=self.usekucoincache, app=self)
            self.takerfee = api.get_taker_fee()
            return self.takerfee
        else:
            return 0.005

    def get_maker_fee(self):
        if not self.is_live and self.exchange == Exchange.COINBASE:
            return 0.004  # default lowest fee tier
        elif not self.is_live and self.exchange == Exchange.COINBASEPRO:
            return 0.005  # default lowest fee tier
        elif not self.is_live and self.exchange == Exchange.BINANCE:
            return 0.0  # default lowest fee tier
        elif not self.is_live and self.exchange == Exchange.KUCOIN:
            return 0.0015  # default lowest fee tier
        elif self.makerfee > -1.0:
            return self.makerfee
        elif self.exchange == Exchange.COINBASE:
            api = CBAuthAPI(self.api_key, self.api_secret, self.api_url, app=self)
            return api.get_maker_fee()
        elif self.exchange == Exchange.COINBASEPRO:
            api = CAuthAPI(self.api_key, self.api_secret, self.api_passphrase, self.api_url, app=self)
            return api.get_maker_fee()
        elif self.exchange == Exchange.BINANCE:
            api = BAuthAPI(self.api_key, self.api_secret, self.api_url, recv_window=self.recv_window, app=self)
            return api.get_maker_fee(self.get_market())
        elif self.exchange == Exchange.KUCOIN:
            api = KAuthAPI(self.api_key, self.api_secret, self.api_passphrase, self.api_url, use_cache=self.usekucoincache, app=self)
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
