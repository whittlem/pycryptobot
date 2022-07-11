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

if app.enable_pandas_ta is True:
    try:
        from models.Trading_myPta import TechnicalAnalysis

        state.trading_myPta = True
        state.pandas_ta_enabled = True
    except ImportError as myTrading_err:
        if file_exists("models/Trading_myPta.py"):
            raise ImportError(f"Custom Trading Error: {myTrading_err}")
        try:
            from models.Trading_Pta import TechnicalAnalysis

            state.pandas_ta_enabled = True
        except ImportError as err:
            raise ImportError(f"Pandas-ta is enabled, but an error occurred: {err}")
else:
    from models.Trading import TechnicalAnalysis

# minimal traceback
sys.tracebacklimit = 1

technical_analysis = None
state.initLastAction()

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

    if app.is_live:
        state.account.mode = "live"
    else:
        state.account.mode = "test"

    # This is used to control some API calls when using websockets
    last_api_call_datetime = datetime.now() - _state.last_api_call_datetime
    if last_api_call_datetime.seconds > 60:
        _state.last_api_call_datetime = datetime.now()

    # This is used by the telegram bot
    # If it not enabled in config while will always be False
    if not _app.is_sim:
        controlstatus = telegram_bot.checkbotcontrolstatus()
        while controlstatus == "pause" or controlstatus == "paused":
            if controlstatus == "pause":
                text_box = TextBox(80, 22)
                text_box.singleLine()
                text_box.center(f"Pausing Bot {_app.market}")
                text_box.singleLine()
                Logger.debug("Pausing Bot.")
                print(str(datetime.now()).format() + " - Bot is paused")
                _app.notify_telegram(f"{_app.market} bot is paused")
                telegram_bot.updatebotstatus("paused")
                if _app.websocket:
                    Logger.info("Stopping _websocket...")
                    _websocket.close()

            time.sleep(30)
            controlstatus = telegram_bot.checkbotcontrolstatus()

        if controlstatus == "start":
            text_box = TextBox(80, 22)
            text_box.singleLine()
            text_box.center(f"Restarting Bot {_app.market}")
            text_box.singleLine()
            Logger.debug("Restarting Bot.")
            # print(str(datetime.now()).format() + " - Bot has restarted")
            _app.notify_telegram(f"{_app.market} bot has restarted")
            telegram_bot.updatebotstatus("active")
            _app.read_config(_app.exchange)
            if _app.websocket:
                Logger.info("Starting _websocket...")
                _websocket.start()

        if controlstatus == "exit":
            text_box = TextBox(80, 22)
            text_box.singleLine()
            text_box.center(f"Closing Bot {_app.market}")
            text_box.singleLine()
            Logger.debug("Closing Bot.")
            _app.notify_telegram(f"{_app.market} bot is stopping")
            telegram_bot.removeactivebot()
            sys.exit(0)

        if controlstatus == "reload":
            text_box = TextBox(80, 22)
            text_box.singleLine()
            text_box.center(f"Reloading config parameters {_app.market}")
            text_box.singleLine()
            Logger.debug("Reloading config parameters.")
            _app.read_config(_app.exchange)
            if _app.websocket:
                _websocket.close()
                if _app.exchange == Exchange.BINANCE:
                    _websocket = BWebSocketClient(
                        [app.market], app.granularity
                    )
                elif _app.exchange == Exchange.COINBASEPRO:
                    _websocket = CWebSocketClient(
                        [app.market], app.granularity
                    )
                elif _app.exchange == Exchange.KUCOIN:
                    _websocket = KWebSocketClient(
                        [app.market], app.granularity
                    )
                _websocket.start()
            _app.setGranularity(_app.granularity)
            list(map(s.cancel, s.queue))
            s.enter(
                5,
                1,
                execute_job,
                (sc, _app, _state, _technical_analysis, _websocket, trading_data),
            )
            # _app.read_config(_app.exchange)
            telegram_bot.updatebotstatus("active")
    else:
        # runs once at the start of a simulation
        if _app.app_started:
            if _app.simstart_date is not None:
                _state.iterations = trading_data.index.get_loc(
                    str(_app.get_date_from_iso8601_str(_app.simstart_date))
                )

            _app.app_started = False

    # reset _websocket every 23 hours if applicable
    if _app.websocket and not _app.is_sim:
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

    # increment _state.iterations
    _state.iterations = _state.iterations + 1

    if not _app.is_sim:
        # check if data exists or not and only refresh at candle close.
        if len(trading_data) == 0 or (
            len(trading_data) > 0
            and (
                datetime.timestamp(datetime.utcnow()) - _app.granularity.to_integer
                >= datetime.timestamp(
                    trading_data.iloc[
                        _state.closed_candle_row, trading_data.columns.get_loc("date")
                    ]
                )
            )
        ):
            trading_data = _app.get_historical_data(
                _app.market, _app.granularity, _websocket
            )
            _state.closed_candle_row = -1
            price = float(trading_data.iloc[-1, trading_data.columns.get_loc("close")])

        else:
            # set time and price with ticker data and add/update current candle
            ticker = _app.get_ticker(_app.market, _websocket)
            # if 0, use last close value as price
            price = trading_data["close"].iloc[-1] if ticker[1] == 0 else ticker[1]
            _app.ticker_date = ticker[0]
            _app.ticker_price = ticker[1]

            if _state.closed_candle_row == -2:
                trading_data.iloc[-1, trading_data.columns.get_loc("low")] = (
                    price
                    if price < trading_data["low"].iloc[-1]
                    else trading_data["low"].iloc[-1]
                )
                trading_data.iloc[-1, trading_data.columns.get_loc("high")] = (
                    price
                    if price > trading_data["high"].iloc[-1]
                    else trading_data["high"].iloc[-1]
                )
                trading_data.iloc[-1, trading_data.columns.get_loc("close")] = price
                trading_data.iloc[
                    -1, trading_data.columns.get_loc("date")
                ] = datetime.strptime(ticker[0], "%Y-%m-%d %H:%M:%S")
                tsidx = pd.DatetimeIndex(trading_data["date"])
                trading_data.set_index(tsidx, inplace=True)
                trading_data.index.name = "ts"
            else:
                # not sure what this code is doing as it has a bug.
                # i've added a websocket check and added a try..catch block

                if _app.websocket:
                    try:
                        trading_data.loc[len(trading_data.index)] = [
                            datetime.strptime(ticker[0], "%Y-%m-%d %H:%M:%S"),
                            trading_data["market"].iloc[-1],
                            trading_data["granularity"].iloc[-1],
                            (price if price < trading_data["close"].iloc[-1] else trading_data["close"].iloc[-1]),
                            (price if price > trading_data["close"].iloc[-1] else trading_data["close"].iloc[-1]),
                            trading_data["close"].iloc[-1],
                            price,
                            trading_data["volume"].iloc[-1]
                        ]

                        tsidx = pd.DatetimeIndex(trading_data["date"])
                        trading_data.set_index(tsidx, inplace=True)
                        trading_data.index.name = "ts"
                        _state.closed_candle_row = -2
                    except Exception:
                        pass

    else:
        df_last = _app.get_interval(trading_data, _state.iterations)
        price = df_last["close"][0]

        if len(trading_data) == 0:
            return None

    # analyse the market data
    if _app.is_sim and len(trading_data.columns) > 8:
        df = trading_data

        # if smartswitch then get the market data using new granularity
        if _app.sim_smartswitch:
            df_last = _app.get_interval(df, _state.iterations)
            if len(self.df_last.index.format()) > 0:
                if _app.simstart_date is not None:
                    start_date = _app.get_date_from_iso8601_str(_app.simstart_date)
                else:
                    start_date = _app.get_date_from_iso8601_str(
                        str(df.head(1).index.format()[0])
                    )

                if _app.simend_date is not None:
                    if _app.simend_date == "now":
                        end_date = _app.get_date_from_iso8601_str(str(datetime.now()))
                    else:
                        end_date = _app.get_date_from_iso8601_str(_app.simend_date)
                else:
                    end_date = _app.get_date_from_iso8601_str(
                        str(df.tail(1).index.format()[0])
                    )

                simDate = _app.get_date_from_iso8601_str(str(_state.last_df_index))

                trading_data = _app.get_smart_switch_historical_data_chained(
                    _app.market,
                    _app.granularity,
                    str(start_date),
                    str(end_date),
                )

                if _app.granularity == Granularity.ONE_HOUR:
                    simDate = _app.get_date_from_iso8601_str(str(simDate))
                    sim_rounded = pd.Series(simDate).dt.round("60min")
                    simDate = sim_rounded[0]
                elif _app.granularity == Granularity.FIFTEEN_MINUTES:
                    simDate = _app.get_date_from_iso8601_str(str(simDate))
                    sim_rounded = pd.Series(simDate).dt.round("15min")
                    simDate = sim_rounded[0]
                elif _app.granularity == Granularity.FIVE_MINUTES:
                    simDate = _app.get_date_from_iso8601_str(str(simDate))
                    sim_rounded = pd.Series(simDate).dt.round("5min")
                    simDate = sim_rounded[0]

                dateFound = False
                while dateFound == False:
                    try:
                        _state.iterations = trading_data.index.get_loc(str(simDate)) + 1
                        dateFound = True
                    except:  # pylint: disable=bare-except
                        simDate += timedelta(seconds=_app.granularity.value[0])

                if (
                    _app.get_date_from_iso8601_str(str(simDate)).isoformat()
                    == _app.get_date_from_iso8601_str(str(_state.last_df_index)).isoformat()
                ):
                    _state.iterations += 1

                if _state.iterations == 0:
                    _state.iterations = 1

                trading_dataCopy = trading_data.copy()
                _technical_analysis = TechnicalAnalysis(
                    trading_dataCopy, _app.adjust_total_periods
                )

                # if 'morning_star' not in df:
                _technical_analysis.addAll()

                df = _technical_analysis.getDataFrame()

                _app.sim_smartswitch = False

        elif _app.smart_switch == 1 and _technical_analysis is None:
            trading_dataCopy = trading_data.copy()
            _technical_analysis = TechnicalAnalysis(
                trading_dataCopy, _app.adjust_total_periods
            )

            if "morning_star" not in df:
                _technical_analysis.addAll()

            df = _technical_analysis.getDataFrame()

    else:
        _technical_analysis = TechnicalAnalysis(trading_data, len(trading_data))
        _technical_analysis.addAll()
        df = _technical_analysis.getDataFrame()

    if _app.is_sim:
        df_last = _app.get_interval(df, _state.iterations)
    else:
        df_last = _app.get_interval(df)

    # Don't want index of new, unclosed candle, use the historical row setting to set index to last closed candle
    if _state.closed_candle_row != -2 and len(self.df_last.index.format()) > 0:
        current_df_index = str(self.df_last.index.format()[0])
    else:
        current_df_index = _state.last_df_index

    formatted_current_df_index = (
        f"{current_df_index} 00:00:00"
        if len(current_df_index) == 10
        else current_df_index
    )

    current_sim_date = formatted_current_df_index

    if _state.iterations == 2:
        # check if bot has open or closed order
        # update data.json "opentrades"
        if _state.last_action == "BUY":
            telegram_bot.add_open_order()
        else:
            telegram_bot.remove_open_order()

    if (
        (last_api_call_datetime.seconds > 60 or _app.is_sim)
        and _app.smart_switch == 1
        and _app.sell_smart_switch == 1
        and _app.granularity != Granularity.FIVE_MINUTES
        and _state.last_action == "BUY"
    ):

        if not _app.is_sim or (
            _app.is_sim and not _app.simresultonly
        ):
            Logger.info(
                "*** open order detected smart switching to 300 (5 min) granularity ***"
            )

        if not _app.telegramtradesonly:
            _app.notify_telegram(
                _app.market
                + " open order detected smart switching to 300 (5 min) granularity"
            )

        if _app.is_sim:
            _app.sim_smartswitch = True

        _app.setGranularity(Granularity.FIVE_MINUTES)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, execute_job, (sc, _app, _state, _technical_analysis, _websocket))

    if (
        (last_api_call_datetime.seconds > 60 or _app.is_sim)
        and _app.smart_switch == 1
        and _app.sell_smart_switch == 1
        and _app.granularity == Granularity.FIVE_MINUTES
        and _state.last_action == "SELL"
    ):

        if not _app.is_sim or (
            _app.is_sim and not _app.simresultonly
        ):
            Logger.info(
                "*** sell detected smart switching to 3600 (1 hour) granularity ***"
            )
        if not _app.telegramtradesonly:
            _app.notify_telegram(
                _app.market
                + " sell detected smart switching to 3600 (1 hour) granularity"
            )
        if _app.is_sim:
            _app.sim_smartswitch = True

        _app.setGranularity(Granularity.ONE_HOUR)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, execute_job, (sc, _app, _state, _technical_analysis, _websocket))

    # use actual sim mode date to check smartchswitch
    if (
        (last_api_call_datetime.seconds > 60 or _app.is_sim)
        and _app.smart_switch == 1
        and _app.granularity == Granularity.ONE_HOUR
        and _app.is1hEMA1226Bull(current_sim_date, _websocket) is True
        and _app.is6hEMA1226Bull(current_sim_date, _websocket) is True
    ):
        if not _app.is_sim or (
            _app.is_sim and not _app.simresultonly
        ):
            Logger.info(
                "*** smart switch from granularity 3600 (1 hour) to 900 (15 min) ***"
            )

        if _app.is_sim:
            _app.sim_smartswitch = True

        if not _app.telegramtradesonly:
            _app.notify_telegram(
                _app.market
                + " smart switch from granularity 3600 (1 hour) to 900 (15 min)"
            )

        _app.setGranularity(Granularity.FIFTEEN_MINUTES)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, execute_job, (sc, _app, _state, _technical_analysis, _websocket))

    # use actual sim mode date to check smartchswitch
    if (
        (last_api_call_datetime.seconds > 60 or _app.is_sim)
        and _app.smart_switch == 1
        and _app.granularity == Granularity.FIFTEEN_MINUTES
        and _app.is1hEMA1226Bull(current_sim_date, _websocket) is False
        and _app.is6hEMA1226Bull(current_sim_date, _websocket) is False
    ):
        if not _app.is_sim or (
            _app.is_sim and not _app.simresultonly
        ):
            Logger.info(
                "*** smart switch from granularity 900 (15 min) to 3600 (1 hour) ***"
            )

        if _app.is_sim:
            _app.sim_smartswitch = True

        if not _app.telegramtradesonly:
            _app.notify_telegram(
                f"{_app.market} smart switch from granularity 900 (15 min) to 3600 (1 hour)"
            )

        _app.setGranularity(Granularity.ONE_HOUR)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, execute_job, (sc, _app, _state, _technical_analysis, _websocket))

    if (
        _app.exchange == Exchange.BINANCE
        and _app.granularity == Granularity.ONE_DAY
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
            len(df) < _app.adjust_total_periods - 5
        ):  # If 300 is required, set adjust_total_periods in config to 305.
            if not _app.is_sim:
                # data frame should have 300 rows or equal to adjusted total rows if set, if not retry
                Logger.error(
                    f"error: data frame length is < {str(_app.adjust_total_periods)} ({str(len(df))})"
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
        if _app.is_live:
            last_action_current = _state.last_action
            # If using websockets make this call every minute instead of each iteration
            if _app.websocket and not _app.is_sim:
                if last_api_call_datetime.seconds > 60:
                    _state.poll_last_action()
            else:
                _state.poll_last_action()

            if last_action_current != _state.last_action:
                Logger.info(
                    f"last_action change detected from {last_action_current} to {_state.last_action}"
                )
                if not _app.telegramtradesonly:
                    _app.notify_telegram(
                        f"{_app.market} last_action change detected from {last_action_current} to {_state.last_action}"
                    )

            # this is used to reset variables if error occurred during trade process
            # make sure signals and telegram info is set correctly, close bot if needed on sell
            if _state.action == "check_action" and _state.last_action == "BUY":
                _state.trade_error_cnt = 0
                _state.trailing_buy = False
                _state.action = None
                _state.trailing_buy_immediate = False
                telegram_bot.add_open_order()

                Logger.warning(
                    f"{_app.market} ({_app.print_granularity}) - {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Catching BUY that occurred previously. Updating signal information."
                )

                if not _app.telegramtradesonly:
                    _app.notify_telegram(
                        _app.market
                        + " ("
                        + _app.print_granularity()
                        + ") - "
                        + datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                        + "\n"
                        + "Catching BUY that occurred previously. Updating signal information."
                    )

            elif _state.action == "check_action" and _state.last_action == "SELL":
                _state.prevent_loss = False
                _state.trailing_sell = False
                _state.trailing_sell_immediate = False
                _state.tsl_triggered = False
                _state.tsl_pcnt = float(_app.trailingStopLoss())
                _state.tsl_trigger = float(_app.trailingStopLossTrigger())
                _state.tsl_max = False
                _state.trade_error_cnt = 0
                _state.action = None
                telegram_bot.remove_open_order()

                Logger.warning(
                    f"{_app.market} ({_app.print_granularity}) - {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Catching SELL that occurred previously. Updating signal information."
                )

                if not _app.telegramtradesonly:
                    _app.notify_telegram(
                        _app.market
                        + " ("
                        + _app.print_granularity()
                        + ") - "
                        + datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                        + "\n"
                        + "Catching SELL that occurred previously. Updating signal information."
                    )

                telegram_bot.closetrade(
                    str(_app.get_date_from_iso8601_str(str(datetime.now()))),
                    0,
                    0,
                )

                if _app.enableexitaftersell and _app.startmethod not in ("standard",):
                    sys.exit(0)

        if price < 0.000001:
            raise Exception(
                f"{_app.market} is unsuitable for trading, quote price is less than 0.000001!"
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
        if _app.is_sim:
            if _app.adjust_total_periods < 200:
                goldencross = False
            else:
                goldencross = _app.is1hSMA50200Bull(current_sim_date, _websocket)

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
        telegram_bot.addindicators("EMA", ema12gtema26 or ema12gtema26co)
        if not _app.disablebuyelderray:
            telegram_bot.addindicators("ERI", elder_ray_buy)
        if _app.disablebullonly:
            telegram_bot.addindicators("BULL", goldencross)
        if not _app.disablebuymacd:
            telegram_bot.addindicators("MACD", macdgtsignal or macdgtsignalco)
        if not _app.disablebuyobv:
            telegram_bot.addindicators("OBV", float(obv_pc) > 0)

        if _app.is_sim:
            # Reset the Strategy so that the last record is the current sim date
            # To allow for calculations to be done on the sim date being processed
            sdf = df[df["date"] <= current_sim_date].tail(_app.adjust_total_periods)
            strategy = Strategy(
                _app, _state, sdf, sdf.index.get_loc(str(current_sim_date)) + 1
            )
        else:
            strategy = Strategy(_app, _state, df)

        trailing_action_logtext = ""

        # determine current action, indicatorvalues will be empty if custom Strategy are disabled or it's debug is False
        _state.action, indicatorvalues = strategy.getAction(
            _state, price, current_sim_date, _websocket
        )

        immediate_action = False
        margin, profit, sell_fee, change_pcnt_high = 0, 0, 0, 0

        # Reset the TA so that the last record is the current sim date
        # To allow for calculations to be done on the sim date being processed
        if _app.is_sim:
            trading_dataCopy = (
                trading_data[trading_data["date"] <= current_sim_date]
                .tail(_app.adjust_total_periods)
                .copy()
            )
            _technical_analysis = TechnicalAnalysis(
                trading_dataCopy, _app.adjust_total_periods
            )

        if (
            _state.last_buy_size > 0
            and _state.last_buy_price > 0
            and price > 0
            and _state.last_action == "BUY"
        ):
            # update last buy high
            if price > _state.last_buy_high:
                _state.last_buy_high = price

            if _state.last_buy_high > 0:
                change_pcnt_high = ((price / _state.last_buy_high) - 1) * 100
            else:
                change_pcnt_high = 0

            # buy and sell calculations
            _state.last_buy_fee = round(_state.last_buy_size * _app.getTakerFee(), 8)
            _state.last_buy_filled = round(
                ((_state.last_buy_size - _state.last_buy_fee) / _state.last_buy_price),
                8,
            )

            # if not a simulation, sync with exchange orders
            if not _app.is_sim:
                if _app.websocket:
                    if last_api_call_datetime.seconds > 60:
                        _state.exchange_last_buy = _app.getLastBuy()
                else:
                    _state.exchange_last_buy = _app.getLastBuy()
                exchange_last_buy = _state.exchange_last_buy
                if exchange_last_buy is not None:
                    if _state.last_buy_size != exchange_last_buy["size"]:
                        _state.last_buy_size = exchange_last_buy["size"]
                    if _state.last_buy_filled != exchange_last_buy["filled"]:
                        _state.last_buy_filled = exchange_last_buy["filled"]
                    if _state.last_buy_price != exchange_last_buy["price"]:
                        _state.last_buy_price = exchange_last_buy["price"]

                    if (
                        _app.exchange == Exchange.COINBASEPRO
                        or _app.exchange == Exchange.KUCOIN
                    ):
                        if _state.last_buy_fee != exchange_last_buy["fee"]:
                            _state.last_buy_fee = exchange_last_buy["fee"]

            margin, profit, sell_fee = calculate_margin(
                buy_size=_state.last_buy_size,
                buy_filled=_state.last_buy_filled,
                buy_price=_state.last_buy_price,
                buy_fee=_state.last_buy_fee,
                sell_percent=_app.getSellPercent(),
                sell_price=price,
                sell_taker_fee=_app.getTakerFee(),
            )

            # handle immediate sell actions
            if _app.manual_trades_only is False and strategy.isSellTrigger(
                _app,
                _state,
                price,
                _technical_analysis.getTradeExit(price),
                margin,
                change_pcnt_high,
                obv_pc,
                macdltsignal,
            ):
                _state.action = "SELL"
                immediate_action = True

        # handle overriding wait actions
        # (e.g. do not sell if sell at loss disabled!, do not buy in bull if bull only, manual trades only)
        if _app.manual_trades_only is True or (
            _state.action != "WAIT" and strategy.isWaitTrigger(margin, goldencross)
        ):
            _state.action = "WAIT"
            immediate_action = False

        # If buy signal, save the price and check for decrease/increase before buying.
        if _state.action == "BUY" and immediate_action is not True:
            (
                _state.action,
                _state.trailing_buy,
                trailing_action_logtext,
                immediate_action,
            ) = strategy.checkTrailingBuy(_state, price)
        # If sell signal, save the price and check for decrease/increase before selling.
        if _state.action == "SELL" and immediate_action is not True:
            (
                _state.action,
                _state.trailing_sell,
                trailing_action_logtext,
                immediate_action,
            ) = strategy.checkTrailingSell(_state, price)

        if _app.enableImmediateBuy():
            if _state.action == "BUY":
                immediate_action = True

        if not _app.is_sim and _app.enabletelegrambotcontrol:
            manual_buy_sell = telegram_bot.checkmanualbuysell()
            if not manual_buy_sell == "WAIT":
                _state.action = manual_buy_sell
                immediate_action = True

        bullbeartext = ""
        if (
            _app.disablebullonly is True
            or _app.adjust_total_periods < 200
            or df_last["sma50"].values[0] == df_last["sma200"].values[0]
        ):
            bullbeartext = ""
        elif goldencross is True:
            bullbeartext = " (BULL)"
        elif goldencross is False:
            bullbeartext = " (BEAR)"

        # polling is every 5 minutes (even for hourly intervals), but only process once per interval
        # Logger.debug("DateCheck: " + str(immediate_action) + ' ' + str(_state.last_df_index) + ' ' + str(current_df_index))
        if immediate_action is True or _state.last_df_index != current_df_index:
            text_box = TextBox(80, 22)

            precision = 4

            if price < 0.01:
                precision = 8

            # Since precision does not change after this point, it is safe to prepare a tailored `truncate()` that would
            # work with this precision. It should save a couple of `precision` uses, one for each `truncate()` call.
            truncate = functools.partial(_truncate, n=precision)

            if immediate_action:
                price_text = str(price)
            else:
                price_text = "Close: " + str(price)
            ema_text = ""
            if _app.disablebuyema is False:
                ema_text = _app.compare(
                    df_last["ema12"].values[0],
                    df_last["ema26"].values[0],
                    "EMA12/26",
                    precision,
                )

            macd_text = ""
            if _app.disablebuymacd is False:
                macd_text = _app.compare(
                    df_last["macd"].values[0],
                    df_last["signal"].values[0],
                    "MACD",
                    precision,
                )

            obv_text = ""
            if _app.disablebuyobv is False:
                obv_text = (
                    "OBV: "
                    + truncate(self.df_last["obv"].values[0])
                    + " ("
                    + str(truncate(self.df_last["obv_pc"].values[0]))
                    + "%)"
                )

            _state.eri_text = ""
            if _app.disablebuyelderray is False:
                if elder_ray_buy is True:
                    _state.eri_text = "ERI: buy | "
                elif elder_ray_sell is True:
                    _state.eri_text = "ERI: sell | "
                else:
                    _state.eri_text = "ERI: | "
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
                and not _app.is_sim
                or (_app.is_sim and not _app.simresultonly)
            ):
                Logger.info(log_text)

            ema_co_prefix = ""
            ema_co_suffix = ""
            if _app.disablebuyema is False:
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
            if _app.disablebuymacd is False:
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
            if _app.disablebuyobv is False:
                if float(obv_pc) > 0:
                    obv_prefix = "^ "
                    obv_suffix = " ^ | "
                elif float(obv_pc) < 0:
                    obv_prefix = "v "
                    obv_suffix = " v | "
                else:
                    obv_suffix = " | "

            if not _app.isVerbose():
                if _state.last_action != "":
                    # Not sure if this if is needed just preserving any existing functionality that may have been missed
                    # Updated to show over margin and profit
                    if not _app.is_sim:
                        output_text = (
                            formatted_current_df_index
                            + " | "
                            + _app.market
                            + bullbeartext
                            + " | "
                            + _app.print_granularity()
                            + " | "
                            + price_text
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
                            + _state.eri_text
                            + _state.action
                            + " | Last Action: "
                            + _state.last_action
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
                                    ((price - df["close"].max()) / df["close"].max())
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
                            + _app.market
                            + bullbeartext
                            + " | "
                            + _app.print_granularity()
                            + " | "
                            + price_text
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
                            + _state.eri_text
                            + _state.action
                            + " | Last Action: "
                            + _state.last_action
                            + " | DF HIGH: "
                            + str(df_high)
                            + " | "
                            + "DF LOW: "
                            + str(df_low)
                            + " | SWING: "
                            + str(round(((df_high - df_low) / df_low) * 100, 2))
                            + "% |"
                            + " CURR Price is "
                            + str(round(((price - df_high) / df_high) * 100, 2))
                            + "% "
                            + "away from DF HIGH | Range: "
                            + str(
                                df.iloc[_state.iterations - _app.adjust_total_periods, 0]
                            )
                            + " <--> "
                            + str(df.iloc[_state.iterations - 1, 0])
                        )
                else:
                    if not _app.isSimulation:
                        output_text = (
                            formatted_current_df_index
                            + " | "
                            + _app.market
                            + bullbeartext
                            + " | "
                            + _app.print_granularity()
                            + " | "
                            + price_text
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
                            + _state.eri_text
                            + _state.action
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
                                    ((price - df["close"].max()) / df["close"].max())
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
                            + _app.market
                            + bullbeartext
                            + " | "
                            + _app.print_granularity()
                            + " | "
                            + price_text
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
                            + _state.eri_text
                            + _state.action
                            + " | DF HIGH: "
                            + str(df_high)
                            + " | "
                            + "DF LOW: "
                            + str(df_low)
                            + " | SWING: "
                            + str(round(((df_high - df_low) / df_low) * 100, 2))
                            + "%"
                            + " CURR Price is "
                            + str(round(((price - df_high) / df_high) * 100, 2))
                            + "% "
                            + "away from DF HIGH | Range: "
                            + str(
                                df.iloc[_state.iterations - _app.adjust_total_periods, 0]
                            )
                            + " <--> "
                            + str(df.iloc[_state.iterations - 1, 0])
                        )
                if _state.last_action == "BUY":
                    if _state.last_buy_size > 0:
                        margin_text = truncate(margin) + "%"
                    else:
                        margin_text = "0%"

                    output_text += (
                        trailing_action_logtext
                        + " | (margin: "
                        + margin_text
                        + " delta: "
                        + str(round(price - _state.last_buy_price, precision))
                        + ")"
                    )
                    if _app.is_sim:
                        # save margin for Summary if open trade
                        _state.open_trade_margin = margin_text

                if not _app.is_sim or (
                    _app.is_sim and not _app.simresultonly
                ):
                    Logger.info(output_text)

                if _app.enableML():
                    # Seasonal Autoregressive Integrated Moving Average (ARIMA) model (ML prediction for 3 intervals from now)
                    if not _app.is_sim:
                        try:
                            prediction = (
                                _technical_analysis.seasonalARIMAModelPrediction(
                                    int(_app.granularity.to_integer / 60) * 3
                                )
                            )  # 3 intervals from now
                            Logger.info(
                                f"Seasonal ARIMA model predicts the closing price will be {str(round(prediction[1], 2))} at {prediction[0]} (delta: {round(prediction[1] - price, 2)})"
                            )
                        # pylint: disable=bare-except
                        except:
                            pass

                if _state.last_action == "BUY":
                    # display support, resistance and fibonacci levels
                    if not _app.is_sim or (
                        _app.is_sim and not _app.simresultonly
                    ):
                        Logger.info(
                            _technical_analysis.printSupportResistanceFibonacciLevels(
                                price
                            )
                        )

            else:
                # set to true for verbose debugging
                debug = False

                if debug:
                    Logger.debug(
                        f"-- Iteration: {str(_state.iterations)} --{bullbeartext}"
                    )

                if _state.last_action == "BUY":
                    if _state.last_buy_size > 0:
                        margin_text = truncate(margin) + "%"
                    else:
                        margin_text = "0%"
                        if _app.is_sim:
                            # save margin for Summary if open trade
                            _state.open_trade_margin = margin_text
                    if debug:
                        Logger.debug(f"-- Margin: {margin_text} --")

                if debug:
                    Logger.debug(f"price: {truncate(price)}")
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
                    if _app.adjust_total_periods >= 50:
                        Logger.debug(
                            f'sma50: {truncate(float(self.df_last["sma50"].values[0]))}'
                        )
                    if _app.adjust_total_periods >= 200:
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
                    Logger.debug(f"action: {_state.action}")

                # informational output on the most recent entry
                Logger.info("")
                text_box.doubleLine()
                text_box.line("Iteration", str(_state.iterations) + bullbeartext)
                text_box.line("Timestamp", str(self.df_last.index.format()[0]))
                text_box.singleLine()
                text_box.line("Close", truncate(price))
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
                text_box.line("Action", _state.action)
                text_box.doubleLine()
                if _state.last_action == "BUY":
                    text_box.line("Margin", margin_text)
                    text_box.doubleLine()

            # if a buy signal
            if _state.action == "BUY":
                _state.last_buy_price = price
                _state.last_buy_high = _state.last_buy_price

                # if live
                if _app.is_live:
                    ac = account.getBalance()
                    account.basebalance_before = 0.0
                    account.quotebalance_before = 0.0
                    try:
                        df_base = ac[ac["currency"] == _app.base_currency][
                            "available"
                        ]
                        account.basebalance_before = (
                            0.0 if len(df_base) == 0 else float(df_base.values[0])
                        )

                        df_quote = ac[ac["currency"] == _app.quote_currency][
                            "available"
                        ]
                        account.quotebalance_before = (
                            0.0 if len(df_quote) == 0 else float(df_quote.values[0])
                        )
                    except:
                        pass

                    if (
                        not _app.insufficientfunds
                        and _app.buyminsize < account.quotebalance_before
                    ):
                        if not _app.isVerbose():
                            if not _app.is_sim or (
                                _app.is_sim and not _app.simresultonly
                            ):
                                Logger.info(
                                    f"{formatted_current_df_index} | {_app.market} | {_app.print_granularity()} | {price_text} | BUY"
                                )
                        else:
                            text_box.singleLine()
                            text_box.center("*** Executing LIVE Buy Order ***")
                            text_box.singleLine()

                        # display balances
                        Logger.info(
                            f"{_app.base_currency} balance before order: {str(account.basebalance_before)}"
                        )
                        Logger.info(
                            f"{_app.quote_currency} balance before order: {str(account.quotebalance_before)}"
                        )

                        # execute a live market buy
                        _state.last_buy_size = float(account.quotebalance_before)

                        if (
                            _app.buymaxsize
                            and _app.buylastsellsize
                            and _state.minimumOrderQuote(
                                quote=_state.last_sell_size, balancechk=True
                            )
                        ):
                            _state.last_buy_size = _state.last_sell_size
                        elif (
                            _app.buymaxsize
                            and _state.last_buy_size > _app.buymaxsize
                        ):
                            _state.last_buy_size = _app.buymaxsize

                        # place the buy order
                        try:
                            resp = _app.marketBuy(
                                _app.market,
                                _state.last_buy_size,
                                _app.getBuyPercent(),
                            )
                            resp_error = 0
                            # Logger.debug(resp)
                        except Exception as err:
                            Logger.warning(f"Trade Error: {err}")
                            resp_error = 1

                        if resp_error == 0:
                            account.basebalance_after = 0
                            account.quotebalance_after = 0
                            try:
                                ac = account.getBalance()
                                df_base = ac[ac["currency"] == _app.base_currency][
                                    "available"
                                ]
                                account.basebalance_after = (
                                    0.0
                                    if len(df_base) == 0
                                    else float(df_base.values[0])
                                )
                                df_quote = ac[
                                    ac["currency"] == _app.quote_currency
                                ]["available"]

                                account.quotebalance_after = (
                                    0.0
                                    if len(df_quote) == 0
                                    else float(df_quote.values[0])
                                )
                                bal_error = 0
                            except Exception as err:
                                bal_error = 1
                                Logger.warning(
                                    f"Error: Balance not retrieved after trade for {app.market}.\n"
                                    f"API Error Msg: {err}"
                                )

                            if bal_error == 0:
                                _state.trade_error_cnt = 0
                                _state.trailing_buy = False
                                _state.last_action = "BUY"
                                _state.action = "DONE"
                                _state.trailing_buy_immediate = False
                                telegram_bot.add_open_order()

                                Logger.info(
                                    f"{_app.base_currency} balance after order: {str(account.basebalance_after)}\n"
                                    f"{_app.quote_currency} balance after order: {str(account.quotebalance_after)}"
                                )

                                _app.notify_telegram(
                                    _app.market
                                    + " ("
                                    + _app.print_granularity()
                                    + ") - "
                                    + datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                                    + "\n"
                                    + "BUY at "
                                    + price_text
                                )

                            else:
                                # set variable to trigger to check trade on next iteration
                                _state.action = "check_action"
                                Logger.info(
                                    f"{_app.market} - Error occurred while checking balance after BUY. Last transaction check will happen shortly."
                                )

                                if not app.disabletelegramerrormsgs:
                                    _app.notify_telegram(
                                        _app.market
                                        + " - Error occurred while checking balance after BUY. Last transaction check will happen shortly."
                                    )

                        else:  # there was a response error
                            # only attempt BUY 3 times before exception to prevent continuous loop
                            _state.trade_error_cnt += 1
                            if _state.trade_error_cnt >= 2:  # 3 attempts made
                                raise Exception(
                                    f"Trade Error: BUY transaction attempted 3 times. Check log for errors"
                                )

                            # set variable to trigger to check trade on next iteration
                            _state.action = "check_action"
                            _state.last_action = None

                            Logger.warning(
                                f"API Error: Unable to place buy order for {app.market}."
                            )
                            if not app.disabletelegramerrormsgs:
                                app.notify_telegram(
                                    f"API Error: Unable to place buy order for {app.market}"
                                )
                            time.sleep(30)

                    else:
                        Logger.warning(
                            "Unable to place order, insufficient funds or buyminsize has not been reached. Check Logs."
                        )

                    state.last_api_call_datetime -= timedelta(seconds=60)

                # if not live
                else:
                    if _state.last_buy_size == 0 and _state.last_buy_filled == 0:
                        # Sim mode can now use buymaxsize as the amount used for a buy
                        if _app.buymaxsize != None:
                            _state.last_buy_size = _app.buymaxsize
                            _state.first_buy_size = _app.buymaxsize
                        else:
                            _state.last_buy_size = 1000
                            _state.first_buy_size = 1000
                    # add option for buy last sell size
                    elif (
                        _app.buymaxsize != None
                        and _app.buylastsellsize
                        and _state.last_sell_size
                        > _state.minimumOrderQuote(
                            quote=_state.last_sell_size, balancechk=True
                        )
                    ):
                        _state.last_buy_size = _state.last_sell_size

                    _state.buy_count = _state.buy_count + 1
                    _state.buy_sum = _state.buy_sum + _state.last_buy_size
                    _state.trailing_buy = False
                    _state.action = "DONE"
                    _state.trailing_buy_immediate = False

                    _app.notify_telegram(
                        _app.market
                        + " ("
                        + _app.print_granularity()
                        + ") -  "
                        + str(current_sim_date)
                        + "\n - TEST BUY at "
                        + price_text
                        + "\n - Buy Size: "
                        + str(_truncate(_state.last_buy_size, 4))
                    )

                    if not _app.isVerbose():
                        if not _app.is_sim or (
                            _app.is_sim and not _app.simresultonly
                        ):
                            Logger.info(
                                f"{formatted_current_df_index} | {_app.market} | {_app.print_granularity()} | {price_text} | BUY"
                            )

                        bands = _technical_analysis.getFibonacciRetracementLevels(
                            float(price)
                        )

                        if not _app.is_sim or (
                            _app.is_sim and not _app.simresultonly
                        ):
                            _technical_analysis.printSupportResistanceLevel(
                                float(price)
                            )

                        if not _app.is_sim or (
                            _app.is_sim and not _app.simresultonly
                        ):
                            Logger.info(f" Fibonacci Retracement Levels:{str(bands)}")

                        if len(bands) >= 1 and len(bands) <= 2:
                            if len(bands) == 1:
                                first_key = list(bands.keys())[0]
                                if first_key == "ratio1":
                                    _state.fib_low = 0
                                    _state.fib_high = bands[first_key]
                                if first_key == "ratio1_618":
                                    _state.fib_low = bands[first_key]
                                    _state.fib_high = bands[first_key] * 2
                                else:
                                    _state.fib_low = bands[first_key]

                            elif len(bands) == 2:
                                first_key = list(bands.keys())[0]
                                second_key = list(bands.keys())[1]
                                _state.fib_low = bands[first_key]
                                _state.fib_high = bands[second_key]

                    else:
                        text_box.singleLine()
                        text_box.center("*** Executing TEST Buy Order ***")
                        text_box.singleLine()

                    _app.trade_tracker = pd.concat(
                        [
                            _app.trade_tracker,
                            pd.DataFrame(
                                {
                                    "Datetime": str(current_sim_date),
                                    "Market": _app.market,
                                    "Action": "BUY",
                                    "Price": price,
                                    "Quote": _state.last_buy_size,
                                    "Base": float(_state.last_buy_size) / float(price),
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

                    state.in_open_trade = True
                    _state.last_action = "BUY"
                    state.last_api_call_datetime -= timedelta(seconds=60)

                if _app.shouldSaveGraphs():
                    if _app.adjust_total_periods < 200:
                        Logger.info(
                            "Trading Graphs can only be generated when dataframe has more than 200 periods."
                        )
                    else:
                        tradinggraphs = TradingGraphs(_technical_analysis)
                        ts = datetime.now().timestamp()
                        filename = f"{_app.market}_{_app.print_granularity()}_buy_{str(ts)}.png"
                        # This allows graphs to be used in sim mode using the correct DF
                        if _app.isSimulation:
                            tradinggraphs.renderEMAandMACD(
                                len(trading_dataCopy), "graphs/" + filename, True
                            )
                        else:
                            tradinggraphs.renderEMAandMACD(
                                len(trading_data), "graphs/" + filename, True
                            )

            # if a sell signal
            elif _state.action == "SELL":
                # if live
                if _app.is_live:
                    if _app.isVerbose():

                        bands = _technical_analysis.getFibonacciRetracementLevels(
                            float(price)
                        )

                        if not _app.is_sim or (
                            _app.is_sim and not _app.simresultonly
                        ):
                            Logger.info(f" Fibonacci Retracement Levels:{str(bands)}")

                            if len(bands) >= 1 and len(bands) <= 2:
                                if len(bands) == 1:
                                    first_key = list(bands.keys())[0]
                                    if first_key == "ratio1":
                                        _state.fib_low = 0
                                        _state.fib_high = bands[first_key]
                                    if first_key == "ratio1_618":
                                        _state.fib_low = bands[first_key]
                                        _state.fib_high = bands[first_key] * 2
                                    else:
                                        _state.fib_low = bands[first_key]

                                elif len(bands) == 2:
                                    first_key = list(bands.keys())[0]
                                    second_key = list(bands.keys())[1]
                                    _state.fib_low = bands[first_key]
                                    _state.fib_high = bands[second_key]

                        text_box.singleLine()
                        text_box.center("*** Executing LIVE Sell Order ***")
                        text_box.singleLine()

                    else:
                        Logger.info(
                            f"{formatted_current_df_index} | {_app.market} | {_app.print_granularity()} | {price_text} | SELL"
                        )

                    # check balances before and display
                    account.basebalance_before = 0
                    account.quotebalance_before = 0
                    try:
                        account.basebalance_before = float(
                            account.getBalance(_app.base_currency)
                        )
                        account.quotebalance_before = float(
                            account.getBalance(_app.quote_currency)
                        )
                    except:
                        pass

                    Logger.info(
                        f"{_app.base_currency} balance before order: {str(account.basebalance_before)}\n"
                        f"{_app.quote_currency} balance before order: {str(account.quotebalance_before)}"
                    )

                    # execute a live market sell
                    baseamounttosell = (
                        float(account.basebalance_before)
                        if _app.sellfullbaseamount == True
                        else float(state.last_buy_filled)
                    )

                    account.basebalance_after = 0
                    account.quotebalance_after = 0
                    # place the sell order
                    try:
                        resp = _app.marketSell(
                            _app.market,
                            baseamounttosell,
                            _app.getSellPercent(),
                        )
                        resp_error = 0
                        # Logger.debug(resp)
                    except Exception as err:
                        Logger.warning(f"Trade Error: {err}")
                        resp_error = 1

                    if resp_error == 0:
                        try:
                            account.basebalance_after = float(
                                account.getBalance(_app.base_currency)
                            )
                            account.quotebalance_after = float(
                                account.getBalance(_app.quote_currency)
                            )
                            bal_error = 0
                        except Exception as err:
                            bal_error = 1
                            Logger.warning(
                                f"Error: Balance not retrieved after trade for {app.market}.\n"
                                f"API Error Msg: {err}"
                            )

                        if bal_error == 0:
                            Logger.info(
                                f"{_app.base_currency} balance after order: {str(account.basebalance_after)}\n"
                                f"{_app.quote_currency} balance after order: {str(account.quotebalance_after)}"
                            )
                            _state.prevent_loss = False
                            _state.trailing_sell = False
                            _state.trailing_sell_immediate = False
                            _state.tsl_triggered = False
                            _state.tsl_pcnt = float(_app.trailingStopLoss())
                            _state.tsl_trigger = float(_app.trailingStopLossTrigger())
                            _state.tsl_max = False
                            _state.trade_error_cnt = 0
                            _state.last_action = "SELL"
                            _state.action = "DONE"

                            _app.notify_telegram(
                                _app.market
                                + " ("
                                + _app.print_granularity()
                                + ") - "
                                + datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                                + "\n"
                                + "SELL at "
                                + price_text
                                + " (margin: "
                                + margin_text
                                + ", delta: "
                                + str(round(price - _state.last_buy_price, precision))
                                + ")"
                            )

                            telegram_bot.closetrade(
                                str(_app.get_date_from_iso8601_str(str(datetime.now()))),
                                price_text,
                                margin_text,
                            )

                            if _app.enableexitaftersell and _app.startmethod not in (
                                "standard",
                                "telegram",
                            ):
                                sys.exit(0)

                        else:
                            # set variable to trigger to check trade on next iteration
                            _state.action = "check_action"

                            Logger.info(
                                _app.market
                                + " - Error occurred while checking balance after SELL. Last transaction check will happen shortly."
                            )

                            if not app.disabletelegramerrormsgs:
                                _app.notify_telegram(
                                    _app.market
                                    + " - Error occurred while checking balance after SELL. Last transaction check will happen shortly."
                                )

                    else:  # there was an error
                        # only attempt SELL 3 times before exception to prevent continuous loop
                        _state.trade_error_cnt += 1
                        if _state.trade_error_cnt >= 2:  # 3 attempts made
                            raise Exception(
                                f"Trade Error: SELL transaction attempted 3 times. Check log for errors."
                            )
                        # set variable to trigger to check trade on next iteration
                        _state.action = "check_action"
                        _state.last_action = None

                        Logger.warning(
                            f"API Error: Unable to place SELL order for {app.market}."
                        )
                        if not app.disabletelegramerrormsgs:
                            app.notify_telegram(
                                f"API Error: Unable to place SELL order for {app.market}"
                            )
                        time.sleep(30)

                    state.last_api_call_datetime -= timedelta(seconds=60)

                # if not live
                else:
                    margin, profit, sell_fee = calculate_margin(
                        buy_size=_state.last_buy_size,
                        buy_filled=_state.last_buy_filled,
                        buy_price=_state.last_buy_price,
                        buy_fee=_state.last_buy_fee,
                        sell_percent=_app.getSellPercent(),
                        sell_price=price,
                        sell_taker_fee=_app.getTakerFee(),
                    )

                    if _state.last_buy_size > 0:
                        margin_text = truncate(margin) + "%"
                    else:
                        margin_text = "0%"

                    # save last buy before this sell to use in Sim Summary
                    _state.previous_buy_size = _state.last_buy_size
                    # preserve next sell values for simulator
                    _state.sell_count = _state.sell_count + 1
                    sell_size = (_app.getSellPercent() / 100) * (
                        (price / _state.last_buy_price)
                        * (_state.last_buy_size - _state.last_buy_fee)
                    )
                    _state.last_sell_size = sell_size - sell_fee
                    _state.sell_sum = _state.sell_sum + _state.last_sell_size

                    # Added to track profit and loss margins during sim runs
                    _state.margintracker += float(margin)
                    _state.profitlosstracker += float(profit)
                    _state.feetracker += float(sell_fee)
                    _state.buy_tracker += float(_state.last_buy_size)

                    _app.notify_telegram(
                        _app.market
                        + " ("
                        + _app.print_granularity()
                        + ") "
                        + str(current_sim_date)
                        + "\n - TEST SELL at "
                        + str(price_text)
                        + " (margin: "
                        + margin_text
                        + ", delta: "
                        + str(round(price - _state.last_buy_price, precision))
                        + ")"
                    )

                    if not _app.isVerbose():
                        if price > 0:
                            margin_text = truncate(margin) + "%"
                        else:
                            margin_text = "0%"

                        if not _app.is_sim or (
                            _app.is_sim and not _app.simresultonly
                        ):
                            Logger.info(
                                formatted_current_df_index
                                + " | "
                                + _app.market
                                + " | "
                                + _app.print_granularity()
                                + " | SELL | "
                                + str(price)
                                + " | BUY | "
                                + str(_state.last_buy_price)
                                + " | DIFF | "
                                + str(price - _state.last_buy_price)
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

                    _app.trade_tracker = pd.concat(
                        [
                            _app.trade_tracker,
                            pd.DataFrame(
                                {
                                    "Datetime": str(current_sim_date),
                                    "Market": _app.market,
                                    "Action": "SELL",
                                    "Price": price,
                                    "Quote": _state.last_sell_size,
                                    "Base": _state.last_buy_filled,
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

                    state.in_open_trade = False
                    state.last_api_call_datetime -= timedelta(seconds=60)
                    _state.last_action = "SELL"
                    _state.prevent_loss = False
                    _state.trailing_sell = False
                    _state.trailing_sell_immediate = False
                    _state.tsl_triggered = False

                    if _app.trailingStopLoss():
                        _state.tsl_pcnt = float(_app.trailingStopLoss())

                    if _app.trailingStopLossTrigger():
                        _state.tsl_trigger = float(_app.trailingStopLossTrigger())

                    _state.tsl_max = False
                    _state.action = "DONE"

                if _app.shouldSaveGraphs():
                    tradinggraphs = TradingGraphs(_technical_analysis)
                    ts = datetime.now().timestamp()
                    filename = f"{_app.market}_{_app.print_granularity()}_sell_{str(ts)}.png"
                    # This allows graphs to be used in sim mode using the correct DF
                    if _app.is_sim:
                        tradinggraphs.renderEMAandMACD(
                            len(trading_dataCopy), "graphs/" + filename, True
                        )
                    else:
                        tradinggraphs.renderEMAandMACD(
                            len(trading_data), "graphs/" + filename, True
                        )

            _state.last_df_index = str(self.df_last.index.format()[0])

            if (
                _app.enabledLogBuySellInJson() == True
                and _state.action == "DONE"
                and len(_app.trade_tracker) > 0
            ):
                Logger.info(
                    _app.trade_tracker.loc[len(_app.trade_tracker) - 1].to_json()
                )

            if _state.action == "DONE" and indicatorvalues != "":
                _app.notify_telegram(indicatorvalues)

            if not _app.is_live and _state.iterations == len(df):
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
                    "exchange": _app.exchange,
                }

                if _app.getConfig() != "":
                    simulation["config"] = _app.getConfig()

                if not _app.simresultonly:
                    Logger.info(f"\nSimulation Summary: {_app.market}")

                tradesfile = _app.getTradesFile()

                if _app.isVerbose():
                    Logger.info("\n" + str(_app.trade_tracker))
                    start = str(df.head(1).index.format()[0]).replace(":", ".")
                    end = str(df.tail(1).index.format()[0]).replace(":", ".")
                    filename = (
                        f"{_app.market} {str(start)} - {str(end)}_{tradesfile}"
                    )

                else:
                    filename = tradesfile
                try:
                    if not os.path.isabs(filename):
                        if not os.path.exists("csv"):
                            os.makedirs("csv")
                        filename = os.path.join(os.curdir, "csv", filename)
                    _app.trade_tracker.to_csv(filename)
                except OSError:
                    Logger.critical(f"Unable to save: {filename}")

                if _state.buy_count == 0:
                    _state.last_buy_size = 0
                    _state.sell_sum = 0
                else:
                    _state.sell_sum = _state.sell_sum + _state.last_sell_size

                remove_last_buy = False
                if _state.buy_count > _state.sell_count:
                    remove_last_buy = True
                    _state.buy_count -= 1  # remove last buy as there has not been a corresponding sell yet
                    _state.last_buy_size = _state.previous_buy_size
                    simulation["data"]["open_buy_excluded"] = 1

                    if not _app.simresultonly:
                        Logger.info(
                            "\nWarning: simulation ended with an open trade and it will be excluded from the margin calculation."
                        )
                        Logger.info(
                            "         (it is not realistic to hard sell at the end of a simulation without a sell signal)"
                        )
                else:
                    simulation["data"]["open_buy_excluded"] = 0

                if not _app.simresultonly:
                    Logger.info("\n")

                if remove_last_buy is True:
                    if not _app.simresultonly:
                        Logger.info(
                            f"   Buy Count : {str(_state.buy_count)} (open buy excluded)"
                        )
                    else:
                        simulation["data"]["buy_count"] = _state.buy_count
                else:
                    if not _app.simresultonly:
                        Logger.info(f"   Buy Count : {str(_state.buy_count)}")
                    else:
                        simulation["data"]["buy_count"] = _state.buy_count

                if not _app.simresultonly:
                    Logger.info(f"  Sell Count : {str(_state.sell_count)}")
                    Logger.info(f"   First Buy : {str(_state.first_buy_size)}")
                    Logger.info(
                        f"   Last Buy : {str(_truncate(_state.last_buy_size, 4))}"
                    )
                else:
                    simulation["data"]["sell_count"] = _state.sell_count
                    simulation["data"]["first_trade"] = {}
                    simulation["data"]["first_trade"]["size"] = _state.first_buy_size

                if _state.sell_count > 0:
                    if not _app.simresultonly:
                        Logger.info(
                            f"   Last Sell : {_truncate(_state.last_sell_size, 4)}\n"
                        )
                    else:
                        simulation["data"]["last_trade"] = {}
                        simulation["data"]["last_trade"]["size"] = float(
                            _truncate(_state.last_sell_size, 2)
                        )
                else:
                    if not _app.simresultonly:
                        Logger.info("\n")
                        Logger.info("      Margin : 0.00%")
                        Logger.info("\n")
                        Logger.info(
                            "  ** margin is nil as a sell has not occurred during the simulation\n"
                        )
                    else:
                        simulation["data"]["margin"] = 0.0

                    _app.notify_telegram(
                        "      Margin: 0.00%\n  ** margin is nil as a sell has not occurred during the simulation\n"
                    )

                _app.notify_telegram(
                    f"Simulation Summary\n"
                    + f"   Market: {_app.market}\n"
                    + f"   Buy Count: {_state.buy_count}\n"
                    + f"   Sell Count: {_state.sell_count}\n"
                    + f"   First Buy: {_state.first_buy_size}\n"
                    + f"   Last Buy: {str(_truncate(_state.last_buy_size, 4))}\n"
                    + f"   Last Sell: {str(_truncate(_state.last_sell_size, 4))}\n"
                )

                if _state.sell_count > 0:
                    _last_trade_margin = _truncate(
                        (
                            (
                                (_state.last_sell_size - _state.last_buy_size)
                                / _state.last_buy_size
                            )
                            * 100
                        ),
                        4,
                    )

                    if not _app.simresultonly:
                        Logger.info(
                            "   Last Trade Margin : " + _last_trade_margin + "%"
                        )
                        if remove_last_buy:
                            Logger.info(
                                f"\n   Open Trade Margin at end of simulation: {_state.open_trade_margin}"
                            )
                        Logger.info("\n")
                        Logger.info(
                            f"   All Trades Buys ({_app.quote_currency}): {_truncate(_state.buy_tracker, 2)}"
                        )
                        Logger.info(
                            f"   All Trades Profit/Loss ({_app.quote_currency}): {_truncate(_state.profitlosstracker, 2)} ({_truncate(_state.feetracker,2)} in fees)"
                        )
                        Logger.info(
                            f"   All Trades Margin : {_truncate(_state.margintracker, 4)}%"
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
                        ] = _app.quote_currency
                        simulation["data"]["all_trades"]["value_buys"] = float(
                            _truncate(_state.buy_tracker, 2)
                        )
                        simulation["data"]["all_trades"]["profit_loss"] = float(
                            _truncate(_state.profitlosstracker, 2)
                        )
                        simulation["data"]["all_trades"]["fees"] = float(
                            _truncate(_state.feetracker, 2)
                        )
                        simulation["data"]["all_trades"]["margin"] = float(
                            _truncate(_state.margintracker, 4)
                        )

                    ## Revised telegram Summary notification to give total margin in addition to last trade margin.
                    _app.notify_telegram(
                        f"      Last Trade Margin: {_last_trade_margin}%\n\n"
                    )
                    if remove_last_buy:
                        _app.notify_telegram(
                            f"\nOpen Trade Margin at end of simulation: {_state.open_trade_margin}\n"
                        )
                    _app.notify_telegram(
                        f"      All Trades Margin: {_truncate(_state.margintracker, 4)}%\n  ** non-live simulation, assuming highest fees\n  ** open trade excluded from margin calculation\n"
                    )
                    telegram_bot.removeactivebot()

                if _app.simresultonly:
                    Logger.info(json.dumps(simulation, sort_keys=True, indent=4))

        else:
            if (
                _state.last_buy_size > 0
                and _state.last_buy_price > 0
                and price > 0
                and _state.last_action == "BUY"
            ):
                # show profit and margin if already bought
                Logger.info(
                    f"{now} | {_app.market}{bullbeartext} | {_app.print_granularity()} | Current Price: {str(price)} {trailing_action_logtext} | Margin: {str(margin)} | Profit: {str(profit)}"
                )
            else:
                Logger.info(
                    f'{now} | {_app.market}{bullbeartext} | {_app.print_granularity()} | Current Price: {str(price)}{trailing_action_logtext} | {str(round(((price-df["close"].max()) / df["close"].max())*100, 2))}% from DF HIGH'
                )
                telegram_bot.addinfo(
                    f'{now} | {_app.market}{bullbeartext} | {_app.print_granularity()} | Current Price: {str(price)}{trailing_action_logtext} | {str(round(((price-df["close"].max()) / df["close"].max())*100, 2))}% from DF HIGH',
                    round(price, 4),
                    str(round(df["close"].max(), 4)),
                    str(
                        round(
                            ((price - df["close"].max()) / df["close"].max()) * 100, 2
                        )
                    )
                    + "%",
                    _state.action,
                )

            if (
                _state.last_action == "BUY"
                and _state.in_open_trade
                and last_api_call_datetime.seconds > 60
            ):
                # update margin for telegram bot
                telegram_bot.addmargin(
                    str(_truncate(margin, 4) + "%")
                    if _state.in_open_trade == True
                    else " ",
                    str(_truncate(profit, 2)) if _state.in_open_trade == True else " ",
                    price,
                    change_pcnt_high,
                    _state.action,
                )

            # Update the watchdog_ping
            telegram_bot.updatewatchdogping()

            # decrement ignored iteration
            if _app.is_sim and _app.smart_switch:
                _state.iterations = _state.iterations - 1

        # if live but not websockets
        if not _app.disabletracker and _app.is_live and not _app.websocket:
            # update order tracker csv
            if _app.exchange == Exchange.BINANCE:
                account.saveTrackerCSV(_app.market)
            elif (
                _app.exchange == Exchange.COINBASEPRO
                or _app.exchange == Exchange.KUCOIN
            ):
                account.saveTrackerCSV()

        if _app.is_sim:
            if _state.iterations < len(df):
                if _app.sim_speed in ["fast", "fast-sample"]:
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
                _app.websocket
                and _websocket is not None
                and (
                    isinstance(_websocket.tickers, pd.DataFrame)
                    and len(_websocket.tickers) == 1
                )
                and (
                    isinstance(_websocket.candles, pd.DataFrame)
                    and len(_websocket.candles) == _app.adjust_total_periods
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
                if _app.websocket and not _app.is_sim:
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
        if app.exchange == Exchange.COINBASEPRO:
            message += "Coinbase Pro bot"
            if app.websocket and not app.is_sim:
                print("Opening websocket to Coinbase Pro...")
                _websocket = CWebSocketClient([app.market], app.granularity)
                _websocket.start()
        elif app.exchange == Exchange.BINANCE:
            message += "Binance bot"
            if app.websocket and not app.is_sim:
                print("Opening websocket to Binance...")
                _websocket = BWebSocketClient([app.market], app.granularity)
                _websocket.start()
        elif app.exchange == Exchange.KUCOIN:
            message += "Kucoin bot"
            if app.websocket and not app.is_sim:
                print("Opening websocket to Kucoin...")
                _websocket = KWebSocketClient([app.market], app.granularity)
                _websocket.start()

        smartswitchstatus = "enabled" if app.smart_switch else "disabled"
        message += f" for {app.market} using granularity {app.print_granularity()}. Smartswitch {smartswitchstatus}"

        if app.startmethod in ("standard", "telegram"):
            app.notify_telegram(message)

        # initialise and start application
        trading_data = app.startApp(app, account, state.last_action)

        if app.is_sim and app.simend_date:
            try:
                # if simend_date is set, then remove trailing data points
                trading_data = trading_data[trading_data["date"] <= app.simend_date]
            except Exception:
                pass

        def runApp(_websocket, _trading_data):
            # run the first job immediately after starting
            if app.is_sim:
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
            if app.autorestart:
                # Wait 30 second and try to relaunch application
                time.sleep(30)
                Logger.critical(f"Restarting application after exception: {repr(e)}")

                if not app.disabletelegramerrormsgs:
                    app.notify_telegram(
                        f"Auto restarting bot for {app.market} after exception: {repr(e)}"
                    )

                # Cancel the events queue
                map(s.cancel, s.queue)

                # Restart the app
                runApp(_websocket)
            else:
                raise

    # catches a keyboard break of app, exits gracefully
    except (KeyboardInterrupt, SystemExit):
        if app.websocket and not app.is_sim:
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
                telegram_bot.removeactivebot()
            except:
                pass
            if app.websocket and not app.is_sim:
                _websocket.close()
            sys.exit(0)
        except SystemExit:
            # pylint: disable=protected-access
            os._exit(0)
    except (BaseException, Exception) as e:  # pylint: disable=broad-except
        # catch all not managed exceptions and send a Telegram message if configured
        if not app.disabletelegramerrormsgs:
            app.notify_telegram(f"Bot for {app.market} got an exception: {repr(e)}")
            try:
                telegram_bot.removeactivebot()
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
