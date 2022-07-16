#!/usr/bin/env python3
# encoding: utf-8

"""Python Crypto Bot consuming Coinbase Pro or Binance APIs"""

import functools
import json
import os
import sched
import signal
import sys
import time
from datetime import datetime, timedelta
import pandas as pd
from os.path import exists as file_exists

from models.AppState import AppState
from models.exchange.binance import WebSocketClient as BWebSocketClient
from models.exchange.coinbase_pro import WebSocketClient as CWebSocketClient
from models.exchange.ExchangesEnum import Exchange
from models.exchange.Granularity import Granularity
from models.exchange.kucoin import WebSocketClient as KWebSocketClient
from models.helper.LogHelper import Logger
from models.helper.MarginHelper import calculate_margin
from models.helper.TelegramBotHelper import TelegramBotHelper
from models.helper.TextBoxHelper import TextBox
from models.PyCryptoBot import PyCryptoBot
from models.PyCryptoBot import truncate as _truncate
from models.Stats import Stats
from models.TradingAccount import TradingAccount
from models.Strategy import Strategy
from views.TradingGraphs import TradingGraphs

app = PyCryptoBot()
account = TradingAccount(app)
Stats(app, account).show()
state = AppState(app, account)

if self.enable_pandas_ta is True:
    try:
        from models.Trading_myPta import TechnicalAnalysis

        self.state.trading_myPta = True
        self.state.pandas_ta_enabled = True
    except ImportError as myTrading_err:
        if file_exists("models/Trading_myPta.py"):
            raise ImportError(f"Custom Trading Error: {myTrading_err}")
        try:
            from models.Trading_Pta import TechnicalAnalysis

            self.state.pandas_ta_enabled = True
        except ImportError as err:
            raise ImportError(f"Pandas-ta is enabled, but an error occurred: {err}")
else:
    from models.Trading import TechnicalAnalysis

# minimal traceback
sys.tracebacklimit = 1

technical_analysis = None
state.init_last_action()

telegram_bot = TelegramBotHelper(app)

s = sched.scheduler(time.time, time.sleep)

pd.set_option("display.float_format", "{:.8f}".format)


def signal_handler(signum):
    if signum == 2:
        print("Please be patient while websockets terminate!")
        # Logger.debug(frame)
        return


def execute_job(
    sc=None,
    _app: PyCryptoBot = None,
    _state: AppState = None,
    _technical_analysis=None,
    _websocket=None,
    trading_data=pd.DataFrame(),
):
    """Trading bot job which runs at a scheduled interval"""

    df_last = None

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
                    Logger.info("Stopping _websocket...")
                    _websocket.close()

            time.sleep(30)
            controlstatus = self.telegram_bot.checkbotcontrolstatus()

        if controlstatus == "start":
            text_box = TextBox(80, 22)
            text_box.singleLine()
            text_box.center(f"Restarting Bot {self.market}")
            text_box.singleLine()
            Logger.debug("Restarting Bot.")
            # print(str(datetime.now()).format() + " - Bot has restarted")
            self.notify_telegram(f"{self.market} bot has restarted")
            self.telegram_bot.updatebotstatus("active")
            self.read_config(self.exchange)
            if self.websocket:
                Logger.info("Starting _websocket...")
                _websocket.start()

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
                _websocket.close()
                if self.exchange == Exchange.BINANCE:
                    _websocket = BWebSocketClient(
                        [app.market], self.granularity
                    )
                elif self.exchange == Exchange.COINBASEPRO:
                    _websocket = CWebSocketClient(
                        [app.market], self.granularity
                    )
                elif self.exchange == Exchange.KUCOIN:
                    _websocket = KWebSocketClient(
                        [app.market], self.granularity
                    )
                _websocket.start()
            self.setGranularity(self.granularity)
            list(map(s.cancel, s.queue))
            s.enter(
                5,
                1,
                execute_job,
                (sc, _app, _state, _technical_analysis, _websocket, trading_data),
            )
            # self.read_config(self.exchange)
            self.telegram_bot.updatebotstatus("active")
    else:
        # runs once at the start of a simulation
        if self.app_started:
            if self.simstart_date is not None:
                self.state.iterations = trading_data.index.get_loc(
                    str(self.get_date_from_iso8601_str(self.simstart_date))
                )

            self.app_started = False

    # reset _websocket every 23 hours if applicable
    if self.websocket and not self.is_sim:
        if _websocket.time_elapsed > 82800:
            Logger.info("Websocket requires a restart every 23 hours!")
            Logger.info("Stopping _websocket...")
            _websocket.close()
            Logger.info("Starting _websocket...")
            _websocket.start()
            Logger.info("Restarting job in 30 seconds...")
            s.enter(
                30,
                1,
                execute_job,
                (sc, _app, _state, _technical_analysis, _websocket, trading_data),
            )

    # increment self.state.iterations
    self.state.iterations = self.state.iterations + 1

    if not self.is_sim:
        # check if data exists or not and only refresh at candle close.
        if len(trading_data) == 0 or (
            len(trading_data) > 0
            and (
                datetime.timestamp(datetime.utcnow()) - self.granularity.to_integer
                >= datetime.timestamp(
                    trading_data.iloc[
                        self.state.closed_candle_row, trading_data.columns.get_loc("date")
                    ]
                )
            )
        ):
            trading_data = self.get_historical_data(
                self.market, self.granularity, _websocket
            )
            self.state.closed_candle_row = -1
            self.price = float(trading_data.iloc[-1, trading_data.columns.get_loc("close")])

        else:
            # set time and self.price with ticker data and add/update current candle
            ticker = self.get_ticker(self.market, _websocket)
            # if 0, use last close value as self.price
            self.price = trading_data["close"].iloc[-1] if ticker[1] == 0 else ticker[1]
            self.ticker_date = ticker[0]
            self.ticker_price = ticker[1]

            if self.state.closed_candle_row == -2:
                trading_data.iloc[-1, trading_data.columns.get_loc("low")] = (
                    self.price
                    if self.price < trading_data["low"].iloc[-1]
                    else trading_data["low"].iloc[-1]
                )
                trading_data.iloc[-1, trading_data.columns.get_loc("high")] = (
                    self.price
                    if self.price > trading_data["high"].iloc[-1]
                    else trading_data["high"].iloc[-1]
                )
                trading_data.iloc[-1, trading_data.columns.get_loc("close")] = self.price
                trading_data.iloc[
                    -1, trading_data.columns.get_loc("date")
                ] = datetime.strptime(ticker[0], "%Y-%m-%d %H:%M:%S")
                tsidx = pd.DatetimeIndex(trading_data["date"])
                trading_data.set_index(tsidx, inplace=True)
                trading_data.index.name = "ts"
            else:
                # not sure what this code is doing as it has a bug.
                # i've added a websocket check and added a try..catch block

                if self.websocket:
                    try:
                        trading_data.loc[len(trading_data.index)] = [
                            datetime.strptime(ticker[0], "%Y-%m-%d %H:%M:%S"),
                            trading_data["market"].iloc[-1],
                            trading_data["granularity"].iloc[-1],
                            (self.price if self.price < trading_data["close"].iloc[-1] else trading_data["close"].iloc[-1]),
                            (self.price if self.price > trading_data["close"].iloc[-1] else trading_data["close"].iloc[-1]),
                            trading_data["close"].iloc[-1],
                            self.price,
                            trading_data["volume"].iloc[-1]
                        ]

                        tsidx = pd.DatetimeIndex(trading_data["date"])
                        trading_data.set_index(tsidx, inplace=True)
                        trading_data.index.name = "ts"
                        self.state.closed_candle_row = -2
                    except Exception:
                        pass

    else:
        df_last = self.get_interval(trading_data, self.state.iterations)
        self.price = df_last["close"][0]

        if len(trading_data) == 0:
            return None

    # analyse the market data
    if self.is_sim and len(trading_data.columns) > 8:
        df = trading_data

        # if smartswitch then get the market data using new granularity
        if self.sim_smartswitch:
            df_last = self.get_interval(df, self.state.iterations)
            if len(self.df_last.index.format()) > 0:
                if self.simstart_date is not None:
                    start_date = self.get_date_from_iso8601_str(self.simstart_date)
                else:
                    start_date = self.get_date_from_iso8601_str(
                        str(df.head(1).index.format()[0])
                    )

                if self.simend_date is not None:
                    if self.simend_date == "now":
                        end_date = self.get_date_from_iso8601_str(str(datetime.now()))
                    else:
                        end_date = self.get_date_from_iso8601_str(self.simend_date)
                else:
                    end_date = self.get_date_from_iso8601_str(
                        str(df.tail(1).index.format()[0])
                    )

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
                    except:  # pylint: disable=bare-except
                        simDate += timedelta(seconds=self.granularity.value[0])

                if (
                    self.get_date_from_iso8601_str(str(simDate)).isoformat()
                    == self.get_date_from_iso8601_str(str(self.state.last_df_index)).isoformat()
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
        _technical_analysis = TechnicalAnalysis(trading_data, len(trading_data))
        _technical_analysis.addAll()
        df = _technical_analysis.getDataFrame()

    if self.is_sim:
        df_last = self.get_interval(df, self.state.iterations)
    else:
        df_last = self.get_interval(df)

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

        if not self.is_sim or (
            self.is_sim and not self.simresultonly
        ):
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

        self.setGranularity(Granularity.FIVE_MINUTES)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, execute_job, (sc, _app, _state, _technical_analysis, _websocket))

    if (
        (last_api_call_datetime.seconds > 60 or self.is_sim)
        and self.smart_switch == 1
        and self.sell_smart_switch == 1
        and self.granularity == Granularity.FIVE_MINUTES
        and self.state.last_action == "SELL"
    ):

        if not self.is_sim or (
            self.is_sim and not self.simresultonly
        ):
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

        self.setGranularity(Granularity.ONE_HOUR)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, execute_job, (sc, _app, _state, _technical_analysis, _websocket))

    # use actual sim mode date to check smartchswitch
    if (
        (last_api_call_datetime.seconds > 60 or self.is_sim)
        and self.smart_switch == 1
        and self.granularity == Granularity.ONE_HOUR
        and self.is1hEMA1226Bull(current_sim_date, _websocket) is True
        and self.is6hEMA1226Bull(current_sim_date, _websocket) is True
    ):
        if not self.is_sim or (
            self.is_sim and not self.simresultonly
        ):
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

        self.setGranularity(Granularity.FIFTEEN_MINUTES)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, execute_job, (sc, _app, _state, _technical_analysis, _websocket))

    # use actual sim mode date to check smartchswitch
    if (
        (last_api_call_datetime.seconds > 60 or self.is_sim)
        and self.smart_switch == 1
        and self.granularity == Granularity.FIFTEEN_MINUTES
        and self.is1hEMA1226Bull(current_sim_date, _websocket) is False
        and self.is6hEMA1226Bull(current_sim_date, _websocket) is False
    ):
        if not self.is_sim or (
            self.is_sim and not self.simresultonly
        ):
            Logger.info(
                "*** smart switch from granularity 900 (15 min) to 3600 (1 hour) ***"
            )

        if self.is_sim:
            self.sim_smartswitch = True

        if not self.telegramtradesonly:
            self.notify_telegram(
                f"{self.market} smart switch from granularity 900 (15 min) to 3600 (1 hour)"
            )

        self.setGranularity(Granularity.ONE_HOUR)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, execute_job, (sc, _app, _state, _technical_analysis, _websocket))

    if (
        self.exchange == Exchange.BINANCE
        and self.granularity == Granularity.ONE_DAY
    ):
        if len(df) < 250:
            # data frame should have 250 rows, if not retry
            Logger.error(f"error: data frame length is < 250 ({str(len(df))})")
            list(map(s.cancel, s.queue))
            s.enter(
                300, 1, execute_job, (sc, _app, _state, _technical_analysis, _websocket)
            )
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
                list(map(s.cancel, s.queue))
                s.enter(
                    300,
                    1,
                    execute_job,
                    (sc, _app, _state, _technical_analysis, _websocket),
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
            if self.state.action == "check_action" and self.state.last_action == "BUY":
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

                if self.enableexitaftersell and self.startmethod not in ("standard",):
                    sys.exit(0)

        if self.price < 0.000001:
            raise Exception(
                f"{self.market} is unsuitable for trading, quote self.price is less than 0.000001!"
            )

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
                goldencross = self.is1hSMA50200Bull(current_sim_date, _websocket)

        # candlestick detection
        hammer = bool(self.df_last["hammer"].values[0])
        inverted_hammer = bool(self.df_last["inverted_hammer"].values[0])
        hanging_man = bool(self.df_last["hanging_man"].values[0])
        shooting_star = bool(self.df_last["shooting_star"].values[0])
        three_white_soldiers = bool(self.df_last["three_white_soldiers"].values[0])
        three_black_crows = bool(self.df_last["three_black_crows"].values[0])
        morning_star = bool(self.df_last["morning_star"].values[0])
        evening_star = bool(self.df_last["evening_star"].values[0])
        three_line_strike = bool(self.df_last["three_line_strike"].values[0])
        abandoned_baby = bool(self.df_last["abandoned_baby"].values[0])
        morning_doji_star = bool(self.df_last["morning_doji_star"].values[0])
        evening_doji_star = bool(self.df_last["evening_doji_star"].values[0])
        two_black_gapping = bool(self.df_last["two_black_gapping"].values[0])

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
                _app, _state, sdf, sdf.index.get_loc(str(current_sim_date)) + 1
            )
        else:
            strategy = Strategy(_app, _state, df)

        trailing_action_logtext = ""

        # determine current action, indicatorvalues will be empty if custom Strategy are disabled or it's debug is False
        self.state.action, indicatorvalues = strategy.get_action(
            _state, self.price, current_sim_date, _websocket
        )

        immediate_action = False
        margin, profit, sell_fee, change_pcnt_high = 0, 0, 0, 0

        # Reset the TA so that the last record is the current sim date
        # To allow for calculations to be done on the sim date being processed
        if self.is_sim:
            trading_dataCopy = (
                trading_data[trading_data["date"] <= current_sim_date]
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
                _app,
                _state,
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
            self.state.action != "WAIT" and strategy.is_wait_trigger(margin, goldencross)
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
            ) = strategy.check_trailing_buy(_state, self.price)
        # If sell signal, save the self.price and check for decrease/increase before selling.
        if self.state.action == "SELL" and immediate_action is not True:
            (
                self.state.action,
                self.state.trailing_sell,
                trailing_action_logtext,
                immediate_action,
            ) = strategy.check_trailing_sell(_state, self.price)

        if self.enableimmediatebuy:
            if self.state.action == "BUY":
                immediate_action = True

        if not self.is_sim and self.enable_telegram_bot_control:
            manual_buy_sell = self.telegram_bot.check_manual_buy_sell()
            if not manual_buy_sell == "WAIT":
                self.state.action = manual_buy_sell
                immediate_action = True

        bullbeartext = ""
        if (
            self.disablebullonly is True
            or self.adjust_total_periods < 200
            or df_last["sma50"].values[0] == df_last["sma200"].values[0]
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
            truncate = functools.partial(_truncate, n=precision)

            if immediate_action:
                self.price_text = str(self.price)
            else:
                self.price_text = "Close: " + str(self.price)
            ema_text = ""
            if self.disablebuyema is False:
                ema_text = self.compare(
                    df_last["ema12"].values[0],
                    df_last["ema26"].values[0],
                    "EMA12/26",
                    precision,
                )

            macd_text = ""
            if self.disablebuymacd is False:
                macd_text = self.compare(
                    df_last["macd"].values[0],
                    df_last["signal"].values[0],
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

            self.state.eri_text = ""
            if self.disablebuyelderray is False:
                if elder_ray_buy is True:
                    self.state.eri_text = "ERI: buy | "
                elif elder_ray_sell is True:
                    self.state.eri_text = "ERI: sell | "
                else:
                    self.state.eri_text = "ERI: | "
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

            obv_prefix = ""
            obv_suffix = ""
            if self.disablebuyobv is False:
                if float(obv_pc) > 0:
                    obv_prefix = "^ "
                    obv_suffix = " ^ | "
                elif float(obv_pc) < 0:
                    obv_prefix = "v "
                    obv_suffix = " v | "
                else:
                    obv_suffix = " | "

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
                            + self.state.eri_text
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
                            + " CURR self.price is "
                            + str(
                                round(
                                    ((self.price - df["close"].max()) / df["close"].max())
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
                            + self.state.eri_text
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
                            + " CURR self.price is "
                            + str(round(((self.price - df_high) / df_high) * 100, 2))
                            + "% "
                            + "away from DF HIGH | Range: "
                            + str(
                                df.iloc[self.state.iterations - self.adjust_total_periods, 0]
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
                            + self.state.eri_text
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
                            + " CURR self.price is "
                            + str(
                                round(
                                    ((self.price - df["close"].max()) / df["close"].max())
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
                            + self.state.eri_text
                            + self.state.action
                            + " | DF HIGH: "
                            + str(df_high)
                            + " | "
                            + "DF LOW: "
                            + str(df_low)
                            + " | SWING: "
                            + str(round(((df_high - df_low) / df_low) * 100, 2))
                            + "%"
                            + " CURR self.price is "
                            + str(round(((self.price - df_high) / df_high) * 100, 2))
                            + "% "
                            + "away from DF HIGH | Range: "
                            + str(
                                df.iloc[self.state.iterations - self.adjust_total_periods, 0]
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
                        + str(round(self.price - self.state.last_buy_price, precision))
                        + ")"
                    )
                    if self.is_sim:
                        # save margin for Summary if open trade
                        self.state.open_trade_margin = margin_text

                if not self.is_sim or (
                    self.is_sim and not self.simresultonly
                ):
                    Logger.info(output_text)

                if self.enableml:
                    # Seasonal Autoregressive Integrated Moving Average (ARIMA) model (ML prediction for 3 intervals from now)
                    if not self.is_sim:
                        try:
                            prediction = (
                                _technical_analysis.arima_model_prediction(
                                    int(self.granularity.to_integer / 60) * 3
                                )
                            )  # 3 intervals from now
                            Logger.info(
                                f"Seasonal ARIMA model predicts the closing self.price will be {str(round(prediction[1], 2))} at {prediction[0]} (delta: {round(prediction[1] - self.price, 2)})"
                            )
                        # pylint: disable=bare-except
                        except:
                            pass

                if self.state.last_action == "BUY":
                    # display support, resistance and fibonacci levels
                    if not self.is_sim or (
                        self.is_sim and not self.simresultonly
                    ):
                        Logger.info(
                            _technical_analysis.print_sr_fib_levels(
                                self.price
                            )
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
                    Logger.debug(f'macd: {truncate(float(self.df_last["macd"].values[0]))}')
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
                text_box.line("Iteration", str(self.state.iterations) + bullbeartext)
                text_box.line("Timestamp", str(self.df_last.index.format()[0]))
                text_box.singleLine()
                text_box.line("Close", truncate(self.price))
                text_box.line("EMA12", truncate(float(self.df_last["ema12"].values[0])))
                text_box.line("EMA26", truncate(float(self.df_last["ema26"].values[0])))
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

                text_box.line("SMA20", truncate(float(self.df_last["sma20"].values[0])))
                text_box.line("SMA200", truncate(float(self.df_last["sma200"].values[0])))
                text_box.singleLine()
                text_box.line("MACD", truncate(float(self.df_last["macd"].values[0])))
                text_box.line("Signal", truncate(float(self.df_last["signal"].values[0])))
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
                    except:
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
                                    f"{formatted_current_df_index} | {self.market} | {self.print_granularity()} | {price_text} | BUY"
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
                        self.state.last_buy_size = float(self.account.quote_balance_before)

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
                            resp = self.marketBuy(
                                self.market,
                                self.state.last_buy_size,
                                self.get_buy_percent(),
                            )
                            resp_error = 0
                            # Logger.debug(resp)
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
                                    + self.price_text
                                )

                            else:
                                # set variable to trigger to check trade on next iteration
                                self.state.action = "check_action"
                                Logger.info(
                                    f"{self.market} - Error occurred while checking balance after BUY. Last transaction check will happen shortly."
                                )

                                if not self.disable_telegram_error_msgs:
                                    self.notify_telegram(
                                        self.market
                                        + " - Error occurred while checking balance after BUY. Last transaction check will happen shortly."
                                    )

                        else:  # there was a response error
                            # only attempt BUY 3 times before exception to prevent continuous loop
                            self.state.trade_error_cnt += 1
                            if self.state.trade_error_cnt >= 2:  # 3 attempts made
                                raise Exception(
                                    f"Trade Error: BUY transaction attempted 3 times. Check log for errors"
                                )

                            # set variable to trigger to check trade on next iteration
                            self.state.action = "check_action"
                            self.state.last_action = None

                            Logger.warning(
                                f"API Error: Unable to place buy order for {self.market}."
                            )
                            if not self.disable_telegram_error_msgs:
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
                    if self.state.last_buy_size == 0 and self.state.last_buy_filled == 0:
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
                    self.state.buy_sum = self.state.buy_sum + self.state.last_buy_size
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
                        + str(_truncate(self.state.last_buy_size, 4))
                    )

                    if not self.is_verbose:
                        if not self.is_sim or (
                            self.is_sim and not self.simresultonly
                        ):
                            Logger.info(
                                f"{formatted_current_df_index} | {self.market} | {self.print_granularity()} | {price_text} | BUY"
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
                            Logger.info(f" Fibonacci Retracement Levels:{str(bands)}")

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
                                    "Base": float(self.state.last_buy_size) / float(self.price),
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
                            Logger.info(f" Fibonacci Retracement Levels:{str(bands)}")

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
                            f"{formatted_current_df_index} | {self.market} | {self.print_granularity()} | {price_text} | SELL"
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
                    except:
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
                        resp = self.marketSell(
                            self.market,
                            baseamounttosell,
                            self.get_sell_percent(),
                        )
                        resp_error = 0
                        # Logger.debug(resp)
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
                            self.state.tsl_trigger = float(self.trailing_stop_loss_trigger)
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
                                + self.price_text
                                + " (margin: "
                                + margin_text
                                + ", delta: "
                                + str(round(self.price - self.state.last_buy_price, precision))
                                + ")"
                            )

                            self.telegram_bot.closetrade(
                                str(self.get_date_from_iso8601_str(str(datetime.now()))),
                                self.price_text,
                                margin_text,
                            )

                            if self.enableexitaftersell and self.startmethod not in (
                                "standard",
                                "telegram",
                            ):
                                sys.exit(0)

                        else:
                            # set variable to trigger to check trade on next iteration
                            self.state.action = "check_action"

                            Logger.info(
                                self.market
                                + " - Error occurred while checking balance after SELL. Last transaction check will happen shortly."
                            )

                            if not self.disable_telegram_error_msgs:
                                self.notify_telegram(
                                    self.market
                                    + " - Error occurred while checking balance after SELL. Last transaction check will happen shortly."
                                )

                    else:  # there was an error
                        # only attempt SELL 3 times before exception to prevent continuous loop
                        self.state.trade_error_cnt += 1
                        if self.state.trade_error_cnt >= 2:  # 3 attempts made
                            raise Exception(
                                f"Trade Error: SELL transaction attempted 3 times. Check log for errors."
                            )
                        # set variable to trigger to check trade on next iteration
                        self.state.action = "check_action"
                        self.state.last_action = None

                        Logger.warning(
                            f"API Error: Unable to place SELL order for {self.market}."
                        )
                        if not self.disable_telegram_error_msgs:
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
                    self.state.sell_sum = self.state.sell_sum + self.state.last_sell_size

                    # Added to track profit and loss margins during sim runs
                    self.state.margintracker += float(margin)
                    self.state.profitlosstracker += float(profit)
                    self.state.feetracker += float(sell_fee)
                    self.state.buy_tracker += float(self.state.last_buy_size)

                    self.notify_telegram(
                        self.market
                        + " ("
                        + self.print_granularity()
                        + ") "
                        + str(current_sim_date)
                        + "\n - TEST SELL at "
                        + str(self.price_text)
                        + " (margin: "
                        + margin_text
                        + ", delta: "
                        + str(round(self.price - self.state.last_buy_price, precision))
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
                        self.state.tsl_trigger = float(self.trailing_stop_loss_trigger)

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

                if self.getConfig() != "":
                    simulation["config"] = self.getConfig()

                if not self.simresultonly:
                    Logger.info(f"\nSimulation Summary: {self.market}")

                tradesfile = self.getTradesFile()

                if self.is_verbose:
                    Logger.info("\n" + str(self.trade_tracker))
                    start = str(df.head(1).index.format()[0]).replace(":", ".")
                    end = str(df.tail(1).index.format()[0]).replace(":", ".")
                    filename = (
                        f"{self.market} {str(start)} - {str(end)}_{tradesfile}"
                    )

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
                    self.state.sell_sum = self.state.sell_sum + self.state.last_sell_size

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
                    simulation["data"]["first_trade"]["size"] = self.state.first_buy_size

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
                    f"Simulation Summary\n"
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
                    self.telegram_bot.removeactivebot()

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
                    f"{now} | {self.market}{bullbeartext} | {self.print_granularity()} | Current self.price: {str(self.price)} {trailing_action_logtext} | Margin: {str(margin)} | Profit: {str(profit)}"
                )
            else:
                Logger.info(
                    f'{now} | {self.market}{bullbeartext} | {self.print_granularity()} | Current self.price: {str(self.price)}{trailing_action_logtext} | {str(round(((self.price-df["close"].max()) / df["close"].max())*100, 2))}% from DF HIGH'
                )
                self.telegram_bot.addinfo(
                    f'{now} | {self.market}{bullbeartext} | {self.print_granularity()} | Current self.price: {str(self.price)}{trailing_action_logtext} | {str(round(((self.price-df["close"].max()) / df["close"].max())*100, 2))}% from DF HIGH',
                    round(self.price, 4),
                    str(round(df["close"].max(), 4)),
                    str(
                        round(
                            ((self.price - df["close"].max()) / df["close"].max()) * 100, 2
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
                self.telegram_bot.addmargin(
                    str(_truncate(margin, 4) + "%")
                    if self.state.in_open_trade is True
                    else " ",
                    str(_truncate(profit, 2)) if self.state.in_open_trade is True else " ",
                    self.price,
                    change_pcnt_high,
                    self.state.action,
                )

            # Update the watchdog_ping
            self.telegram_bot.updatewatchdogping()

            # decrement ignored iteration
            if self.is_sim and self.smart_switch:
                self.state.iterations = self.state.iterations - 1

        # if live but not websockets
        if not self.disabletracker and self.is_live and not self.websocket:
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
                    list(map(s.cancel, s.queue))
                    s.enter(
                        0,
                        1,
                        execute_job,
                        (sc, _app, _state, _technical_analysis, None, df),
                    )
                else:
                    # slow processing
                    list(map(s.cancel, s.queue))
                    s.enter(
                        1,
                        1,
                        execute_job,
                        (sc, _app, _state, _technical_analysis, None, df),
                    )

        else:
            list(map(s.cancel, s.queue))
            if (
                self.websocket
                and _websocket is not None
                and (
                    isinstance(_websocket.tickers, pd.DataFrame)
                    and len(_websocket.tickers) == 1
                )
                and (
                    isinstance(_websocket.candles, pd.DataFrame)
                    and len(_websocket.candles) == self.adjust_total_periods
                )
            ):
                # poll every 5 seconds (_websocket)
                s.enter(
                    5,
                    1,
                    execute_job,
                    (sc, _app, _state, _technical_analysis, _websocket, trading_data),
                )
            else:
                if self.websocket and not self.is_sim:
                    # poll every 15 seconds (waiting for _websocket)
                    s.enter(
                        15,
                        1,
                        execute_job,
                        (
                            sc,
                            _app,
                            _state,
                            _technical_analysis,
                            _websocket,
                            trading_data,
                        ),
                    )
                else:
                    # poll every 1 minute (no _websocket)
                    s.enter(
                        60,
                        1,
                        execute_job,
                        (
                            sc,
                            _app,
                            _state,
                            _technical_analysis,
                            _websocket,
                            trading_data,
                        ),
                    )


def main():
    try:
        _websocket = None
        message = "Starting "
        if self.exchange == Exchange.COINBASEPRO:
            message += "Coinbase Pro bot"
            if self.websocket and not self.is_sim:
                print("Opening websocket to Coinbase Pro...")
                _websocket = CWebSocketClient([app.market], self.granularity)
                _websocket.start()
        elif self.exchange == Exchange.BINANCE:
            message += "Binance bot"
            if self.websocket and not self.is_sim:
                print("Opening websocket to Binance...")
                _websocket = BWebSocketClient([app.market], self.granularity)
                _websocket.start()
        elif self.exchange == Exchange.KUCOIN:
            message += "Kucoin bot"
            if self.websocket and not self.is_sim:
                print("Opening websocket to Kucoin...")
                _websocket = KWebSocketClient([app.market], self.granularity)
                _websocket.start()

        smartswitchstatus = "enabled" if self.smart_switch else "disabled"
        message += f" for {self.market} using granularity {self.print_granularity()}. Smartswitch {smartswitchstatus}"

        if self.startmethod in ("standard", "telegram"):
            self.notify_telegram(message)

        # initialise and start application
        trading_data = self.startApp(app, account, self.state.last_action)

        if self.is_sim and self.simend_date:
            try:
                # if simend_date is set, then remove trailing data points
                trading_data = trading_data[trading_data["date"] <= self.simend_date]
            except Exception:
                pass

        def runApp(_websocket, _trading_data):
            # run the first job immediately after starting
            if self.is_sim:
                execute_job(
                    s, app, state, technical_analysis, _websocket, _trading_data
                )
            else:
                execute_job(
                    s, app, state, technical_analysis, _websocket, pd.DataFrame()
                )

            s.run()

        try:
            runApp(_websocket, trading_data)
        except (KeyboardInterrupt, SystemExit):
            raise
        except (BaseException, Exception) as e:  # pylint: disable=broad-except
            if self.autorestart:
                # Wait 30 second and try to relaunch application
                time.sleep(30)
                Logger.critical(f"Restarting application after exception: {repr(e)}")

                if not self.disable_telegram_error_msgs:
                    self.notify_telegram(
                        f"Auto restarting bot for {self.market} after exception: {repr(e)}"
                    )

                # Cancel the events queue
                map(s.cancel, s.queue)

                # Restart the app
                runApp(_websocket)
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
            except:
                pass
            if self.websocket and not self.is_sim:
                _websocket.close()
            sys.exit(0)
        except SystemExit:
            # pylint: disable=protected-access
            os._exit(0)
    except (BaseException, Exception) as e:  # pylint: disable=broad-except
        # catch all not managed exceptions and send a Telegram message if configured
        if not self.disable_telegram_error_msgs:
            self.notify_telegram(f"Bot for {self.market} got an exception: {repr(e)}")
            try:
                self.telegram_bot.removeactivebot()
            except Exception as e:
                pass
        Logger.critical(repr(e))
        # pylint: disable=protected-access
        os._exit(0)
        # raise


if __name__ == "__main__":
    if sys.version_info < (3, 6, 0):
        sys.stderr.write("You need python 3.6 or higher to run this script\n")
        exit(1)

    main()
