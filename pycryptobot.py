#!/usr/bin/env python3
# encoding: utf-8

"""Python Crypto Bot consuming Coinbase Pro or Binance APIs"""

import functools
import os
import sched
import sys
import time
from datetime import datetime, timedelta

import pandas as pd

from models.AppState import AppState
from models.helper.LogHelper import Logger
from models.helper.MarginHelper import calculate_margin
from models.PyCryptoBot import PyCryptoBot
from models.PyCryptoBot import truncate as _truncate
from models.Stats import Stats
from models.Strategy import Strategy
from models.Trading import TechnicalAnalysis
from models.TradingAccount import TradingAccount
from views.TradingGraphs import TradingGraphs
from models.Strategy import Strategy
from models.helper.LogHelper import Logger
from models.helper.TextBoxHelper import TextBox

# minimal traceback
sys.tracebacklimit = 1

app = PyCryptoBot()
account = TradingAccount(app)
Stats(app, account).show()
technical_analysis = None
state = AppState(app, account)
state.initLastAction()

s = sched.scheduler(time.time, time.sleep)

def executeJob(sc=None, app: PyCryptoBot=None, state: AppState=None, trading_data=pd.DataFrame()):
    """Trading bot job which runs at a scheduled interval"""

    global technical_analysis

    # connectivity check (only when running live)
    if app.isLive() and app.getTime() is None:
        Logger.warning('Bot for ' + app.getMarket() + ' has lost connection to the exchange (will retry in 1 minute)')
        app.notifyTelegram('Bot for ' + app.getMarket() + ' has lost connection to the exchange (will retry in 1 minute)')
        # poll every 1 minute
        list(map(s.cancel, s.queue))
        s.enter(60, 0.25, executeJob, (sc, app, state))
        Logger.warning('Bot for ' + app.getMarket() + ' is attempting to reconnect!')
        app.notifyTelegram('Bot for ' + app.getMarket() + ' is attempting to reconnect!')
        return

    # increment state.iterations
    state.iterations = state.iterations + 1

    if not app.isSimulation():
        # retrieve the app.getMarket() data
        trading_data = app.getHistoricalData(app.getMarket(), app.getGranularity())

    else:
        if len(trading_data) == 0:
            return None

    # analyse the market data
    if app.isSimulation() and len(trading_data.columns) > 8:
        df = trading_data
        if app.appStarted and app.simstartdate is not None:
            # On first run set the iteration to the start date entered
            # This sim mode now pulls 300 candles from before the entered start date 
            state.iterations = df.index.get_loc(str(app.getDateFromISO8601Str(app.simstartdate))) + 1
            app.appStarted = False
        # if smartswitch then get the market data using new granularity
        if app.sim_smartswitch:
            df_last = app.getInterval(df, state.iterations)
            if len(df_last.index.format()) > 0:
                if app.simstartdate is not None:
                    startDate = app.getDateFromISO8601Str(app.simstartdate)
                else:
                    startDate = app.getDateFromISO8601Str(str(df.head(1).index.format()[0]))

                if app.simenddate is not None:
                    if app.simenddate == "now":
                        endDate = app.getDateFromISO8601Str(str(datetime.now()))
                    else:
                        endDate = app.getDateFromISO8601Str(app.simenddate)
                else:
                    endDate = app.getDateFromISO8601Str(str(df.tail(1).index.format()[0]))

                simDate = app.getDateFromISO8601Str(str(df_last.index.format()[0]))

                trading_data = app.getSmartSwitchHistoricalDataChained(app.getMarket(), app.getGranularity(), str(startDate), str(endDate))

                if app.getGranularity() == 3600:
                    simDate = app.getDateFromISO8601Str(str(simDate))
                    sim_rounded = pd.Series(simDate).dt.round('60min')
                    simDate = sim_rounded[0]
                elif app.getGranularity() == 900:
                    simDate = app.getDateFromISO8601Str(str(simDate))
                    sim_rounded = pd.Series(simDate).dt.round('15min')
                    simDate = sim_rounded[0]

                state.iterations = trading_data.index.get_loc(str(simDate))

                if state.iterations == 0:
                    state.iterations = 1
                elif app.getGranularity() == 3600:
                    state.iterations += 2
                elif app.getGranularity() == 900:
                    state.iterations -= 2

                trading_dataCopy = trading_data.copy()
                technical_analysis = TechnicalAnalysis(trading_dataCopy)

                #if 'morning_star' not in df:
                technical_analysis.addAll()

                df = technical_analysis.getDataFrame()

                app.sim_smartswitch = False

        elif app.getSmartSwitch() == 1 and technical_analysis is None:
                trading_dataCopy = trading_data.copy()
                technical_analysis = TechnicalAnalysis(trading_dataCopy)

                if 'morning_star' not in df:
                    technical_analysis.addAll()

                df = technical_analysis.getDataFrame()

    else:

        trading_dataCopy = trading_data.copy()
        technical_analysis = TechnicalAnalysis(trading_dataCopy)
        technical_analysis.addAll()
        df = technical_analysis.getDataFrame()

        if app.isSimulation() and app.appStarted:
            # On first run set the iteration to the start date entered
            # This sim mode now pulls 300 candles from before the entered start date 
            state.iterations = df.index.get_loc(str(app.getDateFromISO8601Str(app.simstartdate))) + 1
            app.appStarted = False

    if app.isSimulation():
        df_last = app.getInterval(df, state.iterations)
    else:
        df_last = app.getInterval(df)

    if len(df_last.index.format()) > 0:
        current_df_index = str(df_last.index.format()[0])
    else:
        current_df_index = state.last_df_index

    formatted_current_df_index = f'{current_df_index} 00:00:00' if len(current_df_index) == 10 else current_df_index

    current_sim_date = formatted_current_df_index

    # use actual sim mode date to check smartchswitch
    if app.getSmartSwitch() == 1 and app.getGranularity() == 3600 and app.is1hEMA1226Bull(current_sim_date) is True and app.is6hEMA1226Bull(current_sim_date) is True:
        Logger.info('*** smart switch from granularity 3600 (1 hour) to 900 (15 min) ***')

        if app.isSimulation():
            app.sim_smartswitch = True

        app.notifyTelegram(app.getMarket() + " smart switch from granularity 3600 (1 hour) to 900 (15 min)")

        app.setGranularity(900)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, executeJob, (sc, app, state))

    # use actual sim mode date to check smartchswitch
    if app.getSmartSwitch() == 1 and app.getGranularity() == 900 and app.is1hEMA1226Bull(current_sim_date) is False and app.is6hEMA1226Bull(current_sim_date) is False:
        Logger.info("*** smart switch from granularity 900 (15 min) to 3600 (1 hour) ***")

        if app.isSimulation():
            app.sim_smartswitch = True

        app.notifyTelegram(app.getMarket() + " smart switch from granularity 900 (15 min) to 3600 (1 hour)")

        app.setGranularity(3600)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, executeJob, (sc, app, state))

    if app.getExchange() == 'binance' and app.getGranularity() == 86400:
        if len(df) < 250:
            # data frame should have 250 rows, if not retry
            Logger.error('error: data frame length is < 250 (' + str(len(df)) + ')')
            list(map(s.cancel, s.queue))
            s.enter(300, 1, executeJob, (sc, app, state))
    else:
        if len(df) < 300:
            if not app.isSimulation():
                # data frame should have 300 rows, if not retry
                Logger.error('error: data frame length is < 300 (' + str(len(df)) + ')')
                list(map(s.cancel, s.queue))
                s.enter(300, 1, executeJob, (sc, app, state))

    if len(df_last) > 0:
        now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        # last_action polling if live
        if app.isLive():
            last_action_current = state.last_action
            state.pollLastAction()
            if last_action_current != state.last_action:
                Logger.info(f'last_action change detected from {last_action_current} to {state.last_action}')
                app.notifyTelegram(f"{app.getMarket} last_action change detected from {last_action_current} to {state.last_action}")

        if not app.isSimulation():
            ticker = app.getTicker(app.getMarket())
            now = ticker[0]
            price = ticker[1]
            if price < df_last['low'].values[0] or price == 0:
                price = float(df_last['close'].values[0])
        else:
            price = float(df_last['close'].values[0])

        if price < 0.0001:
            raise Exception(app.getMarket() + ' is unsuitable for trading, quote price is less than 0.0001!')

        # technical indicators
        ema12gtema26 = bool(df_last['ema12gtema26'].values[0])
        ema12gtema26co = bool(df_last['ema12gtema26co'].values[0])
        goldencross = bool(df_last['goldencross'].values[0])
        macdgtsignal = bool(df_last['macdgtsignal'].values[0])
        macdgtsignalco = bool(df_last['macdgtsignalco'].values[0])
        ema12ltema26 = bool(df_last['ema12ltema26'].values[0])
        ema12ltema26co = bool(df_last['ema12ltema26co'].values[0])
        macdltsignal = bool(df_last['macdltsignal'].values[0])
        macdltsignalco = bool(df_last['macdltsignalco'].values[0])
        obv = float(df_last['obv'].values[0])
        obv_pc = float(df_last['obv_pc'].values[0])
        elder_ray_buy = bool(df_last['eri_buy'].values[0])
        elder_ray_sell = bool(df_last['eri_sell'].values[0])

        # if simulation, set goldencross based on actual sim date
        if app.isSimulation():
            goldencross = app.is1hSMA50200Bull(current_sim_date)

        # candlestick detection
        hammer = bool(df_last['hammer'].values[0])
        inverted_hammer = bool(df_last['inverted_hammer'].values[0])
        hanging_man = bool(df_last['hanging_man'].values[0])
        shooting_star = bool(df_last['shooting_star'].values[0])
        three_white_soldiers = bool(df_last['three_white_soldiers'].values[0])
        three_black_crows = bool(df_last['three_black_crows'].values[0])
        morning_star = bool(df_last['morning_star'].values[0])
        evening_star = bool(df_last['evening_star'].values[0])
        three_line_strike = bool(df_last['three_line_strike'].values[0])
        abandoned_baby = bool(df_last['abandoned_baby'].values[0])
        morning_doji_star = bool(df_last['morning_doji_star'].values[0])
        evening_doji_star = bool(df_last['evening_doji_star'].values[0])
        two_black_gapping = bool(df_last['two_black_gapping'].values[0])

        if app.isSimulation():
            strategy = Strategy(app, state, df[df["date"] <= current_sim_date].tail(300), 299)
        else:
            strategy = Strategy(app, state, df, state.iterations)

        state.action = strategy.getAction(price)

        immediate_action = False
        margin, profit, sell_fee = 0, 0, 0

        # Reset the TA so that the last record is the current sim date 
        # To allow for calculations to be done on the sim date being processed
        if app.isSimulation():
            trading_dataCopy = trading_data[trading_data['date'] <= current_sim_date].tail(300).copy()
            technical_analysis = TechnicalAnalysis(trading_dataCopy)

        if state.last_buy_size > 0 and state.last_buy_price > 0 and price > 0 and state.last_action == 'BUY':
            # update last buy high
            if price > state.last_buy_high:
                state.last_buy_high = price

            if state.last_buy_high > 0:
                change_pcnt_high = ((price / state.last_buy_high) - 1) * 100
            else:
                change_pcnt_high = 0

            # buy and sell calculations
            state.last_buy_fee = round(state.last_buy_size * app.getTakerFee(), 8)
            state.last_buy_filled = round(((state.last_buy_size - state.last_buy_fee) / state.last_buy_price), 8)

            # if not a simulation, sync with exchange orders
            if not app.isSimulation():
                exchange_last_buy = app.getLastBuy()
                if exchange_last_buy is not None:
                    if state.last_buy_size != exchange_last_buy['size']:
                        state.last_buy_size = exchange_last_buy['size']
                    if state.last_buy_filled != exchange_last_buy['filled']:
                        state.last_buy_filled = exchange_last_buy['filled']
                    if state.last_buy_price != exchange_last_buy['price']:
                        state.last_buy_price = exchange_last_buy['price']

                    if app.getExchange() == 'coinbasepro':
                        if state.last_buy_fee != exchange_last_buy['fee']:
                            state.last_buy_fee = exchange_last_buy['fee']

            margin, profit, sell_fee = calculate_margin(
                buy_size=state.last_buy_size,
                buy_filled=state.last_buy_filled,
                buy_price=state.last_buy_price,
                buy_fee=state.last_buy_fee,
                sell_percent=app.getSellPercent(),
                sell_price=price,
                sell_taker_fee=app.getTakerFee())

            # handle immedate sell actions
            if strategy.isSellTrigger(price, technical_analysis.getTradeExit(price), margin, change_pcnt_high, obv_pc, macdltsignal):
                state.action = 'SELL'
                state.last_action = 'BUY'
                immediate_action = True

            # handle overriding wait actions (e.g. do not sell if sell at loss disabled!, do not buy in bull if bull only)
            if strategy.isWaitTrigger(margin, goldencross):
                state.action = 'WAIT'
                immediate_action = False

        bullbeartext = ''
        if app.disableBullOnly() is True or (df_last['sma50'].values[0] == df_last['sma200'].values[0]):
            bullbeartext = ''
        elif goldencross is True:
            bullbeartext = ' (BULL)'
        elif goldencross is False:
            bullbeartext = ' (BEAR)'

        # polling is every 5 minutes (even for hourly intervals), but only process once per interval
        #Logger.debug("DateCheck: " + str(immediate_action) + ' ' + str(state.last_df_index) + ' ' + str(current_df_index))
        if (immediate_action is True or state.last_df_index != current_df_index):
            textBox = TextBox(80, 22)

            precision = 4

            if (price < 0.01):
                precision = 8

            # Since precision does not change after this point, it is safe to prepare a tailored `truncate()` that would
            # work with this precision. It should save a couple of `precision` uses, one for each `truncate()` call.
            truncate = functools.partial(_truncate, n=precision)

            price_text = 'Close: ' + truncate(price)
            ema_text=''
            if app.disableBuyEMA() is False:
                ema_text = app.compare(df_last['ema12'].values[0], df_last['ema26'].values[0], 'EMA12/26', precision)

            macd_text = ''
            if app.disableBuyMACD() is False:
                macd_text = app.compare(df_last['macd'].values[0], df_last['signal'].values[0], 'MACD', precision)

            obv_text = ''
            if app.disableBuyOBV() is False:
                obv_text = 'OBV: ' + truncate(df_last['obv'].values[0]) + ' (' + str(
                    truncate(df_last['obv_pc'].values[0])) + '%)'

            state.eri_text = ''
            if app.disableBuyElderRay() is False:
                if elder_ray_buy is True:
                    state.eri_text = 'ERI: buy | '
                elif elder_ray_sell is True:
                    state.eri_text = 'ERI: sell | '
                else:
                    state.eri_text = 'ERI: | '

            if hammer is True:
                log_text = '* Candlestick Detected: Hammer ("Weak - Reversal - Bullish Signal - Up")'
                Logger.info(log_text)

            if shooting_star is True:
                log_text = '* Candlestick Detected: Shooting Star ("Weak - Reversal - Bearish Pattern - Down")'
                Logger.info(log_text)

            if hanging_man is True:
                log_text = '* Candlestick Detected: Hanging Man ("Weak - Continuation - Bearish Pattern - Down")'
                Logger.info(log_text)

            if inverted_hammer is True:
                log_text = '* Candlestick Detected: Inverted Hammer ("Weak - Continuation - Bullish Pattern - Up")'
                Logger.info(log_text)

            if three_white_soldiers is True:
                log_text = '*** Candlestick Detected: Three White Soldiers ("Strong - Reversal - Bullish Pattern - Up")'
                Logger.info(log_text)

                app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') ' + log_text)

            if three_black_crows is True:
                log_text = '* Candlestick Detected: Three Black Crows ("Strong - Reversal - Bearish Pattern - Down")'
                Logger.info(log_text)

                app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') ' + log_text)

            if morning_star is True:
                log_text = '*** Candlestick Detected: Morning Star ("Strong - Reversal - Bullish Pattern - Up")'
                Logger.info(log_text)

                app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') ' + log_text)

            if evening_star is True:
                log_text = '*** Candlestick Detected: Evening Star ("Strong - Reversal - Bearish Pattern - Down")'
                Logger.info(log_text)

                app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') ' + log_text)

            if three_line_strike is True:
                log_text = '** Candlestick Detected: Three Line Strike ("Reliable - Reversal - Bullish Pattern - Up")'
                Logger.info(log_text)

                app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') ' + log_text)

            if abandoned_baby is True:
                log_text = '** Candlestick Detected: Abandoned Baby ("Reliable - Reversal - Bullish Pattern - Up")'
                Logger.info(log_text)

                app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') ' + log_text)

            if morning_doji_star is True:
                log_text = '** Candlestick Detected: Morning Doji Star ("Reliable - Reversal - Bullish Pattern - Up")'
                Logger.info(log_text)

                app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') ' + log_text)

            if evening_doji_star is True:
                log_text = '** Candlestick Detected: Evening Doji Star ("Reliable - Reversal - Bearish Pattern - Down")'
                Logger.info(log_text)

                app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') ' + log_text)

            if two_black_gapping is True:
                log_text = '*** Candlestick Detected: Two Black Gapping ("Reliable - Reversal - Bearish Pattern - Down")'
                Logger.info(log_text)

                app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') ' + log_text)

            ema_co_prefix = ''
            ema_co_suffix = ''
            if app.disableBuyEMA() is False:
                if ema12gtema26co is True:
                    ema_co_prefix = '*^ '
                    ema_co_suffix = ' ^* | '
                elif ema12ltema26co is True:
                    ema_co_prefix = '*v '
                    ema_co_suffix = ' v* | '
                elif ema12gtema26 is True:
                    ema_co_prefix = '^ '
                    ema_co_suffix = ' ^ | '
                elif ema12ltema26 is True:
                    ema_co_prefix = 'v '
                    ema_co_suffix = ' v | '

            macd_co_prefix = ''
            macd_co_suffix = ''
            if app.disableBuyMACD() is False:
                if macdgtsignalco is True:
                    macd_co_prefix = '*^ '
                    macd_co_suffix = ' ^* | '
                elif macdltsignalco is True:
                    macd_co_prefix = '*v '
                    macd_co_suffix = ' v* | '
                elif macdgtsignal is True:
                    macd_co_prefix = '^ '
                    macd_co_suffix = ' ^ | '
                elif macdltsignal is True:
                    macd_co_prefix = 'v '
                    macd_co_suffix = ' v | '

            obv_prefix = ''
            obv_suffix = ''
            if app.disableBuyOBV() is False:
                if float(obv_pc) > 0:
                    obv_prefix = '^ '
                    obv_suffix = ' ^ | '
                elif float(obv_pc) < 0:
                    obv_prefix = 'v '
                    obv_suffix = ' v | '
                else:
                    obv_suffix = ' | '

            if not app.isVerbose():
                if state.last_action != '':
                    # Not sure if this if is needed just preserving any exisitng functionality that may have been missed
                    # Updated to show over margin and profit
                    if not app.isSimulation:
                        output_text = formatted_current_df_index + ' | ' + app.getMarket() + bullbeartext + ' | ' + \
                                  app.printGranularity() + ' | ' + price_text + ' | ' + ema_co_prefix + \
                                  ema_text + ema_co_suffix + macd_co_prefix + macd_text + macd_co_suffix + \
                                  obv_prefix + obv_text + obv_suffix + state.eri_text + state.action + \
                                  ' | Last Action: ' + state.last_action + ' | DF HIGH: ' + str(df['close'].max()) + ' | ' + 'DF LOW: ' + str(df['close'].min()) + ' | SWING: ' +str(round(((df['close'].max()-df['close'].min()) / df['close'].min())*100, 2)) + '% |' + \
                                  ' CURR Price is ' + str(round(((price-df['close'].max()) / df['close'].max())*100, 2)) + '% ' + 'away from DF HIGH | Range: ' + str(df.iloc[0, 0]) + ' <--> ' + str(df.iloc[len(df)-1, 0])
                    else:
                        df_high = df[df['date'] <= current_sim_date]['close'].max()
                        df_low = df[df['date'] <= current_sim_date]['close'].min()
                        #print(df_high)
                        output_text = formatted_current_df_index + ' | ' + app.getMarket() + bullbeartext + ' | ' + \
                                  app.printGranularity() + ' | ' + price_text + ' | ' + ema_co_prefix + \
                                  ema_text + ema_co_suffix + macd_co_prefix + macd_text + macd_co_suffix + \
                                  obv_prefix + obv_text + obv_suffix + state.eri_text + state.action + \
                                  ' | Last Action: ' + state.last_action + ' | DF HIGH: ' + str(df_high) + ' | ' + 'DF LOW: ' + str(df_low) + ' | SWING: ' +str(round(((df_high-df_low) / df_low)*100, 2)) + '% |' + \
                                  ' CURR Price is ' + str(round(((price-df_high) / df_high)*100, 2)) + '% ' + 'away from DF HIGH | Range: ' + str(df.iloc[state.iterations-300, 0]) + ' <--> ' + str(df.iloc[state.iterations-1, 0])
                else:
                    if not app.isSimulation:
                        output_text = formatted_current_df_index + ' | ' + app.getMarket() + bullbeartext + ' | ' + \
                                  app.printGranularity() + ' | ' + price_text + ' | ' + ema_co_prefix + \
                                  ema_text + ema_co_suffix + macd_co_prefix + macd_text + macd_co_suffix + \
                                  obv_prefix + obv_text + obv_suffix + state.eri_text + state.action + ' | DF HIGH: ' + str(df['close'].max()) + ' | ' + 'DF LOW: ' + str(df['close'].min()) + ' | SWING: ' +str(round(((df['close'].max()-df['close'].min()) / df['close'].min())*100, 2)) + '%' + \
                                  ' CURR Price is ' + str(round(((price-df['close'].max()) / df['close'].max())*100, 2)) + '% ' + 'away from DF HIGH | Range: ' +str(df.iloc[0, 0]) + ' <--> ' +str(df.iloc[len(df)-1, 0])
                    else:
                        df_high = df[df['date'] <= current_sim_date]['close'].max()
                        df_low = df[df['date'] <= current_sim_date]['close'].min()

                        output_text = formatted_current_df_index + ' | ' + app.getMarket() + bullbeartext + ' | ' + \
                                  app.printGranularity() + ' | ' + price_text + ' | ' + ema_co_prefix + \
                                  ema_text + ema_co_suffix + macd_co_prefix + macd_text + macd_co_suffix + \
                                  obv_prefix + obv_text + obv_suffix + state.eri_text + state.action + ' | DF HIGH: ' + str(df_high) + ' | ' + 'DF LOW: ' + str(df_low) + ' | SWING: ' +str(round(((df_high-df_low) / df_low)*100, 2)) + '%' + \
                                  ' CURR Price is ' + str(round(((price-df_high) / df_high)*100, 2)) + '% ' + 'away from DF HIGH | Range: ' +str(df.iloc[state.iterations-300, 0]) + ' <--> ' + str(df.iloc[state.iterations-1, 0])
                if state.last_action == 'BUY':
                    if state.last_buy_size > 0:
                        margin_text = truncate(margin) + '%'
                    else:
                        margin_text = '0%'

                    output_text += ' | ' + margin_text + ' (delta: ' + str(round(price - state.last_buy_price, precision)) + ')'

                Logger.info(output_text)

                # Seasonal Autoregressive Integrated Moving Average (ARIMA) model (ML prediction for 3 intervals from now)
                if not app.isSimulation():
                    try:
                        prediction = technical_analysis.seasonalARIMAModelPrediction(int(app.getGranularity() / 60) * 3) # 3 intervals from now
                        Logger.info(f'Seasonal ARIMA model predicts the closing price will be {str(round(prediction[1], 2))} at {prediction[0]} (delta: {round(prediction[1] - price, 2)})')
                    except:
                        pass

                if state.last_action == 'BUY':
                    # display support, resistance and fibonacci levels
                    Logger.info(technical_analysis.printSupportResistanceFibonacciLevels(price))

            else:
                Logger.debug('-- Iteration: ' + str(state.iterations) + ' --' + bullbeartext)

                if state.last_action == 'BUY':
                    if state.last_buy_size > 0:
                        margin_text = truncate(margin) + '%'
                    else:
                        margin_text = '0%'

                    Logger.debug('-- Margin: ' + margin_text + ' --')

                Logger.debug('price: ' + truncate(price))
                Logger.debug('ema12: ' + truncate(float(df_last['ema12'].values[0])))
                Logger.debug('ema26: ' + truncate(float(df_last['ema26'].values[0])))
                Logger.debug('ema12gtema26co: ' + str(ema12gtema26co))
                Logger.debug('ema12gtema26: ' + str(ema12gtema26))
                Logger.debug('ema12ltema26co: ' + str(ema12ltema26co))
                Logger.debug('ema12ltema26: ' + str(ema12ltema26))
                Logger.debug('sma50: ' + truncate(float(df_last['sma50'].values[0])))
                Logger.debug('sma200: ' + truncate(float(df_last['sma200'].values[0])))
                Logger.debug('macd: ' + truncate(float(df_last['macd'].values[0])))
                Logger.debug('signal: ' + truncate(float(df_last['signal'].values[0])))
                Logger.debug('macdgtsignal: ' + str(macdgtsignal))
                Logger.debug('macdltsignal: ' + str(macdltsignal))
                Logger.debug('obv: ' + str(obv))
                Logger.debug('obv_pc: ' + str(obv_pc))
                Logger.debug('action: ' + state.action)

                # informational output on the most recent entry
                Logger.info('')
                textBox.doubleLine()
                textBox.line('Iteration', str(state.iterations) + bullbeartext)
                textBox.line('Timestamp', str(df_last.index.format()[0]))
                textBox.singleLine()
                textBox.line('Close', truncate(price))
                textBox.line('EMA12', truncate(float(df_last['ema12'].values[0])))
                textBox.line('EMA26', truncate(float(df_last['ema26'].values[0])))
                textBox.line('Crossing Above', str(ema12gtema26co))
                textBox.line('Currently Above', str(ema12gtema26))
                textBox.line('Crossing Below', str(ema12ltema26co))
                textBox.line('Currently Below', str(ema12ltema26))

                if (ema12gtema26 is True and ema12gtema26co is True):
                    textBox.line('Condition', 'EMA12 is currently crossing above EMA26')
                elif (ema12gtema26 is True and ema12gtema26co is False):
                    textBox.line('Condition', 'EMA12 is currently above EMA26 and has crossed over')
                elif (ema12ltema26 is True and ema12ltema26co is True):
                    textBox.line('Condition', 'EMA12 is currently crossing below EMA26')
                elif (ema12ltema26 is True and ema12ltema26co is False):
                    textBox.line('Condition', 'EMA12 is currently below EMA26 and has crossed over')
                else:
                    textBox.line('Condition', '-')

                textBox.line('SMA20', truncate(float(df_last['sma20'].values[0])))
                textBox.line('SMA200', truncate(float(df_last['sma200'].values[0])))
                textBox.singleLine()
                textBox.line('MACD', truncate(float(df_last['macd'].values[0])))
                textBox.line('Signal', truncate(float(df_last['signal'].values[0])))
                textBox.line('Currently Above', str(macdgtsignal))
                textBox.line('Currently Below', str(macdltsignal))

                if (macdgtsignal is True and macdgtsignalco is True):
                    textBox.line('Condition', 'MACD is currently crossing above Signal')
                elif (macdgtsignal is True and macdgtsignalco is False):
                    textBox.line('Condition', 'MACD is currently above Signal and has crossed over')
                elif (macdltsignal is True and macdltsignalco is True):
                    textBox.line('Condition', 'MACD is currently crossing below Signal')
                elif (macdltsignal is True and macdltsignalco is False):
                    textBox.line('Condition', 'MACD is currently below Signal and has crossed over')
                else:
                    textBox.line('Condition', '-')

                textBox.singleLine()
                textBox.line('Action', state.action)
                textBox.doubleLine()
                if state.last_action == 'BUY':
                    textBox.line('Margin', margin_text)
                    textBox.doubleLine()

            # if a buy signal
            if state.action == 'BUY':
                state.last_buy_price = price
                state.last_buy_high = state.last_buy_price

                # if live
                if app.isLive():
                    app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') BUY at ' + price_text)

                    if not app.isVerbose():
                        Logger.info(formatted_current_df_index + ' | ' + app.getMarket() + ' | ' + app.printGranularity() +  ' | ' + price_text + ' | BUY')
                    else:
                        textBox.singleLine()
                        textBox.center('*** Executing LIVE Buy Order ***')
                        textBox.singleLine()

                    # display balances
                    Logger.info(app.getBaseCurrency() + ' balance before order: ' + str(account.getBalance(app.getBaseCurrency())))
                    Logger.info(app.getQuoteCurrency() + ' balance before order: ' + str(account.getBalance(app.getQuoteCurrency())))

                    # execute a live market buy
                    state.last_buy_size = float(account.getBalance(app.getQuoteCurrency()))
                    if app.getBuyMaxSize() and state.last_buy_size > app.getBuyMaxSize():
                        state.last_buy_size = app.getBuyMaxSize()

                    resp = app.marketBuy(app.getMarket(), state.last_buy_size, app.getBuyPercent())
                    Logger.debug(resp)

                    # display balances
                    Logger.info(app.getBaseCurrency() + ' balance after order: ' + str(account.getBalance(app.getBaseCurrency())))
                    Logger.info(app.getQuoteCurrency() + ' balance after order: ' + str(account.getBalance(app.getQuoteCurrency())))
                # if not live
                else:
                    app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') TEST BUY at ' + price_text)
                    if state.last_buy_size == 0 and state.last_buy_filled == 0:
                        # Sim mode can now use buymaxsize as the amount used for a buy
                        if app.getBuyMaxSize() != None:
                            state.last_buy_size = app.getBuyMaxSize()
                            state.first_buy_size = app.getBuyMaxSize()
                        else:
                            state.last_buy_size = 1000
                            state.first_buy_size = 1000

                    state.buy_count = state.buy_count + 1
                    state.buy_sum = state.buy_sum + state.last_buy_size

                    if not app.isVerbose():
                        Logger.info(formatted_current_df_index + ' | ' + app.getMarket() + ' | ' + app.printGranularity() + ' | ' + price_text + ' | BUY')

                        bands = technical_analysis.getFibonacciRetracementLevels(float(price))
                        technical_analysis.printSupportResistanceLevel(float(price))

                        Logger.info(' Fibonacci Retracement Levels:' + str(bands))

                        if len(bands) >= 1 and len(bands) <= 2:
                            if len(bands) == 1:
                                first_key = list(bands.keys())[0]
                                if first_key == 'ratio1':
                                    state.fib_low = 0
                                    state.fib_high = bands[first_key]
                                if first_key == 'ratio1_618':
                                    state.fib_low = bands[first_key]
                                    state.fib_high = bands[first_key] * 2
                                else:
                                    state.fib_low = bands[first_key]

                            elif len(bands) == 2:
                                first_key = list(bands.keys())[0]
                                second_key = list(bands.keys())[1]
                                state.fib_low = bands[first_key]
                                state.fib_high = bands[second_key]

                    else:
                        textBox.singleLine()
                        textBox.center('*** Executing TEST Buy Order ***')
                        textBox.singleLine()

                    app.trade_tracker = app.trade_tracker.append(
                        {
                            "Datetime": str(current_sim_date),
                            "Market": app.getMarket(),
                            "Action": "BUY",
                            "Price": price,
                            "Quote": state.last_buy_size,
                            "Base": float(state.last_buy_size) / float(price),
                            "DF_High": df[df['date'] <= current_sim_date]['close'].max(),
                            "DF_Low": df[df['date'] <= current_sim_date]['close'].min()}
                            , ignore_index=True
                                )

                if app.shouldSaveGraphs():
                    tradinggraphs = TradingGraphs(technical_analysis)
                    ts = datetime.now().timestamp()
                    filename = app.getMarket() + '_' + app.printGranularity() + '_buy_' + str(ts) + '.png'
                    # This allows graphs to be used in sim mode using the correct DF
                    if app.isSimulation:
                        tradinggraphs.renderEMAandMACD(len(trading_dataCopy), 'graphs/' + filename, True)
                    else:
                        tradinggraphs.renderEMAandMACD(len(trading_data), 'graphs/' + filename, True)

            # if a sell signal
            elif state.action == 'SELL':
                # if live
                if app.isLive():
                    app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') SELL at ' +
                                      price_text + ' (margin: ' + margin_text + ', (delta: ' +
                                      str(round(price - state.last_buy_price, precision)) + ')')

                    if not app.isVerbose():
                        Logger.info(formatted_current_df_index + ' | ' + app.getMarket() + ' | ' + app.printGranularity() + ' | ' + price_text + ' | SELL')

                        bands = technical_analysis.getFibonacciRetracementLevels(float(price))
                        Logger.info(' Fibonacci Retracement Levels:' + str(bands))

                        if len(bands) >= 1 and len(bands) <= 2:
                            if len(bands) == 1:
                                first_key = list(bands.keys())[0]
                                if first_key == 'ratio1':
                                    state.fib_low = 0
                                    state.fib_high = bands[first_key]
                                if first_key == 'ratio1_618':
                                    state.fib_low = bands[first_key]
                                    state.fib_high = bands[first_key] * 2
                                else:
                                    state.fib_low = bands[first_key]

                            elif len(bands) == 2:
                                first_key = list(bands.keys())[0]
                                second_key = list(bands.keys())[1]
                                state.fib_low = bands[first_key]
                                state.fib_high = bands[second_key]

                    else:
                        textBox.singleLine()
                        textBox.center('*** Executing LIVE Sell Order ***')
                        textBox.singleLine()

                    # display balances
                    Logger.info(app.getBaseCurrency() + ' balance before order: ' + str(account.getBalance(app.getBaseCurrency())))
                    Logger.info(app.getQuoteCurrency() + ' balance before order: ' + str(account.getBalance(app.getQuoteCurrency())))

                    # execute a live market sell
                    resp = app.marketSell(app.getMarket(), float(account.getBalance(app.getBaseCurrency())), app.getSellPercent())
                    Logger.debug(resp)

                    # display balances
                    Logger.info(app.getBaseCurrency() + ' balance after order: ' + str(account.getBalance(app.getBaseCurrency())))
                    Logger.info(app.getQuoteCurrency() + ' balance after order: ' + str(account.getBalance(app.getQuoteCurrency())))

                # if not live
                else:
                    margin, profit, sell_fee = calculate_margin(
                        buy_size=state.last_buy_size,
                        buy_filled=state.last_buy_filled,
                        buy_price=state.last_buy_price,
                        buy_fee=state.last_buy_fee,
                        sell_percent=app.getSellPercent(),
                        sell_price=price,
                        sell_taker_fee=app.getTakerFee())

                    if state.last_buy_size > 0:
                        margin_text = truncate(margin) + '%'
                    else:
                        margin_text = '0%'

                    app.notifyTelegram(app.getMarket() + ' (' + app.printGranularity() + ') TEST SELL at ' +
                                      price_text + ' (margin: ' + margin_text + ', (delta: ' +
                                      str(round(price - state.last_buy_price, precision)) + ')')

                    # preserve next sell values for simulator
                    state.sell_count = state.sell_count + 1
                    sell_size = ((app.getSellPercent() / 100) * ((price / state.last_buy_price) * (state.last_buy_size - state.last_buy_fee)))
                    state.last_sell_size = sell_size - sell_fee
                    state.sell_sum = state.sell_sum + state.last_sell_size

                    # Added to track profit and loss margins during sim runs
                    state.margintracker += float(margin)
                    state.profitlosstracker += float(profit)
                    state.feetracker += float(sell_fee)
                    state.buy_tracker += float(state.last_sell_size)

                    if not app.isVerbose():
                        if price > 0:
                            margin_text = truncate(margin) + '%'
                        else:
                            margin_text = '0%'

                        Logger.info(formatted_current_df_index + ' | ' + app.getMarket() + ' | ' +
                                     app.printGranularity() + ' | SELL | ' + str(price) + ' | BUY | ' +
                                     str(state.last_buy_price) + ' | DIFF | ' + str(price - state.last_buy_price) +
                                     ' | DIFF | ' + str(profit) + ' | MARGIN NO FEES | ' +
                                     margin_text + ' | MARGIN FEES | ' + str(round(sell_fee, precision)))

                    else:
                        textBox.singleLine()
                        textBox.center('*** Executing TEST Sell Order ***')
                        textBox.singleLine()

                    app.trade_tracker = app.trade_tracker.append(
                        {
                            "Datetime": str(current_sim_date),
                            "Market": app.getMarket(),
                            "Action": "SELL",
                            "Price": price,
                            "Quote": state.last_sell_size,
                            "Base": state.last_buy_filled,
                            "Margin": margin,
                            "Profit": profit,
                            "Fee": sell_fee,
                            "DF_High": df[df['date'] <= current_sim_date]['close'].max(),
                            "DF_Low": df[df['date'] <= current_sim_date]['close'].min()}
                            , ignore_index=True
                        )
                if app.shouldSaveGraphs():
                    tradinggraphs = TradingGraphs(technical_analysis)
                    ts = datetime.now().timestamp()
                    filename = app.getMarket() + '_' + app.printGranularity() + '_sell_' + str(ts) + '.png'
                    # This allows graphs to be used in sim mode using the correct DF
                    if app.isSimulation():
                        tradinggraphs.renderEMAandMACD(len(trading_dataCopy), 'graphs/' + filename, True)
                    else:
                        tradinggraphs.renderEMAandMACD(len(trading_data), 'graphs/' + filename, True)

            # last significant action
            if state.action in ['BUY', 'SELL']:
                state.last_action = state.action

            state.last_df_index = str(df_last.index.format()[0])

            if not app.isLive() and state.iterations == len(df):
                Logger.info("\nSimulation Summary: ")

                if app.isVerbose():
                    Logger.info("\n" + str(app.trade_tracker))
                    if app.simuluationSpeed() == "fast":
                        start = str(df.head(1).index.format()[0]).replace(":", ".")
                        end = str(df.tail(1).index.format()[0]).replace(":", ".")
                        filename = f"{app.getMarket()} {str(start)} - {str(end)}_trades.csv"
                    else:
                        filename = f"{app.getMarket()} {str(app.simstartdate)} - {str(app.simenddate)}_trades.csv"
                else:
                    filename = "trades.csv"
                try:
                    app.trade_tracker.to_csv(filename)
                except OSError:
                    Logger.critical(f"Unable to save: {filename}")

                if state.buy_count == 0:
                    state.last_buy_size = 0
                    state.sell_sum = 0
                else:
                    # calculate last sell size
                    state.last_buy_size = ((app.getSellPercent() / 100) * ((price / state.last_buy_price) * (state.last_buy_size - state.last_buy_fee)))

                    # reduce sell fee from last sell size
                    state.last_buy_size = state.last_buy_size - state.last_buy_price * app.getTakerFee()
                    state.sell_sum = state.sell_sum + state.last_buy_size

                remove_last_buy = False
                if state.buy_count > state.sell_count:
                    remove_last_buy = True
                    state.buy_count -= 1 # remove last buy as there has not been a corresponding sell yet

                    Logger.info("\nWarning: simulation ended with an open trade and it will be excluded from the margin calculation.")
                    Logger.info("         (it is not realistic to hard sell at the end of a simulation without a sell signal)")

                Logger.info("\n")
                if remove_last_buy is True:
                    Logger.info('   Buy Count : ' + str(state.buy_count) + ' (open buy excluded)')
                else:
                    Logger.info('   Buy Count : ' + str(state.buy_count))
                Logger.info('  Sell Count : ' + str(state.sell_count))
                Logger.info('   First Buy : ' + str(state.first_buy_size))

                if state.sell_count > 0:
                    Logger.info('   Last Sell : ' + _truncate(state.last_sell_size, 2) + "\n")
                else:
                    Logger.info("\n")
                    Logger.info('      Margin : 0.00%')
                    Logger.info("\n")
                    Logger.info("  ** margin is nil as a sell as not occurred during the simulation\n")
                    app.notifyTelegram(f"      Margin: 0.00%\n  ** margin is nil as a sell as not occurred during the simulation\n")

                app.notifyTelegram(f"Simulation Summary\n   Buy Count: {state.buy_count}\n   Sell Count: {state.sell_count}\n   First Buy: {state.first_buy_size}\n   Last Buy: {state.last_buy_size}\n")

                if state.sell_count > 0:
                    Logger.info('   Last Trade Margin : ' + _truncate((((state.last_sell_size - state.first_buy_size) / state.first_buy_size) * 100), 4) + '%')
                    Logger.info("\n")
                    Logger.info('   All Trades Buys (' + app.quote_currency + '): ' + _truncate(state.buy_tracker, 2))
                    Logger.info('   All Trades Profit/Loss (' + app.quote_currency + '): ' + _truncate(state.profitlosstracker, 2) + " (" + _truncate(state.feetracker,2) + " in fees)")
                    Logger.info('   All Trades Margin : ' + _truncate(state.margintracker, 4) + '%')
                    Logger.info("\n")
                    Logger.info("  ** non-live simulation, assuming highest fees")
                    Logger.info("  ** open trade excluded from margin calculation\n")
                    app.notifyTelegram(f"      Margin: {_truncate((((state.last_sell_size - state.first_buy_size) / state.first_buy_size) * 100), 4)}%\n  ** non-live simulation, assuming highest fees\n  ** open trade excluded from margin calculation\n")
        else:
            if state.last_buy_size > 0 and state.last_buy_price > 0 and price > 0 and state.last_action == 'BUY':
                # show profit and margin if already bought
                Logger.info(now + ' | ' + app.getMarket() + bullbeartext + ' | ' + app.printGranularity() + ' | Current Price: ' + str(price) + ' | Margin: ' + str(margin) + ' | Profit: ' + str(profit))
            else:
                Logger.info(now + ' | ' + app.getMarket() + bullbeartext + ' | ' + app.printGranularity() + ' | Current Price: ' + str(price) +' is ' + str(round(((price-df['close'].max()) / df['close'].max())*100, 2)) + '% ' + 'away from DF HIGH')

            # decrement ignored iteration
            state.iterations = state.iterations - 1

        # if live
        if not app.disableTracker() and app.isLive():
            # update order tracker csv
            if app.getExchange() == 'binance':
                account.saveTrackerCSV(app.getMarket())
            elif app.getExchange() == 'coinbasepro':
                account.saveTrackerCSV()

        if app.isSimulation():
            if state.iterations < len(df):
                if app.simuluationSpeed() in ['fast', 'fast-sample']:
                    # fast processing
                    list(map(s.cancel, s.queue))
                    s.enter(0, 1, executeJob, (sc, app, state, df))
                else:
                    # slow processing
                    list(map(s.cancel, s.queue))
                    s.enter(1, 1, executeJob, (sc, app, state, df))

        else:
            # poll every 1 minute
            list(map(s.cancel, s.queue))
            s.enter(60, 1, executeJob, (sc, app, state))


def main():
    try:

        message = 'Starting '
        if app.getExchange() == 'coinbasepro':
            message += 'Coinbase Pro bot'
        elif app.getExchange() == 'binance':
            message += 'Binance bot'

        smartSwitchStatus = 'enabled' if app.getSmartSwitch() else 'disabled'
        message += ' for ' + app.getMarket() + ' using granularity ' + app.printGranularity() + '. Smartswitch ' + smartSwitchStatus
        app.notifyTelegram(message)

        # initialise and start application
        trading_data = app.startApp(account, state.last_action)

        def runApp():
            # run the first job immediately after starting
            if app.isSimulation():
                executeJob(s, app, state, trading_data)
            else:
                executeJob(s, app, state)

            s.run()

        try:
            runApp()
        except KeyboardInterrupt:
            raise
        except(BaseException, Exception) as e:
            if app.autoRestart():
                # Wait 30 second and try to relaunch application
                time.sleep(30)
                Logger.critical('Restarting application after exception: ' + repr(e))

                app.notifyTelegram('Auto restarting bot for ' + app.getMarket() + ' after exception: ' + repr(e))

                # Cancel the events queue
                map(s.cancel, s.queue)

                # Restart the app
                runApp()
            else:
                raise

    # catches a keyboard break of app, exits gracefully
    except KeyboardInterrupt:
        Logger.warning(str(datetime.now()) + ' bot is closed via keyboard interrupt...')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except(BaseException, Exception) as e:
        # catch all not managed exceptions and send a Telegram message if configured
        app.notifyTelegram('Bot for ' + app.getMarket() + ' got an exception: ' + repr(e))

        Logger.critical(repr(e))

        raise


main()
