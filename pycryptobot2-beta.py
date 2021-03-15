"""Python Crypto Bot consuming Coinbase Pro or Binance APIs"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging, os, random, sched, sys, time

from models.PyCryptoBot import PyCryptoBot
from models.Trading import TechnicalAnalysis
from models.TradingAccount import TradingAccount
from views.TradingGraphs import TradingGraphs

# production: disable traceback
#sys.tracebacklimit = 0

app = PyCryptoBot()
s = sched.scheduler(time.time, time.sleep)

# initial state is to wait
action = 'WAIT'
last_action = ''
last_df_index = ''
buy_state = ''
last_buy = 0
iterations = 0
buy_count = 0
sell_count = 0
buy_sum = 0
sell_sum = 0
fib_high = 0
fib_low = 0

config = {}
account = None
# if live trading is enabled
if app.isLive() == 1:
    account = TradingAccount(app)

    if account.getBalance(app.getBaseCurrency()) < account.getBalance(app.getQuoteCurrency()):
        last_action = 'SELL'
    elif account.getBalance(app.getBaseCurrency()) > account.getBalance(app.getQuoteCurrency()):
        last_action = 'BUY'

    if app.getExchange() == 'binance':
        if last_action == 'SELL'and account.getBalance(app.getQuoteCurrency()) < 0.001:
            raise Exception('Insufficient available funds to place sell order: ' + str(account.getBalance(app.getQuoteCurrency())) + ' < 0.1 ' + app.getQuoteCurrency() + "\nNote: A manual limit order places a hold on available funds.")
        elif last_action == 'BUY'and account.getBalance(app.getBaseCurrency()) < 0.001:
            raise Exception('Insufficient available funds to place buy order: ' + str(account.getBalance(app.getBaseCurrency())) + ' < 0.1 ' + app.getBaseCurrency() + "\nNote: A manual limit order places a hold on available funds.")
 
    elif app.getExchange() == 'coinbasepro':
        if last_action == 'SELL'and account.getBalance(app.getQuoteCurrency()) < 50:
            raise Exception('Insufficient available funds to place buy order: ' + str(account.getBalance(app.getQuoteCurrency())) + ' < 50 ' + app.getQuoteCurrency() + "\nNote: A manual limit order places a hold on available funds.")
        elif last_action == 'BUY'and account.getBalance(app.getBaseCurrency()) < 0.001:
            raise Exception('Insufficient available funds to place sell order: ' + str(account.getBalance(app.getBaseCurrency())) + ' < 0.1 ' + app.getBaseCurrency() + "\nNote: A manual limit order places a hold on available funds.")

    orders = account.getOrders(app.getMarket(), '', 'done')
    if len(orders) > 0:
        df = orders[-1:]

        if str(df.action.values[0]) == 'buy':
            last_buy = float(df[df.action == 'buy']['price'])
        else:
            last_buy = 0.0

def executeJob(sc, app=PyCryptoBot(), trading_data=pd.DataFrame()):
    """Trading bot job which runs at a scheduled interval"""
    global action, buy_count, buy_sum, iterations, last_action, last_buy, last_df_index, sell_count, sell_sum, buy_state, fib_high, fib_low

    # increment iterations
    iterations = iterations + 1

    if app.isSimulation() == 0:
        # retrieve the app.getMarket() data
        trading_data = app.getHistoricalData(app.getMarket(), app.getGranularity())
    else:
        if len(trading_data) == 0:
            return None

    # analyse the market data
    trading_dataCopy = trading_data.copy()
    ta = TechnicalAnalysis(trading_dataCopy)
    ta.addAll()
    df = ta.getDataFrame()

    if app.isSimulation() == 1:
        # with a simulation df_last will iterate through data
        df_last = df.iloc[iterations-1:iterations]
    else:
        # df_last contains the most recent entry
        df_last = df.tail(1)
    
    if len(df_last.index.format()) > 0:
        current_df_index = str(df_last.index.format()[0])
    else:
        current_df_index = last_df_index

    if app.getExchange() == 'binance' and app.getGranularity() == '1h' and app.is1hEMA1226Bull() == True and app.is6hEMA1226Bull() == True:
        print ("*** Smart switch from granularity '1h' (1 hour) to '15m' (15 min) ***")
        app.setGranularity('15m')
        list(map(s.cancel, s.queue))
        s.enter(5, 1, executeJob, (sc, app))

    elif app.getExchange() == 'coinbasepro' and app.getGranularity() == 3600 and app.is1hEMA1226Bull() == True and app.is6hEMA1226Bull() == True:
        print ('*** Smart switch from granularity 3600 (1 hour) to 900 (15 min) ***')
        app.setGranularity(900)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, executeJob, (sc, app))

    if app.getExchange() == 'binance' and app.getGranularity() == '15m' and app.is1hEMA1226Bull() == False and app.is6hEMA1226Bull() == False:
        print ("*** Smart switch from granularity '15m' (15 min) to '1h' (1 hour) ***")
        app.setGranularity('1h')
        list(map(s.cancel, s.queue))
        s.enter(5, 1, executeJob, (sc, app))

    elif app.getExchange() == 'coinbasepro' and app.getGranularity() == 900 and app.is1hEMA1226Bull() == False and app.is6hEMA1226Bull() == False:
        print ("*** Smart switch from granularity 900 (15 min) to 3600 (1 hour) ***")
        app.setGranularity(3600)
        list(map(s.cancel, s.queue))
        s.enter(5, 1, executeJob, (sc, app))

    if app.getExchange() == 'binance' and str(app.getGranularity()) == '1d':
        if len(df) < 250:
            # data frame should have 250 rows, if not retry
            print('error: data frame length is < 250 (' + str(len(df)) + ')')
            logging.error('error: data frame length is < 250 (' + str(len(df)) + ')')
            list(map(s.cancel, s.queue))
            s.enter(300, 1, executeJob, (sc, app))
    else:
        if len(df) < 300:
            # data frame should have 300 rows, if not retry
            print('error: data frame length is < 300 (' + str(len(df)) + ')')
            logging.error('error: data frame length is < 300 (' + str(len(df)) + ')')
            list(map(s.cancel, s.queue))
            s.enter(300, 1, executeJob, (sc, app))

    if len(df_last) > 0:
        if app.isSimulation() == 0:
            price = app.getTicker(app.getMarket())
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
        #deathcross = bool(df_last['deathcross'].values[0])
        macdgtsignal = bool(df_last['macdgtsignal'].values[0])
        macdgtsignalco = bool(df_last['macdgtsignalco'].values[0])
        ema12ltema26 = bool(df_last['ema12ltema26'].values[0])
        ema12ltema26co = bool(df_last['ema12ltema26co'].values[0])
        macdltsignal = bool(df_last['macdltsignal'].values[0])
        macdltsignalco = bool(df_last['macdltsignalco'].values[0])
        obv = float(df_last['obv'].values[0])
        obv_pc = float(df_last['obv_pc'].values[0])
        elder_ray_bull = float(df_last['elder_ray_bull'].values[0])
        elder_ray_bear = float(df_last['elder_ray_bear'].values[0])

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

        # criteria for a buy signal
        if ema12gtema26co == True and macdgtsignal == True and goldencross == True and obv_pc > -5 and elder_ray_bull > 0 and last_action != 'BUY':
            action = 'BUY'
        # criteria for a sell signal
        elif ((ema12ltema26co == True and macdltsignal == True) or (elder_ray_bull < 0 and elder_ray_bear < 0)) and last_action not in ['','SELL']:
            action = 'SELL'
        # anything other than a buy or sell, just wait
        else:
            action = 'WAIT'

        last_buy_minus_fees = 0
        if last_buy > 0 and last_action == 'BUY':
            change_pcnt = ((price / last_buy) - 1) * 100

            # calculate last buy minus fees
            fee = last_buy * 0.005
            last_buy_minus_fees = last_buy + fee
            margin = ((price - last_buy_minus_fees) / price) * 100

            # loss failsafe sell at fibonacci band
            if app.allowSellAtLoss() and app.sellLowerPcnt() == None and fib_low > 0 and fib_low >= float(price):
                action = 'SELL'
                last_action = 'BUY'
                log_text = '! Loss Failsafe Triggered (Fibonacci Band: ' + str(fib_low) + ')'
                print (log_text, "\n")
                logging.warning(log_text)

            # loss failsafe sell at sell_lower_pcnt
            if app.allowSellAtLoss() and app.sellLowerPcnt() != None and change_pcnt < app.sellLowerPcnt():
                action = 'SELL'
                last_action = 'BUY'
                log_text = '! Loss Failsafe Triggered (< ' + str(app.sellLowerPcnt()) + '%)'
                print (log_text, "\n")
                logging.warning(log_text)

            if app.getExchange() == 'binance' and app.getGranularity() == '15m' and change_pcnt >= 2:
                # profit bank at 2% in smart switched mode
                action = 'SELL'
                last_action = 'BUY'
                log_text = '! Profit Bank Triggered (Smart Switch 2%)'
                print (log_text, "\n")
                logging.warning(log_text)

            if app.getExchange() == 'coinbasepro' and app.getGranularity() == 900 and change_pcnt >= 2:
                # profit bank at 2% in smart switched mode
                action = 'SELL'
                last_action = 'BUY'
                log_text = '! Profit Bank Triggered (Smart Switch 2%)'
                print (log_text, "\n")
                logging.warning(log_text)

            # profit bank at sell_upper_pcnt
            if app.sellUpperPcnt() != None and change_pcnt > app.sellUpperPcnt():
                action = 'SELL'
                last_action = 'BUY'
                log_text = '! Profit Bank Triggered (> ' + str(app.sellUpperPcnt()) + '%)'
                print (log_text, "\n")
                logging.warning(log_text)

            # profit bank at sell at fibonacci band
            if margin > 3 and app.sellUpperPcnt() != None and fib_high > fib_low and fib_high <= float(price):
                action = 'SELL'
                last_action = 'BUY'
                log_text = '! Profit Bank Triggered (Fibonacci Band: ' + str(fib_high) + ')'
                print (log_text, "\n")
                logging.warning(log_text)

            # profit bank when strong reversal detected
            if margin > 3 and obv_pc < 0 and macdltsignal == True:
                action = 'SELL'
                last_action = 'BUY'
                log_text = '! Profit Bank Triggered (Strong Reversal Detected)'
                print (log_text, "\n")
                logging.warning(log_text)

            # configuration specifies to not sell at a loss
            if not app.allowSellAtLoss() and margin <= 0:
                action = 'WAIT'
                last_action = 'BUY'
                log_text = '! Ignore Sell Signal (No Sell At Loss)'
                print (log_text, "\n")
                logging.warning(log_text)

        bullbeartext = ''
        if df_last['sma50'].values[0] == df_last['sma200'].values[0]:
            bullbeartext = ''
        elif goldencross == True and elder_ray_bull > 0:
            bullbeartext = ' (BULL)'
        elif goldencross == False and elder_ray_bear < 0:
            bullbeartext = ' (BEAR)'

        if elder_ray_bull < 0 and elder_ray_bear < 0:
            bullbeartext = ' (BEAR)'
        elif elder_ray_bull > 0 and elder_ray_bear > 0:
            bullbeartext = ' (BULL)'

        # polling is every 5 minutes (even for hourly intervals), but only process once per interval
        if (last_df_index != current_df_index):
            precision = 2

            if (price < 0.01):
                precision = 8

            price_text = 'Close: ' + str(app.truncate(price, precision))
            ema_text = app.compare(df_last['ema12'].values[0], df_last['ema26'].values[0], 'EMA12/26', precision)
            macd_text = app.compare(df_last['macd'].values[0], df_last['signal'].values[0], 'MACD', precision)
            obv_text = 'OBV: ' + str(app.truncate(df_last['obv'].values[0], 4)) + ' (' + str(app.truncate(df_last['obv_pc'].values[0], 2)) + '%)'
            eri_text = 'ERI: ' + str(app.truncate(elder_ray_bull, 4)) + ' / ' + str(app.truncate(elder_ray_bear, 4))

            if hammer == True:
                log_text = '* Candlestick Detected: Hammer ("Weak - Reversal - Bullish Signal - Up")'
                print (log_text, "\n")
                logging.debug(log_text)

            if shooting_star == True:
                log_text = '* Candlestick Detected: Shooting Star ("Weak - Reversal - Bearish Pattern - Down")'
                print (log_text, "\n")
                logging.debug(log_text)

            if hanging_man == True:
                log_text = '* Candlestick Detected: Hanging Man ("Weak - Continuation - Bearish Pattern - Down")'
                print (log_text, "\n")
                logging.debug(log_text)

            if inverted_hammer == True:
                log_text = '* Candlestick Detected: Inverted Hammer ("Weak - Continuation - Bullish Pattern - Up")'
                print (log_text, "\n")
                logging.debug(log_text)
    
            if three_white_soldiers == True:
                log_text = '*** Candlestick Detected: Three White Soldiers ("Strong - Reversal - Bullish Pattern - Up")'
                print (log_text, "\n")
                logging.debug(log_text)

            if three_black_crows == True:
                log_text = '* Candlestick Detected: Three Black Crows ("Strong - Reversal - Bearish Pattern - Down")'
                print (log_text, "\n")
                logging.debug(log_text)

            if morning_star == True:
                log_text = '*** Candlestick Detected: Morning Star ("Strong - Reversal - Bullish Pattern - Up")'
                print (log_text, "\n")
                logging.debug(log_text)

            if evening_star == True:
                log_text = '*** Candlestick Detected: Evening Star ("Strong - Reversal - Bearish Pattern - Down")'
                print (log_text, "\n")
                logging.debug(log_text)

            if three_line_strike == True:
                log_text = '** Candlestick Detected: Three Line Strike ("Reliable - Reversal - Bullish Pattern - Up")'
                print (log_text, "\n")
                logging.debug(log_text)

            if abandoned_baby == True:
                log_text = '** Candlestick Detected: Abandoned Baby ("Reliable - Reversal - Bullish Pattern - Up")'
                print (log_text, "\n")
                logging.debug(log_text)

            if morning_doji_star == True:
                log_text = '** Candlestick Detected: Morning Doji Star ("Reliable - Reversal - Bullish Pattern - Up")'
                print (log_text, "\n")
                logging.debug(log_text)

            if evening_doji_star == True:
                log_text = '** Candlestick Detected: Evening Doji Star ("Reliable - Reversal - Bearish Pattern - Down")'
                print (log_text, "\n")
                logging.debug(log_text)

            if two_black_gapping == True:
                log_text = '*** Candlestick Detected: Two Black Gapping ("Reliable - Reversal - Bearish Pattern - Down")'
                print (log_text, "\n")
                logging.debug(log_text)

            ema_co_prefix = ''
            ema_co_suffix = ''
            if ema12gtema26co == True:
                ema_co_prefix = '*^ '
                ema_co_suffix = ' ^*'
            elif ema12ltema26co == True:
                ema_co_prefix = '*v '
                ema_co_suffix = ' v*'   
            elif ema12gtema26 == True:
                ema_co_prefix = '^ '
                ema_co_suffix = ' ^'
            elif ema12ltema26 == True:
                ema_co_prefix = 'v '
                ema_co_suffix = ' v'

            macd_co_prefix = ''
            macd_co_suffix = ''
            if macdgtsignalco == True:
                macd_co_prefix = '*^ '
                macd_co_suffix = ' ^*'
            elif macdltsignalco == True:
                macd_co_prefix = '*v '
                macd_co_suffix = ' v*'
            elif macdgtsignal == True:
                macd_co_prefix = '^ '
                macd_co_suffix = ' ^'
            elif macdltsignal == True:
                macd_co_prefix = 'v '
                macd_co_suffix = ' v'

            obv_prefix = ''
            obv_suffix = ''
            if float(obv_pc) > 0:
                obv_prefix = '^ '
                obv_suffix = ' ^'
            elif float(obv_pc) < 0:
                obv_prefix = 'v '
                obv_suffix = ' v'

            if app.isVerbose() == 0:
                if last_action != '':
                    output_text = current_df_index + ' | ' + app.getMarket() + bullbeartext + ' | ' + str(app.getGranularity()) + ' | ' + price_text + ' | ' + ema_co_prefix + ema_text + ema_co_suffix + ' | ' + macd_co_prefix + macd_text + macd_co_suffix + ' | ' + obv_prefix + obv_text + obv_suffix + ' | ' + eri_text + ' | ' + action + ' | Last Action: ' + last_action
                else:
                    output_text = current_df_index + ' | ' + app.getMarket() + bullbeartext + ' | ' + str(app.getGranularity()) + ' | ' + price_text + ' | ' + ema_co_prefix + ema_text + ema_co_suffix + ' | ' + macd_co_prefix + macd_text + macd_co_suffix + ' | ' + obv_prefix + obv_text + obv_suffix + ' | ' + eri_text + ' | ' + action + ' '

                if last_action == 'BUY':
                    if last_buy_minus_fees > 0:
                        margin = str(app.truncate((((price - last_buy_minus_fees) / price) * 100), 2)) + '%'
                    else:
                        margin = '0%'

                    output_text += ' | ' +  margin

                logging.debug(output_text)
                print (output_text)
            else:
                logging.debug('-- Iteration: ' + str(iterations) + ' --' + bullbeartext)

                if last_action == 'BUY':
                    margin = str(app.truncate((((price - last_buy) / price) * 100), 2)) + '%'
                    logging.debug('-- Margin: ' + margin + '% --')            
                
                logging.debug('price: ' + str(app.truncate(price, precision)))
                logging.debug('ema12: ' + str(app.truncate(float(df_last['ema12'].values[0]), precision)))
                logging.debug('ema26: ' + str(app.truncate(float(df_last['ema26'].values[0]), precision)))
                logging.debug('ema12gtema26co: ' + str(ema12gtema26co))
                logging.debug('ema12gtema26: ' + str(ema12gtema26))
                logging.debug('ema12ltema26co: ' + str(ema12ltema26co))
                logging.debug('ema12ltema26: ' + str(ema12ltema26))
                logging.debug('sma50: ' + str(app.truncate(float(df_last['sma50'].values[0]), precision)))
                logging.debug('sma200: ' + str(app.truncate(float(df_last['sma200'].values[0]), precision)))
                logging.debug('macd: ' + str(app.truncate(float(df_last['macd'].values[0]), precision)))
                logging.debug('signal: ' + str(app.truncate(float(df_last['signal'].values[0]), precision)))
                logging.debug('macdgtsignal: ' + str(macdgtsignal))
                logging.debug('macdltsignal: ' + str(macdltsignal))
                logging.debug('obv: ' + str(obv))
                logging.debug('obv_pc: ' + str(obv_pc))
                logging.debug('action: ' + action)

                # informational output on the most recent entry  
                print('')
                print('================================================================================')
                txt = '        Iteration : ' + str(iterations) + bullbeartext
                print('|', txt, (' ' * (75 - len(txt))), '|')
                txt = '        Timestamp : ' + str(df_last.index.format()[0])
                print('|', txt, (' ' * (75 - len(txt))), '|')
                print('--------------------------------------------------------------------------------')
                txt = '            Close : ' + str(app.truncate(price, precision))
                print('|', txt, (' ' * (75 - len(txt))), '|')
                txt = '            EMA12 : ' + str(app.truncate(float(df_last['ema12'].values[0]), precision))
                print('|', txt, (' ' * (75 - len(txt))), '|')
                txt = '            EMA26 : ' + str(app.truncate(float(df_last['ema26'].values[0]), precision))
                print('|', txt, (' ' * (75 - len(txt))), '|')               
                txt = '   Crossing Above : ' + str(ema12gtema26co)
                print('|', txt, (' ' * (75 - len(txt))), '|')
                txt = '  Currently Above : ' + str(ema12gtema26)
                print('|', txt, (' ' * (75 - len(txt))), '|')
                txt = '   Crossing Below : ' + str(ema12ltema26co)
                print('|', txt, (' ' * (75 - len(txt))), '|')
                txt = '  Currently Below : ' + str(ema12ltema26)
                print('|', txt, (' ' * (75 - len(txt))), '|')

                if (ema12gtema26 == True and ema12gtema26co == True):
                    txt = '        Condition : EMA12 is currently crossing above EMA26'
                elif (ema12gtema26 == True and ema12gtema26co == False):
                    txt = '        Condition : EMA12 is currently above EMA26 and has crossed over'
                elif (ema12ltema26 == True and ema12ltema26co == True):
                    txt = '        Condition : EMA12 is currently crossing below EMA26'
                elif (ema12ltema26 == True and ema12ltema26co == False):
                    txt = '        Condition : EMA12 is currently below EMA26 and has crossed over'
                else:
                    txt = '        Condition : -'
                print('|', txt, (' ' * (75 - len(txt))), '|')

                txt = '            SMA20 : ' + str(app.truncate(float(df_last['sma20'].values[0]), precision))
                print('|', txt, (' ' * (75 - len(txt))), '|')
                txt = '           SMA200 : ' + str(app.truncate(float(df_last['sma200'].values[0]), precision))
                print('|', txt, (' ' * (75 - len(txt))), '|')

                print('--------------------------------------------------------------------------------')
                txt = '             MACD : ' + str(app.truncate(float(df_last['macd'].values[0]), precision))
                print('|', txt, (' ' * (75 - len(txt))), '|')
                txt = '           Signal : ' + str(app.truncate(float(df_last['signal'].values[0]), precision))
                print('|', txt, (' ' * (75 - len(txt))), '|')
                txt = '  Currently Above : ' + str(macdgtsignal)
                print('|', txt, (' ' * (75 - len(txt))), '|')
                txt = '  Currently Below : ' + str(macdltsignal)
                print('|', txt, (' ' * (75 - len(txt))), '|')

                if (macdgtsignal == True and macdgtsignalco == True):
                    txt = '        Condition : MACD is currently crossing above Signal'
                elif (macdgtsignal == True and macdgtsignalco == False):
                    txt = '        Condition : MACD is currently above Signal and has crossed over'
                elif (macdltsignal == True and macdltsignalco == True):
                    txt = '        Condition : MACD is currently crossing below Signal'
                elif (macdltsignal == True and macdltsignalco == False):
                    txt = '        Condition : MACD is currently below Signal and has crossed over'
                else:
                    txt = '        Condition : -'
                print('|', txt, (' ' * (75 - len(txt))), '|')

                print('--------------------------------------------------------------------------------')
                txt = '           Action : ' + action
                print('|', txt, (' ' * (75 - len(txt))), '|')
                print('================================================================================')
                if last_action == 'BUY':
                    txt = '           Margin : ' + margin + '%'
                    print('|', txt, (' ' * (75 - len(txt))), '|')
                    print('================================================================================')

            # if a buy signal
            if action == 'BUY':
                last_buy = price
                buy_count = buy_count + 1
                fee = float(price) * 0.005
                price_incl_fees = float(price) + fee
                buy_sum = buy_sum + price_incl_fees

                # if live
                if app.isLive() == 1:
                    if app.isVerbose() == 0:
                        logging.info(current_df_index + ' | ' + app.getMarket() + ' ' + str(app.getGranularity()) + ' | ' + price_text + ' | BUY')
                        print ("\n", current_df_index, '|', app.getMarket(), str(app.getGranularity()), '|', price_text, '| BUY', "\n")                    
                    else:
                        print('--------------------------------------------------------------------------------')
                        print('|                      *** Executing LIVE Buy Order ***                        |')
                        print('--------------------------------------------------------------------------------')
                    
                    # execute a live market buy
                    resp = app.marketBuy(app.getMarket(), float(account.getBalance(app.getQuoteCurrency())))
                    logging.info(resp)

                # if not live
                else:
                    if app.isVerbose() == 0:
                        logging.info(current_df_index + ' | ' + app.getMarket() + ' ' + str(app.getGranularity()) + ' | ' + price_text + ' | BUY')
                        print ("\n", current_df_index, '|', app.getMarket(), str(app.getGranularity()), '|', price_text, '| BUY')

                        bands = ta.getFibonacciRetracementLevels(float(price))                      
                        print (' Fibonacci Retracement Levels:', str(bands))
                        ta.printSupportResistanceLevel(float(price))

                        if len(bands) >= 1 and len(bands) <= 2:
                            if len(bands) == 1:
                                first_key = list(bands.keys())[0]
                                if first_key == 'ratio1':
                                    fib_low = 0
                                    fib_high = bands[first_key]
                                if first_key == 'ratio1_618':
                                    fib_low = bands[first_key]
                                    fib_high = bands[first_key] * 2
                                else:
                                    fib_low = bands[first_key]

                            elif len(bands) == 2:
                                first_key = list(bands.keys())[0]
                                second_key = list(bands.keys())[1]
                                fib_low = bands[first_key] 
                                fib_high = bands[second_key]
                            
                    else:
                        print('--------------------------------------------------------------------------------')
                        print('|                      *** Executing TEST Buy Order ***                        |')
                        print('--------------------------------------------------------------------------------')

                if app.shouldSaveGraphs() == 1:
                    tradinggraphs = TradingGraphs(ta)
                    ts = datetime.now().timestamp()
                    filename = app.getMarket() + '_' + str(app.getGranularity()) + '_buy_' + str(ts) + '.png'
                    tradinggraphs.renderEMAandMACD(24, 'graphs/' + filename, True)

            # if a sell signal
            elif action == 'SELL':
                sell_count = sell_count + 1
                fee = float(price) * 0.005
                price_incl_fees = float(price) - fee
                sell_sum = sell_sum + price_incl_fees

                # if live
                if app.isLive() == 1:
                    if app.isVerbose() == 0:
                        logging.info(current_df_index + ' | ' + app.getMarket() + ' ' + str(app.getGranularity()) + ' | ' + price_text + ' | SELL')
                        print ("\n", current_df_index, '|', app.getMarket(), str(app.getGranularity()), '|', price_text, '| SELL')

                        bands = ta.getFibonacciRetracementLevels(float(price))                      
                        print (' Fibonacci Retracement Levels:', str(bands), "\n")                    

                        if len(bands) >= 1 and len(bands) <= 2:
                            if len(bands) == 1:
                                first_key = list(bands.keys())[0]
                                if first_key == 'ratio1':
                                    fib_low = 0
                                    fib_high = bands[first_key]
                                if first_key == 'ratio1_618':
                                    fib_low = bands[first_key]
                                    fib_high = bands[first_key] * 2
                                else:
                                    fib_low = bands[first_key]

                            elif len(bands) == 2:
                                first_key = list(bands.keys())[0]
                                second_key = list(bands.keys())[1]
                                fib_low = bands[first_key] 
                                fib_high = bands[second_key]

                    else:
                        print('--------------------------------------------------------------------------------')
                        print('|                      *** Executing LIVE Sell Order ***                        |')
                        print('--------------------------------------------------------------------------------')

                    # execute a live market sell
                    resp = app.marketSell(app.getMarket(), float(account.getBalance(app.getBaseCurrency())))
                    logging.info(resp)

                # if not live
                else:
                    if app.isVerbose() == 0:
                        sell_price = float(str(app.truncate(price, precision)))
                        last_buy_price = float(str(app.truncate(float(last_buy), precision)))
                        buy_sell_diff = round(np.subtract(sell_price, last_buy_price), precision)

                        if (sell_price != 0):
                            buy_sell_margin_no_fees = str(app.truncate((((sell_price - last_buy_price) / sell_price) * 100), 2)) + '%'
                        else:
                            buy_sell_margin_no_fees = '0%'

                        # calculate last buy minus fees
                        buy_fee = last_buy_price * 0.005
                        last_buy_price_minus_fees = last_buy_price + buy_fee

                        if (sell_price != 0):
                            buy_sell_margin_fees = str(app.truncate((((sell_price - last_buy_price_minus_fees) / sell_price) * 100), 2)) + '%'
                        else:
                            buy_sell_margin_fees = '0%'

                        logging.info(current_df_index + ' | ' + app.getMarket() + ' ' + str(app.getGranularity()) + ' | SELL | ' + str(sell_price) + ' | BUY | ' + str(last_buy_price) + ' | DIFF | ' + str(buy_sell_diff) + ' | MARGIN NO FEES | ' + str(buy_sell_margin_no_fees) + ' | MARGIN FEES | ' + str(buy_sell_margin_fees))
                        print ("\n", current_df_index, '|', app.getMarket(), str(app.getGranularity()), '| SELL |', str(sell_price), '| BUY |', str(last_buy_price), '| DIFF |', str(buy_sell_diff) , '| MARGIN NO FEES |', str(buy_sell_margin_no_fees), '| MARGIN FEES |', str(buy_sell_margin_fees), "\n")                    
                    else:
                        print('--------------------------------------------------------------------------------')
                        print('|                      *** Executing TEST Sell Order ***                        |')
                        print('--------------------------------------------------------------------------------')

                if app.shouldSaveGraphs() == 1:
                    tradinggraphs = TradingGraphs(ta)
                    ts = datetime.now().timestamp()
                    filename = app.getMarket() + '_' + str(app.getGranularity()) + '_buy_' + str(ts) + '.png'
                    tradinggraphs.renderEMAandMACD(24, 'graphs/' + filename, True)

            # last significant action
            if action in [ 'BUY', 'SELL' ]:
                last_action = action
            
            last_df_index = str(df_last.index.format()[0])

            if iterations == len(df):
                print ("\nSimulation Summary\n")

                if buy_count > sell_count:
                    fee = price * 0.005
                    last_price_minus_fees = price - fee
                    sell_sum = sell_sum + last_price_minus_fees
                    sell_count = sell_count + 1

                print ('   Buy Count :', buy_count)
                print ('  Sell Count :', sell_count, "\n")

                if sell_count > 0:
                    print ('      Margin :', str(app.truncate((((sell_sum - buy_sum) / sell_sum) * 100), 2)) + '%', "\n")

                    print ('  ** non-live simulation, assuming highest fees', "\n")

        else:
            now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            print (now, '|', app.getMarket() + bullbeartext, '|', str(app.getGranularity()), '| Current Price:', price)

            # decrement ignored iteration
            iterations = iterations - 1

        # if live
        if app.isLive() == 1:
            # update order tracker csv
            if app.getExchange() == 'binance':
                account.saveTrackerCSV(app.getMarket())
            elif app.getExchange() == 'binance':
                account.saveTrackerCSV()

        if app.isSimulation() == 1:
            if iterations < 300:
                if app.simuluationSpeed() in [ 'fast', 'fast-sample' ]:
                    # fast processing
                    executeJob(sc, app, trading_data)
                else:
                    # slow processing
                    list(map(s.cancel, s.queue))
                    s.enter(1, 1, executeJob, (sc, app, trading_data))

        else:
            # poll every 5 minute
            list(map(s.cancel, s.queue))
            s.enter(300, 1, executeJob, (sc, app))

try:
    # initialise logging
    logging.basicConfig(filename='pycryptobot.log', format='%(asctime)s - %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filemode='a', level=logging.DEBUG)

    # initialise and start application
    app.setGranularity(3600)
    trading_data = app.startApp(account, last_action)

    # run the first job immediately after starting
    if app.isSimulation() == 1:
        executeJob(s, app, trading_data)
    else:
        executeJob(s, app)

    s.run()

# catches a keyboard break of app, exits gracefully
except KeyboardInterrupt:
    print(datetime.now(), 'closed')
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)
