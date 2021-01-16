import pandas as pd
import json, os, re, sched, sys, time
from datetime import datetime
from models.CoinbasePro import CoinbasePro
from models.TradingAccount import TradingAccount
from models.CoinbaseProAPI import CoinbaseProAPI

"""
DISCLAIMER:
* Enable live trading (is_live = 1) completely at your own risk.
* Set investment amount to all (invest_amount = -1) at your own risk.
 * This will execute buys with your entire FIAT balance e.g. GBP
 * This will execute sells with your entire crypto balance e.g. BTC
"""

"""
Settings
"""

is_live = 1
cryptoMarket = 'BTC'
fiatMarket = 'GBP'
granularity = 3600 # 1 hour

"""
Highly advisable not to change any code below this point!
"""

if cryptoMarket not in ['BCH','BTC','ETH','LTC']:
    raise Exception('Invalid crypto market: BCH, BTC, ETH, LTC or ETH')

if fiatMarket not in ['EUR','GBP','USD']:
    raise Exception('Invalid FIAT market: EUR, GBP, USD')

market = cryptoMarket + '-' + fiatMarket

config = {}
account = None
if is_live == 1:
    with open('config.json') as config_file:
        config = json.load(config_file)
    account = TradingAccount(config)

action = 'wait'
last_action = ''
last_df_index = ''

def executeJob(sc, market, granularity): 
    global action, last_action, last_df_index

    coinbasepro = CoinbasePro(market, granularity)
    coinbasepro.addEMABuySignals()
    coinbasepro.addMACDBuySignals()
    df = coinbasepro.getDataFrame()

    df_last = df.tail(1)
    ema12gtema26co = bool(df_last['ema12gtema26co'].values[0])
    macdgtsignal = bool(df_last['macdgtsignal'].values[0])
    ema12ltema26co = bool(df_last['ema12ltema26co'].values[0])
    macdltsignal = bool(df_last['macdltsignal'].values[0])
    obv_pc = float(df_last['obv_pc'].values[0])

    if ema12gtema26co == True and macdgtsignal == True and obv_pc >= 2 and last_action != 'buy':
        action = 'buy'
    elif ema12ltema26co == True and macdltsignal == True and last_action != 'sell':
        action = 'sell'
    else:
        action = 'wait'

    if (last_df_index != df_last.index.format()): # process once per interval
        print(df_last.index.format(), 'ema12:' + str(df_last['ema12'].values[0]), 'ema26:' + str(df_last['ema26'].values[0]), ema12gtema26co, ema12ltema26co, 'macd:' + str(df_last['macd'].values[0]), 'signal:' + str(df_last['signal'].values[0]), macdgtsignal, macdltsignal, obv_pc, action)

        if action == 'buy':
            if is_live == 1:
                print ('>>> EXECUTING LIVE BUY! <<<') 
                model = CoinbaseProAPI(config['api_key'], config['api_secret'], config['api_pass'], config['api_url'])
                resp = model.marketBuy(market, account.getBalance(fiatMarket))
                print (resp)
            else:
                print ('>>> NON-LIVE SIMULATION BUY <<<')  
            print (df_last)
            
        elif action == 'buy':
            if is_live == 1:
                print ('>>> EXECUTING LIVE SELL! <<<')
                model = CoinbaseProAPI(config['api_key'], config['api_secret'], config['api_pass'], config['api_url'])
                resp = model.marketSell(market, account.getBalance(cryptoMarket))
                print (resp)                
            else:
                print ('>>> NON-LIVE SIMULATION SELL <<<')  
            print (df_last)

        last_action = action
        last_df_index = df_last.index.format()

    s.enter(300, 1, executeJob, (sc, market, granularity)) # poll every 5 minutes

try:
    print("Python Crypto Bot using Coinbase Pro API\n")
    print(datetime.now(), 'started for market', market, 'using interval', granularity)

    s = sched.scheduler(time.time, time.sleep)
    s.enter(1, 1, executeJob, (s, market, granularity))
    s.run()
except KeyboardInterrupt:
    print(datetime.now(), 'closed')
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)