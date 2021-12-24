#!/usr/bin/env python3
# encoding: utf-8

"""Python Crypto Bot consuming Coinbase Pro or Binance APIs"""

import functools
import os
import sched
import sys
import time
import signal
import json
from datetime import datetime, timedelta
import pandas as pd

from models.AppState import AppState
from models.exchange.Granularity import Granularity
from models.helper.LogHelper import Logger
from models.helper.MarginHelper import calculate_margin
from models.PyCryptoBot import PyCryptoBot
from models.PyCryptoBot import truncate as _truncate
from models.Stats import Stats
from models.Strategy import Strategy
from models.Trading import TechnicalAnalysis
from models.TradingAccount import TradingAccount
from views.TradingGraphs import TradingGraphs
from models.helper.TextBoxHelper import TextBox
from models.exchange.ExchangesEnum import Exchange
from models.exchange.binance import WebSocketClient as BWebSocketClient
from models.exchange.coinbase_pro import WebSocketClient as CWebSocketClient
from models.exchange.kucoin import WebSocketClient as KWebSocketClient
from models.helper.TelegramBotHelper import TelegramBotHelper

# minimal traceback
sys.tracebacklimit = 1

app = PyCryptoBot()
account = TradingAccount(app)
Stats(app, account).show()
technical_analysis = None
state = AppState(app, account)
state.initLastAction()

telegram_bot = TelegramBotHelper(app)

s = sched.scheduler(time.time, time.sleep)


def signal_handler(signum, frame):
    if signum == 2:
        print("Please be patient while websockets terminate!")
        #Logger.debug(frame)
        return


def executeJob(
    sc=None,
    _app: PyCryptoBot = None,
    _state: AppState = None,
    _technical_analysis=None,
    _websocket=None,
    trading_data=pd.DataFrame(),
):
    """Trading bot job which runs at a scheduled interval"""

    # This is used to control some API calls when using websockets
    last_api_call_datetime = datetime.now() - _state.last_api_call_datetime
    if last_api_call_datetime.seconds > 60:
        _state.last_api_call_datetime = datetime.now()

    # This is used by the telegram bot
    # If it not enabled in config while will always be False
    if not _app.isSimulation():
        controlstatus = telegram_bot.checkbotcontrolstatus()
        while controlstatus == "pause" or controlstatus == "paused":
            if controlstatus == "pause":
                print(str(datetime.now()).format() + " - Bot is paused")
                _app.notifyTelegram(f"{_app.getMarket()} bot is paused")
                telegram_bot.updatebotstatus("paused")
                if _app.enableWebsocket():
                    Logger.info("Stopping _websocket...")
                    _websocket.close()

            time.sleep(30)
            controlstatus = telegram_bot.checkbotcontrolstatus()

        if controlstatus == "start":
            print(str(datetime.now()).format() + " - Bot has restarted")
            _app.notifyTelegram(f"{_app.getMarket()} bot has restarted")
            telegram_bot.updatebotstatus("active")
            _app.read_config(_app.getExchange())
            if _app.enableWebsocket():
                Logger.info("Starting _websocket...")
                _websocket.start()

        if controlstatus == "exit":
            _app.notifyTelegram(f"{_app.getMarket()} bot is stopping")
            sys.exit(0)

    # reset _websocket every 23 hours if applicable
    if _app.enableWebsocket() and not _app.isSimulation():
        if _websocket.getTimeElapsed() > 82800:
            Logger.info("Websocket requires a restart every 23 hours!")
            Logger.info("Stopping _websocket...")
            _websocket.close()
            Logger.info("Starting _websocket...")
            _websocket.start()
            Logger.info("Restarting job in 30 seconds...")
            s.enter(
                30, 1, executeJob, (sc, _app, _state, _technical_analysis, _websocket)
            )

    # increment _state.iterations
    _state.iterations = _state.iterations + 1

    if not _app.isSimulation():
        # retrieve the _app.getMarket() data
        trading_data = _app.getHistoricalData(
            _app.getMarket(), _app.getGranularity(), _websocket
        )

    else:
        if len(trading_data) == 0:
            return None

    # analyse the market data
    if _app.isSimulation() and len(trading_data.columns) > 8:
        df = trading_data
        if _app.appStarted and _app.simstartdate is not None:
            # On first run set the iteration to the start date entered
            # This sim mode now pulls 300 candles from before the entered start date
            _state.iterations = (
                df.index.get_loc(str(_app.getDateFromISO8601Str(_app.simstartdate))) + 1
            )
            _app.appStarted = False
        # if smartswitch then get the market data using new granularity
        if _app.sim_smartswitch:
            df_last = _app.getInterval(df, _state.iterations)
            if len(df_last.index.format()) > 0:
                if _app.simstartdate is not None:
                    startDate = _app.getDateFromISO8601Str(_app.simstartdate)
                else:
                    startDate = _app.getDateFromISO8601Str(
                        str(df.head(1).index.format()[0])
                    )

                if _app.simenddate is not None:
                    if _app.simenddate == "now":
                        endDate = _app.getDateFromISO8601Str(str(datetime.now()))
                    else:
                        endDate = _app.getDateFromISO8601Str(_app.simenddate)
                else:
                    endDate = _app.getDateFromISO8601Str(
                        str(df.tail(1).index.format()[0])
                    )

                simDate = _app.getDateFromISO8601Str(str(_state.last_df_index))

                trading_data = _app.getSmartSwitchHistoricalDataChained(
                    _app.getMarket(),
                    _app.getGranularity(),
                    str(startDate),
                    str(endDate),
                )

                if _app.getGranularity() == Granularity.ONE_HOUR:
                    simDate = _app.getDateFromISO8601Str(str(simDate))
                    sim_rounded = pd.Series(simDate).dt.round("60min")
                    simDate = sim_rounded[0]
                elif _app.getGranularity() == Granularity.FIFTEEN_MINUTES:
                    simDate = _app.getDateFromISO8601Str(str(simDate))
                    sim_rounded = pd.Series(simDate).dt.round("15min")
                    simDate = sim_rounded[0]
                elif _app.getGranularity() == Granularity.FIVE_MINUTES:
                    simDate = _app.getDateFromISO8601Str(str(simDate))
                    sim_rounded = pd.Series(simDate).dt.round("5min")
                    simDate = sim_rounded[0]

                dateFound = False
                while dateFound == False:
                    try:
                        _state.iterations = trading_data.index.get_loc(str(simDate)) + 1
                        dateFound = True
                    except:
                        simDate += timedelta(seconds=_app.getGranularity().value[0])

                if (
                    _app.getDateFromISO8601Str(str(simDate)).isoformat()
                    == _app.getDateFromISO8601Str(str(_state.last_df_index)).isoformat()
                ):
                    _state.iterations += 1

                if _state.iterations == 0:
                    _state.iterations = 1

                trading_dataCopy = trading_data.copy()
                _technical_analysis = TechnicalAnalysis(trading_dataCopy)

                # if 'morning_star' not in df:
                _technical_analysis.addAll()

                df = _technical_analysis.getDataFrame()

                _app.sim_smartswitch = False

        elif _app.getSmartSwitch() == 1 and _technical_analysis is None:
            trading_dataCopy = trading_data.copy()
            _technical_analysis = TechnicalAnalysis(trading_dataCopy)

            if "morning_star" not in df:
                _technical_analysis.addAll()

            df = _technical_analysis.getDataFrame()

    else:
        trading_dataCopy = trading_data.copy()
        _technical_analysis = TechnicalAnalysis(trading_dataCopy)
        _technical_analysis.addAll()
        df = _technical_analysis.getDataFrame()

        if _app.isSimulation() and _app.appStarted:
            # On first run set the iteration to the start date entered
            # This sim mode now pulls 300 candles from before the entered start date
            _state.iterations = (
                df.index.get_loc(str(_app.getDateFromISO8601Str(_app.simstartdate))) + 1
            )
            _app.appStarted = False

    if _app.isSimulation():
        df_last = _app.getInterval(df, _state.iterations)
    else:
        df_last = _app.getInterval(df)

    if len(df_last.index.format()) > 0:
        current_df_index = str(df_last.index.format()[0])
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
        (last_api_call_datetime.seconds > 60 or _app.isSimulation())
        and _app.getSmartSwitch() == 1
        and _app.getSellSmartSwitch() == 1
        and _app.getGranularity() != Granularity.FIVE_MINUTES
        and _state.last_action == "BUY"
    ):

        if not _app.isSimulation() or (
            _app.isSimulation() and not _app.simResultOnly()
        ):
            Logger.info(
                "*** open order detected smart switching to 300 (5 min) granularity ***"
            )

        if not _app.telegramTradesOnly():
            _app.notifyTelegram(
                _app.getMarket()
                + " open order detected smart switching to 300 (5 min) granularity"
            )

        if _app.isSimulation():
            _app.sim_smartswitch = True

        _app.setGranularity(Granularity.FIVE_MINUTES)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, executeJob, (sc, _app, _state, _technical_analysis, _websocket))

    if (
        (last_api_call_datetime.seconds > 60 or _app.isSimulation())
        and _app.getSmartSwitch() == 1
        and _app.getSellSmartSwitch() == 1
        and _app.getGranularity() == Granularity.FIVE_MINUTES
        and _state.last_action == "SELL"
    ):

        if not _app.isSimulation() or (
            _app.isSimulation() and not _app.simResultOnly()
        ):
            Logger.info(
                "*** sell detected smart switching to 3600 (1 hour) granularity ***"
            )
        if not _app.telegramTradesOnly():
            _app.notifyTelegram(
                _app.getMarket()
                + " sell detected smart switching to 3600 (1 hour) granularity"
            )
        if _app.isSimulation():
            _app.sim_smartswitch = True

        _app.setGranularity(Granularity.ONE_HOUR)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, executeJob, (sc, _app, _state, _technical_analysis, _websocket))

    # use actual sim mode date to check smartchswitch
    if (
        (last_api_call_datetime.seconds > 60 or _app.isSimulation())
        and _app.getSmartSwitch() == 1
        and _app.getGranularity() == Granularity.ONE_HOUR
        and _app.is1hEMA1226Bull(current_sim_date, _websocket) is True
        and _app.is6hEMA1226Bull(current_sim_date, _websocket) is True
    ):
        if not _app.isSimulation() or (
            _app.isSimulation() and not _app.simResultOnly()
        ):
            Logger.info(
                "*** smart switch from granularity 3600 (1 hour) to 900 (15 min) ***"
            )

        if _app.isSimulation():
            _app.sim_smartswitch = True

        if not _app.telegramTradesOnly():
            _app.notifyTelegram(
                _app.getMarket()
                + " smart switch from granularity 3600 (1 hour) to 900 (15 min)"
            )

        _app.setGranularity(Granularity.FIFTEEN_MINUTES)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, executeJob, (sc, _app, _state, _technical_analysis, _websocket))

    # use actual sim mode date to check smartchswitch
    if (
        (last_api_call_datetime.seconds > 60 or _app.isSimulation())
        and _app.getSmartSwitch() == 1
        and _app.getGranularity() == Granularity.FIFTEEN_MINUTES
        and _app.is1hEMA1226Bull(current_sim_date, _websocket) is False
        and _app.is6hEMA1226Bull(current_sim_date, _websocket) is False
    ):
        if not _app.isSimulation() or (
            _app.isSimulation() and not _app.simResultOnly()
        ):
            Logger.info(
                "*** smart switch from granularity 900 (15 min) to 3600 (1 hour) ***"
            )

        if _app.isSimulation():
            _app.sim_smartswitch = True

        if not _app.telegramTradesOnly():
            _app.notifyTelegram(
                f"{_app.getMarket()} smart switch from granularity 900 (15 min) to 3600 (1 hour)"
            )

        _app.setGranularity(Granularity.ONE_HOUR)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, executeJob, (sc, _app, _state, _technical_analysis, _websocket))

    if (
        _app.getExchange() == Exchange.BINANCE
        and _app.getGranularity() == Granularity.ONE_DAY
    ):
        if len(df) < 250:
            # data frame should have 250 rows, if not retry
            Logger.error(f"error: data frame length is < 250 ({str(len(df))})")
            list(map(s.cancel, s.queue))
            s.enter(
                300, 1, executeJob, (sc, _app, _state, _technical_analysis, _websocket)
            )
    else:
        if len(df) < 300:
            if not _app.isSimulation():
                # data frame should have 300 rows, if not retry
                Logger.error(f"error: data frame length is < 300 ({str(len(df))})")
                list(map(s.cancel, s.queue))
                s.enter(
                    300,
                    1,
                    executeJob,
                    (sc, _app, _state, _technical_analysis, _websocket),
                )
    # change_pcnt_high set to 0 here to prevent errors on some tokens for some users.
    # Need to track down main source of error.  This allows bots to launch in those instances.
    change_pcnt_high = 0
    if len(df_last) > 0:
        now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        # last_action polling if live
        if _app.isLive():
            last_action_current = _state.last_action
            # If using websockets make this call every minute instead of each iteration
            if _app.enableWebsocket() and not _app.isSimulation():
                if last_api_call_datetime.seconds > 60:
                    _state.pollLastAction()
            else:
                _state.pollLastAction()
            if last_action_current != _state.last_action:
                Logger.info(
                    f"last_action change detected from {last_action_current} to {_state.last_action}"
                )
                if not _app.telegramTradesOnly():
                    _app.notifyTelegram(
                        f"{_app.getMarket} last_action change detected from {last_action_current} to {_state.last_action}"
                    )

        if not _app.isSimulation():
            ticker = _app.getTicker(_app.getMarket(), _websocket)
            now = ticker[0]
            price = ticker[1]
            if price < df_last["low"].values[0] or price == 0:
                price = float(df_last["close"].values[0])
        else:
            price = float(df_last["close"].values[0])

        if price < 0.000001:
            raise Exception(
                f"{_app.getMarket()} is unsuitable for trading, quote price is less than 0.000001!"
            )

        # technical indicators
        ema12gtema26 = bool(df_last["ema12gtema26"].values[0])
        ema12gtema26co = bool(df_last["ema12gtema26co"].values[0])
        goldencross = bool(df_last["goldencross"].values[0])
        macdgtsignal = bool(df_last["macdgtsignal"].values[0])
        macdgtsignalco = bool(df_last["macdgtsignalco"].values[0])
        ema12ltema26 = bool(df_last["ema12ltema26"].values[0])
        ema12ltema26co = bool(df_last["ema12ltema26co"].values[0])
        macdltsignal = bool(df_last["macdltsignal"].values[0])
        macdltsignalco = bool(df_last["macdltsignalco"].values[0])
        obv = float(df_last["obv"].values[0])
        obv_pc = float(df_last["obv_pc"].values[0])
        elder_ray_buy = bool(df_last["eri_buy"].values[0])
        elder_ray_sell = bool(df_last["eri_sell"].values[0])

        # if simulation, set goldencross based on actual sim date
        if _app.isSimulation():
            goldencross = _app.is1hSMA50200Bull(current_sim_date, _websocket)

        # candlestick detection
        hammer = bool(df_last["hammer"].values[0])
        inverted_hammer = bool(df_last["inverted_hammer"].values[0])
        hanging_man = bool(df_last["hanging_man"].values[0])
        shooting_star = bool(df_last["shooting_star"].values[0])
        three_white_soldiers = bool(df_last["three_white_soldiers"].values[0])
        three_black_crows = bool(df_last["three_black_crows"].values[0])
        morning_star = bool(df_last["morning_star"].values[0])
        evening_star = bool(df_last["evening_star"].values[0])
        three_line_strike = bool(df_last["three_line_strike"].values[0])
        abandoned_baby = bool(df_last["abandoned_baby"].values[0])
        morning_doji_star = bool(df_last["morning_doji_star"].values[0])
        evening_doji_star = bool(df_last["evening_doji_star"].values[0])
        two_black_gapping = bool(df_last["two_black_gapping"].values[0])

        # Log data for Telegram Bot
        telegram_bot.addindicators("EMA", ema12gtema26co or ema12ltema26)
        if not _app.disableBuyElderRay():
            telegram_bot.addindicators("ERI", elder_ray_buy)
        if _app.disableBullOnly():
            telegram_bot.addindicators("BULL", goldencross)
        if not _app.disableBuyMACD():
            telegram_bot.addindicators("MACD", macdgtsignal or macdgtsignalco)
        if not _app.disableBuyOBV():
            telegram_bot.addindicators("OBV", float(obv_pc) > 0)

        if _app.isSimulation():
            # Reset the Strategy so that the last record is the current sim date
            # To allow for calculations to be done on the sim date being processed
            sdf = df[df["date"] <= current_sim_date].tail(300)
            strategy = Strategy(
                _app, _state, sdf, sdf.index.get_loc(str(current_sim_date)) + 1
            )
        else:
            strategy = Strategy(_app, _state, df, _state.iterations)

        _state.action = strategy.getAction(_app, price, current_sim_date)

        immediate_action = False
        margin, profit, sell_fee = 0, 0, 0

        # Reset the TA so that the last record is the current sim date
        # To allow for calculations to be done on the sim date being processed
        if _app.isSimulation():
            trading_dataCopy = (
                trading_data[trading_data["date"] <= current_sim_date].tail(300).copy()
            )
            _technical_analysis = TechnicalAnalysis(trading_dataCopy)

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
            if not _app.isSimulation():
                if _app.enableWebsocket():
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
                        _app.getExchange() == Exchange.COINBASEPRO
                        or _app.getExchange() == Exchange.KUCOIN
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
            if strategy.isSellTrigger(
                _app,
                price,
                _technical_analysis.getTradeExit(price),
                margin,
                change_pcnt_high,
                obv_pc,
                macdltsignal,
            ):
                _state.action = "SELL"
                _state.last_action = "BUY"
                immediate_action = True

        # handle overriding wait actions (e.g. do not sell if sell at loss disabled!, do not buy in bull if bull only)
        if strategy.isWaitTrigger(_app, margin, goldencross):
            _state.action = "WAIT"
            immediate_action = False

        if _app.enableImmediateBuy():
            if _state.action == "BUY":
                immediate_action = True

        if not _app.isSimulation() and _app.enableTelegramBotControl():
            manual_buy_sell = telegram_bot.checkmanualbuysell()
            if not manual_buy_sell == "WAIT":
                _state.action = manual_buy_sell
                _state.last_action = "BUY" if _state.action == "SELL" else "SELL"
                immediate_action = True

        # If buy signal, save the price and check for decrease/increase before buying.
        trailing_buy_logtext = ""
        if _state.action == "BUY" and immediate_action != True:
            _state.action, _state.trailing_buy, trailing_buy_logtext = strategy.checkTrailingBuy(_app, _state, price)

        bullbeartext = ""
        if _app.disableBullOnly() is True or (
            df_last["sma50"].values[0] == df_last["sma200"].values[0]
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

            price_text = "Close: " + str(price)
            ema_text = ""
            if _app.disableBuyEMA() is False:
                ema_text = _app.compare(
                    df_last["ema12"].values[0],
                    df_last["ema26"].values[0],
                    "EMA12/26",
                    precision,
                )

            macd_text = ""
            if _app.disableBuyMACD() is False:
                macd_text = _app.compare(
                    df_last["macd"].values[0],
                    df_last["signal"].values[0],
                    "MACD",
                    precision,
                )

            obv_text = ""
            if _app.disableBuyOBV() is False:
                obv_text = (
                    "OBV: "
                    + truncate(df_last["obv"].values[0])
                    + " ("
                    + str(truncate(df_last["obv_pc"].values[0]))
                    + "%)"
                )

            _state.eri_text = ""
            if _app.disableBuyElderRay() is False:
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
                and not _app.isSimulation()
                or (_app.isSimulation() and not _app.simResultOnly())
            ):
                Logger.info(log_text)

            ema_co_prefix = ""
            ema_co_suffix = ""
            if _app.disableBuyEMA() is False:
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
            if _app.disableBuyMACD() is False:
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
            if _app.disableBuyOBV() is False:
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
                    if not _app.isSimulation():
                        output_text = (
                            formatted_current_df_index
                            + " | "
                            + _app.getMarket()
                            + bullbeartext
                            + " | "
                            + _app.printGranularity()
                            + " | "
                            + price_text
                            + trailing_buy_logtext
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
                            + _app.getMarket()
                            + bullbeartext
                            + " | "
                            + _app.printGranularity()
                            + " | "
                            + price_text
                            + trailing_buy_logtext
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
                            + str(df.iloc[_state.iterations - 300, 0])
                            + " <--> "
                            + str(df.iloc[_state.iterations - 1, 0])
                        )
                else:
                    if not _app.isSimulation:
                        output_text = (
                            formatted_current_df_index
                            + " | "
                            + _app.getMarket()
                            + bullbeartext
                            + " | "
                            + _app.printGranularity()
                            + " | "
                            + price_text
                            + trailing_buy_logtext
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
                            + _app.getMarket()
                            + bullbeartext
                            + " | "
                            + _app.printGranularity()
                            + " | "
                            + price_text
                            + trailing_buy_logtext
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
                            + str(df.iloc[_state.iterations - 300, 0])
                            + " <--> "
                            + str(df.iloc[_state.iterations - 1, 0])
                        )
                if _state.last_action == "BUY":
                    if _state.last_buy_size > 0:
                        margin_text = truncate(margin) + "%"
                    else:
                        margin_text = "0%"

                    output_text += (
                        " | (margin: "
                        + margin_text
                        + " delta: "
                        + str(round(price - _state.last_buy_price, precision))
                        + ")"
                    )
                    if _app.isSimulation():
                        # save margin for Summary if open trade
                        _state.open_trade_margin = margin_text

                if not _app.isSimulation() or (
                    _app.isSimulation() and not _app.simResultOnly()
                ):
                    Logger.info(output_text)

                if _app.enableML():
                    # Seasonal Autoregressive Integrated Moving Average (ARIMA) model (ML prediction for 3 intervals from now)
                    if not _app.isSimulation():
                        try:
                            prediction = (
                                _technical_analysis.seasonalARIMAModelPrediction(
                                    int(_app.getGranularity().to_integer / 60) * 3
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
                    if not _app.isSimulation() or (
                        _app.isSimulation() and not _app.simResultOnly()
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
                    Logger.debug(f"-- Iteration: {str(_state.iterations)} --{bullbeartext}")

                if _state.last_action == "BUY":
                    if _state.last_buy_size > 0:
                        margin_text = truncate(margin) + "%"
                    else:
                        margin_text = "0%"
                        if _app.isSimulation():
                            # save margin for Summary if open trade
                            _state.open_trade_margin = margin_text
                    if debug:
                        Logger.debug(f"-- Margin: {margin_text} --")

                if debug:
                    Logger.debug(f"price: {truncate(price)}")
                    Logger.debug(f'ema12: {truncate(float(df_last["ema12"].values[0]))}')
                    Logger.debug(f'ema26: {truncate(float(df_last["ema26"].values[0]))}')
                    Logger.debug(f"ema12gtema26co: {str(ema12gtema26co)}")
                    Logger.debug(f"ema12gtema26: {str(ema12gtema26)}")
                    Logger.debug(f"ema12ltema26co: {str(ema12ltema26co)}")
                    Logger.debug(f"ema12ltema26: {str(ema12ltema26)}")
                    Logger.debug(f'sma50: {truncate(float(df_last["sma50"].values[0]))}')
                    Logger.debug(f'sma200: {truncate(float(df_last["sma200"].values[0]))}')
                    Logger.debug(f'macd: {truncate(float(df_last["macd"].values[0]))}')
                    Logger.debug(f'signal: {truncate(float(df_last["signal"].values[0]))}')
                    Logger.debug(f"macdgtsignal: {str(macdgtsignal)}")
                    Logger.debug(f"macdltsignal: {str(macdltsignal)}")
                    Logger.debug(f"obv: {str(obv)}")
                    Logger.debug(f"obv_pc: {str(obv_pc)}")
                    Logger.debug(f"action: {_state.action}")

                # informational output on the most recent entry
                Logger.info("")
                text_box.doubleLine()
                text_box.line("Iteration", str(_state.iterations) + bullbeartext)
                text_box.line("Timestamp", str(df_last.index.format()[0]))
                text_box.singleLine()
                text_box.line("Close", truncate(price))
                text_box.line("EMA12", truncate(float(df_last["ema12"].values[0])))
                text_box.line("EMA26", truncate(float(df_last["ema26"].values[0])))
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

                text_box.line("SMA20", truncate(float(df_last["sma20"].values[0])))
                text_box.line("SMA200", truncate(float(df_last["sma200"].values[0])))
                text_box.singleLine()
                text_box.line("MACD", truncate(float(df_last["macd"].values[0])))
                text_box.line("Signal", truncate(float(df_last["signal"].values[0])))
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
                if _app.isLive():
                    if not _app.insufficientfunds and _app.getBuyMinSize() < float(
                        account.getBalance(_app.getQuoteCurrency())
                    ):
                        if not _app.isVerbose():
                            if not _app.isSimulation() or (
                                _app.isSimulation() and not _app.simResultOnly()
                            ):
                                Logger.info(
                                    f"{formatted_current_df_index} | {_app.getMarket()} | {_app.printGranularity()} | {price_text} | BUY"
                                )
                        else:
                            text_box.singleLine()
                            text_box.center("*** Executing LIVE Buy Order ***")
                            text_box.singleLine()

                        account.basebalance = 0.0
                        account.quotebalance = 0.0

                        ac = account.getBalance()
                        try:
                            df_base = ac[ac["currency"] == _app.getBaseCurrency()][
                                "available"
                            ]
                            account.basebalance = (
                                0.0 if len(df_base) == 0 else float(df_base.values[0])
                            )

                            df_quote = ac[ac["currency"] == _app.getQuoteCurrency()][
                                "available"
                            ]
                            account.quotebalance = (
                                0.0 if len(df_quote) == 0 else float(df_quote.values[0])
                            )
                        except:
                            pass
                        # display balances
                        Logger.info(
                            f"{_app.getBaseCurrency()} balance before order: {str(account.basebalance)}"
                        )
                        Logger.info(
                            f"{_app.getQuoteCurrency()} balance before order: {str(account.quotebalance)}"
                        )

                        # execute a live market buy
                        # _state.last_buy_size = float(account.getBalance(_app.getQuoteCurrency()))
                        _state.last_buy_size = float(account.quotebalance)

                        if (
                            _app.getBuyMaxSize()
                            and _app.buyLastSellSize()
                            and _state.last_sell_size > 0
                        ):
                            _state.last_buy_size = _state.last_sell_size
                        elif (
                            _app.getBuyMaxSize()
                            and _state.last_buy_size > _app.getBuyMaxSize()
                        ):
                            _state.last_buy_size = _app.getBuyMaxSize()

                        try:
                            resp = _app.marketBuy(
                                _app.getMarket(),
                                _state.last_buy_size,
                                _app.getBuyPercent(),
                            )

                            # Logger.debug(resp)

                            # display balances
                            ac = account.getBalance()
                            try:

                                df_base = ac[ac["currency"] == _app.getBaseCurrency()]["available"]
                                account.basebalance = (
                                    0.0
                                    if len(df_base) == 0
                                    else float(df_base.values[0])
                                )

                                df_quote = ac[ac["currency"] == _app.getQuoteCurrency()]["available"]

                                account.quotebalance = (
                                    0.0
                                    if len(df_quote) == 0
                                    else float(df_quote.values[0])
                                )
                            except:
                                pass

                        except:
                            Logger.warning("Unable to place order")
                            state.last_api_call_datetime -= timedelta(seconds=60)

                        Logger.info(
                            f"{_app.getBaseCurrency()} balance after order: {str(account.basebalance)}"
                        )
                        Logger.info(
                            f"{_app.getQuoteCurrency()} balance after order: {str(account.quotebalance)}"
                        )

                        now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                        _app.notifyTelegram(
                            _app.getMarket()
                            + " ("
                            + _app.printGranularity()
                            + ") - "
                            + now
                            + "\n"
                            + "BUY at "
                            + price_text
                        )

                        state.last_api_call_datetime -= timedelta(seconds=60)
                        telegram_bot.add_open_order()
                        _state.trailing_buy = 0

                    else:
                        Logger.warning(
                            "Unable to place order, insufficient funds or buyminsize has not been reached"
                        )
                        state.last_api_call_datetime -= timedelta(seconds=60)
                # if not live
                else:
                    if _state.last_buy_size == 0 and _state.last_buy_filled == 0:
                        # Sim mode can now use buymaxsize as the amount used for a buy
                        if _app.getBuyMaxSize() != None:
                            _state.last_buy_size = _app.getBuyMaxSize()
                            _state.first_buy_size = _app.getBuyMaxSize()
                        else:
                            _state.last_buy_size = 1000
                            _state.first_buy_size = 1000
                    # add option for buy last sell size
                    elif (
                        _app.getBuyMaxSize() != None
                        and _app.buyLastSellSize()
                        and _state.last_sell_size > 0
                    ):
                        _state.last_buy_size = _state.last_sell_size

                    _state.buy_count = _state.buy_count + 1
                    _state.buy_sum = _state.buy_sum + _state.last_buy_size
                    _state.trailing_buy = 0

                    _app.notifyTelegram(
                        _app.getMarket()
                        + " ("
                        + _app.printGranularity()
                        + ") -  "
                        + str(current_sim_date)
                        + "\n - TEST BUY at "
                        + price_text
                        + "\n - Buy Size: "
                        + str(_truncate(_state.last_buy_size, 4))
                    )

                    if not _app.isVerbose():
                        if not _app.isSimulation() or (
                            _app.isSimulation() and not _app.simResultOnly()
                        ):
                            Logger.info(
                                f"{formatted_current_df_index} | {_app.getMarket()} | {_app.printGranularity()} | {price_text} | BUY"
                            )

                        bands = _technical_analysis.getFibonacciRetracementLevels(
                            float(price)
                        )

                        if not _app.isSimulation() or (
                            _app.isSimulation() and not _app.simResultOnly()
                        ):
                            _technical_analysis.printSupportResistanceLevel(
                                float(price)
                            )

                        if not _app.isSimulation() or (
                            _app.isSimulation() and not _app.simResultOnly()
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

                    _app.trade_tracker = _app.trade_tracker.append(
                        {
                            "Datetime": str(current_sim_date),
                            "Market": _app.getMarket(),
                            "Action": "BUY",
                            "Price": price,
                            "Quote": _state.last_buy_size,
                            "Base": float(_state.last_buy_size) / float(price),
                            "DF_High": df[df["date"] <= current_sim_date][
                                "close"
                            ].max(),
                            "DF_Low": df[df["date"] <= current_sim_date]["close"].min(),
                        },
                        ignore_index=True,
                    )

                    state.last_api_call_datetime -= timedelta(seconds=60)

                if _app.shouldSaveGraphs():
                    tradinggraphs = TradingGraphs(_technical_analysis)
                    ts = datetime.now().timestamp()
                    filename = f"{_app.getMarket()}_{_app.printGranularity()}_buy_{str(ts)}.png"
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
                if _app.isLive():
                    account.basebalance = float(
                        account.getBalance(_app.getBaseCurrency())
                    )
                    account.quotebalance = float(
                        account.getBalance(_app.getQuoteCurrency())
                    )

                    if not _app.isVerbose():
                        Logger.info(
                            f"{formatted_current_df_index} | {_app.getMarket()} | {_app.printGranularity()} | {price_text} | SELL"
                        )

                        bands = _technical_analysis.getFibonacciRetracementLevels(
                            float(price)
                        )

                        if not _app.isSimulation() or (
                            _app.isSimulation() and not _app.simResultOnly()
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
                        text_box.center("*** Executing LIVE Sell Order ***")
                        text_box.singleLine()

                    # display balances
                    Logger.info(
                        f"{_app.getBaseCurrency()} balance before order: {str(account.basebalance)}"
                    )
                    Logger.info(
                        f"{_app.getQuoteCurrency()} balance before order: {str(account.quotebalance)}"
                    )

                    # execute a live market sell
                    baseamounttosell = (
                        float(account.basebalance)
                        if _app.sellfullbaseamount == True
                        else float(state.last_buy_filled)
                    )
                    resp = _app.marketSell(
                        _app.getMarket(),
                        baseamounttosell,
                        _app.getSellPercent(),
                    )
                    #Logger.debug(resp)

                    # display balances
                    account.basebalance = float(
                        account.getBalance(_app.getBaseCurrency())
                    )
                    account.quotebalance = float(
                        account.getBalance(_app.getQuoteCurrency())
                    )
                    Logger.info(
                        f"{_app.getBaseCurrency()} balance after order: {str(account.basebalance)}"
                    )
                    Logger.info(
                        f"{_app.getQuoteCurrency()} balance after order: {str(account.quotebalance)}"
                    )
                    _state.prevent_loss = 0

                    _app.notifyTelegram(
                        _app.getMarket()
                        + " ("
                        + _app.printGranularity()
                        + ") - "
                        + now
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
                        str(_app.getDateFromISO8601Str(str(datetime.now()))),
                        price_text,
                        margin_text,
                    )

                    if _app.enableexitaftersell and _app.startmethod not in (
                        "standard",
                        "telegram",
                    ):
                        sys.exit(0)

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

                    _app.notifyTelegram(
                        _app.getMarket()
                        + " ("
                        + _app.printGranularity()
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

                        if not _app.isSimulation() or (
                            _app.isSimulation() and not _app.simResultOnly()
                        ):
                            Logger.info(
                                formatted_current_df_index
                                + " | "
                                + _app.getMarket()
                                + " | "
                                + _app.printGranularity()
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

                    _app.trade_tracker = _app.trade_tracker.append(
                        {
                            "Datetime": str(current_sim_date),
                            "Market": _app.getMarket(),
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
                            "DF_Low": df[df["date"] <= current_sim_date]["close"].min(),
                        },
                        ignore_index=True,
                    )
                    state.last_api_call_datetime -= timedelta(seconds=60)
                if _app.shouldSaveGraphs():
                    tradinggraphs = TradingGraphs(_technical_analysis)
                    ts = datetime.now().timestamp()
                    filename = f"{_app.getMarket()}_{_app.printGranularity()}_sell_{str(ts)}.png"
                    # This allows graphs to be used in sim mode using the correct DF
                    if _app.isSimulation():
                        tradinggraphs.renderEMAandMACD(
                            len(trading_dataCopy), "graphs/" + filename, True
                        )
                    else:
                        tradinggraphs.renderEMAandMACD(
                            len(trading_data), "graphs/" + filename, True
                        )

            # last significant action
            if _state.action in ["BUY", "SELL"]:
                _state.last_action = _state.action

            _state.last_df_index = str(df_last.index.format()[0])

            if (
                _app.enabledLogBuySellInJson() == True
                and _state.action in ["BUY", "SELL"]
                and len(_app.trade_tracker) > 0
            ):
                Logger.info(
                    _app.trade_tracker.loc[len(_app.trade_tracker) - 1].to_json()
                )

            if not _app.isLive() and _state.iterations == len(df):
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
                    "exchange": _app.getExchange(),
                }

                if _app.getConfig() != "":
                    simulation["config"] = _app.getConfig()

                if not _app.simResultOnly():
                    Logger.info(f"\nSimulation Summary: {_app.getMarket()}")

                tradesfile = _app.getTradesFile()

                if _app.isVerbose():
                    Logger.info("\n" + str(_app.trade_tracker))
                    start = str(df.head(1).index.format()[0]).replace(":", ".")
                    end = str(df.tail(1).index.format()[0]).replace(":", ".")
                    filename = (
                        f"{_app.getMarket()} {str(start)} - {str(end)}_{tradesfile}"
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

                    if not _app.simResultOnly():
                        Logger.info(
                            "\nWarning: simulation ended with an open trade and it will be excluded from the margin calculation."
                        )
                        Logger.info(
                            "         (it is not realistic to hard sell at the end of a simulation without a sell signal)"
                        )
                else:
                    simulation["data"]["open_buy_excluded"] = 0

                if not _app.simResultOnly():
                    Logger.info("\n")

                if remove_last_buy is True:
                    if not _app.simResultOnly():
                        Logger.info(
                            f"   Buy Count : {str(_state.buy_count)} (open buy excluded)"
                        )
                    else:
                        simulation["data"]["buy_count"] = _state.buy_count
                else:
                    if not _app.simResultOnly():
                        Logger.info(f"   Buy Count : {str(_state.buy_count)}")
                    else:
                        simulation["data"]["buy_count"] = _state.buy_count

                if not _app.simResultOnly():
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
                    if not _app.simResultOnly():
                        Logger.info(
                            f"   Last Sell : {_truncate(_state.last_sell_size, 4)}\n"
                        )
                    else:
                        simulation["data"]["last_trade"] = {}
                        simulation["data"]["last_trade"]["size"] = float(
                            _truncate(_state.last_sell_size, 2)
                        )
                else:
                    if not _app.simResultOnly():
                        Logger.info("\n")
                        Logger.info("      Margin : 0.00%")
                        Logger.info("\n")
                        Logger.info(
                            "  ** margin is nil as a sell as not occurred during the simulation\n"
                        )
                    else:
                        simulation["data"]["margin"] = 0.0

                    _app.notifyTelegram(
                        "      Margin: 0.00%\n  ** margin is nil as a sell as not occurred during the simulation\n"
                    )

                _app.notifyTelegram(
                    f"Simulation Summary\n"
                    + f"   Market: {_app.getMarket()}\n"
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

                    if not _app.simResultOnly():
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
                    _app.notifyTelegram(
                        f"      Last Trade Margin: {_last_trade_margin}%\n\n"
                    )
                    if remove_last_buy:
                        _app.notifyTelegram(
                            f"\nOpen Trade Margin at end of simulation: {_state.open_trade_margin}\n"
                        )
                    _app.notifyTelegram(
                        f"      All Trades Margin: {_truncate(_state.margintracker, 4)}%\n  ** non-live simulation, assuming highest fees\n  ** open trade excluded from margin calculation\n"
                    )
                    telegram_bot.removeactivebot()

                if _app.simResultOnly():
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
                    f"{now} | {_app.getMarket()}{bullbeartext} | {_app.printGranularity()} | Current Price: {str(price)} | Margin: {str(margin)} | Profit: {str(profit)}"
                )
            else:
                Logger.info(
                    f'{now} | {_app.getMarket()}{bullbeartext} | {_app.printGranularity()} | Current Price: {str(price)}{trailing_buy_logtext} | {str(round(((price-df["close"].max()) / df["close"].max())*100, 2))}% from DF HIGH'
                )
                telegram_bot.addinfo(
                    f'{now} | {_app.getMarket()}{bullbeartext} | {_app.printGranularity()} | Current Price: {str(price)}{trailing_buy_logtext} | {str(round(((price-df["close"].max()) / df["close"].max())*100, 2))}% from DF HIGH',
                    round(price, 4),
                    str(round(df["close"].max(), 4)),
                    str(
                        round(
                            ((price - df["close"].max()) / df["close"].max()) * 100, 2
                        )
                    )
                    + "%",
                )

            if _state.last_action == "BUY":
                # update margin for telegram bot
                telegram_bot.addmargin(
                    str(_truncate(margin, 4) + "%"),
                    str(_truncate(profit, 2)),
                    price,
                    change_pcnt_high,
                )

            # decrement ignored iteration
            if _app.isSimulation() and _app.smart_switch:
                _state.iterations = _state.iterations - 1

        # if live but not websockets
        if not _app.disableTracker() and _app.isLive() and not _app.enableWebsocket():
            # update order tracker csv
            if _app.getExchange() == Exchange.BINANCE:
                account.saveTrackerCSV(_app.getMarket())
            elif (
                _app.getExchange() == Exchange.COINBASEPRO
                or _app.getExchange() == Exchange.KUCOIN
            ):
                account.saveTrackerCSV()

        if _app.isSimulation():
            if _state.iterations < len(df):
                if _app.simuluationSpeed() in ["fast", "fast-sample"]:
                    # fast processing
                    list(map(s.cancel, s.queue))
                    s.enter(
                        0,
                        1,
                        executeJob,
                        (sc, _app, _state, _technical_analysis, None, df),
                    )
                else:
                    # slow processing
                    list(map(s.cancel, s.queue))
                    s.enter(
                        1,
                        1,
                        executeJob,
                        (sc, _app, _state, _technical_analysis, None, df),
                    )

        else:
            list(map(s.cancel, s.queue))
            if (
                _app.enableWebsocket()
                and _websocket is not None
                and (
                    isinstance(_websocket.tickers, pd.DataFrame)
                    and len(_websocket.tickers) == 1
                )
                and (
                    isinstance(_websocket.candles, pd.DataFrame)
                    and len(_websocket.candles) == 300
                )
            ):
                # poll every 5 seconds (_websocket)
                s.enter(
                    5,
                    1,
                    executeJob,
                    (sc, _app, _state, _technical_analysis, _websocket),
                )
            else:
                if _app.enableWebsocket() and not _app.isSimulation():
                    # poll every 15 seconds (waiting for _websocket)
                    s.enter(
                        15,
                        1,
                        executeJob,
                        (sc, _app, _state, _technical_analysis, _websocket),
                    )
                else:
                    # poll every 1 minute (no _websocket)
                    s.enter(
                        60,
                        1,
                        executeJob,
                        (sc, _app, _state, _technical_analysis, _websocket),
                    )


def main():
    try:
        _websocket = None
        message = "Starting "
        if app.getExchange() == Exchange.COINBASEPRO:
            message += "Coinbase Pro bot"
            if app.enableWebsocket() and not app.isSimulation():
                print("Opening websocket to Coinbase Pro...")
                _websocket = CWebSocketClient([app.getMarket()], app.getGranularity())
                _websocket.start()
        elif app.getExchange() == Exchange.BINANCE:
            message += "Binance bot"
            if app.enableWebsocket() and not app.isSimulation():
                print("Opening websocket to Binance...")
                _websocket = BWebSocketClient([app.getMarket()], app.getGranularity())
                _websocket.start()
        elif app.getExchange() == Exchange.KUCOIN:
            message += "Kucoin bot"
            if app.enableWebsocket() and not app.isSimulation():
                print("Opening websocket to Kucoin...")
                _websocket = KWebSocketClient([app.getMarket()], app.getGranularity())
                _websocket.start()

        smartswitchstatus = "enabled" if app.getSmartSwitch() else "disabled"
        message += f" for {app.getMarket()} using granularity {app.printGranularity()}. Smartswitch {smartswitchstatus}"

        if app.startmethod in ("standard", "telegram"):
            app.notifyTelegram(message)

        # initialise and start application
        trading_data = app.startApp(app, account, state.last_action)

        def runApp(_websocket):
            # run the first job immediately after starting
            if app.isSimulation():
                executeJob(s, app, state, technical_analysis, _websocket, trading_data)
            else:
                executeJob(s, app, state, technical_analysis, _websocket)

            s.run()

        try:
            runApp(_websocket)
        except (KeyboardInterrupt, SystemExit):
            raise
        except (BaseException, Exception) as e:  # pylint: disable=broad-except
            if app.autoRestart():
                # Wait 30 second and try to relaunch application
                time.sleep(30)
                Logger.critical(f"Restarting application after exception: {repr(e)}")

                if not app.disableTelegramErrorMsgs():
                    app.notifyTelegram(
                        f"Auto restarting bot for {app.getMarket()} after exception: {repr(e)}"
                    )

                # Cancel the events queue
                map(s.cancel, s.queue)

                # Restart the app
                runApp(_websocket)
            else:
                raise

    # catches a keyboard break of app, exits gracefully
    except (KeyboardInterrupt, SystemExit):
        if app.enableWebsocket() and not app.isSimulation():
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
            if app.enableWebsocket() and not app.isSimulation():
                _websocket.close()
            sys.exit(0)
        except SystemExit:
            # pylint: disable=protected-access
            os._exit(0)
    except (BaseException, Exception) as e:  # pylint: disable=broad-except
        # catch all not managed exceptions and send a Telegram message if configured
        if not app.disableTelegramErrorMsgs():
            app.notifyTelegram(f"Bot for {app.getMarket()} got an exception: {repr(e)}")
            try:
                telegram_bot.removeactivebot()
            except:
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
