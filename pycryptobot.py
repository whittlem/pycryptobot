"""Python Crypto Bot consuming Coinbase Pro API

DISCLAIMER -- PLEASE READ!

I developed this crypto trading bot for myself. I'm happy to share the project and code with others
but I don't take responsibility for how it performs for you or any potential losses incurred due to
market conditions or even bugs. I'm using this bot myself and will keep improving it so please make
sure you are pulling the repo often for updates and bug fixes ("git pull"). 

USAGE

You are free to use this app and code however you wish. I know others who are using some of my code
in their personal projects and I'm fine with that. I do however have a polite request and that is
if you improve on my code to share it with me. You may have found this project via Medium where I am
a writer (https://whittle.medium.com). I would really appreciate it if you follow me and read and 
"clap" for my articles (especially related to this project). I get paid by Medium for my articles
so that is one way you can reward me for my efforts without actually spending anything. If you 
would like to share and promote my articles I would also really appreciate it.

IMPORTANT

In order to limit exposure by the trading bot, in your Coinbase Pro profile I suggest you create
another "Portfolio" dedicted for this trading bot. Create your API keys associated with the
"Trading Bot" portfolio and only keep funds you want to give the bot access to in the portfolio.
That way if anything goes wrong only what is within this portfolio is at risk!
"""

import pandas as pd
import json
import os
import re
import sched
import sys
import time
from datetime import datetime
from models.CoinbasePro import CoinbasePro
from models.TradingAccount import TradingAccount
from models.CoinbaseProAPI import CoinbaseProAPI

"""Settings"""

# 0 is test/demo, 1 is live
is_live = 0

# the crypto market you wish you trade
cryptoMarket = 'BTC'

# the source of funds for your trading
fiatMarket = 'GBP'

# supported granularity (recommended 3600 for 1 hour interval for day trading)
granularity = 3600  # 1 hour

"""Highly advisable not to change any code below this point!"""

# validation of crypto market inputs
if cryptoMarket not in ['BCH', 'BTC', 'ETH', 'LTC']:
    raise Exception('Invalid crypto market: BCH, BTC, ETH, LTC or ETH')

# validation of fiat market inputs
if fiatMarket not in ['EUR', 'GBP', 'USD']:
    raise Exception('Invalid FIAT market: EUR, GBP, USD')

# reconstruct the market based on the crypto and fiat inputs
market = cryptoMarket + '-' + fiatMarket

config = {}
account = None
# if live trading is enabled
if is_live == 1:
    # open the config.json file
    with open('config.json') as config_file:
        # store the configuration in dictionary
        config = json.load(config_file)
    # connect your Coinbase Pro live account
    account = TradingAccount(config)

# initial state is to wait
action = 'wait'
last_action = ''
last_df_index = ''

def executeJob(sc, market, granularity):
    """Trading bot job which runs at a scheduled interval"""
    global action, last_action, last_df_index

    # Retrieves the latest analysed market data
    coinbasepro = CoinbasePro(market, granularity)
    coinbasepro.addEMABuySignals()
    coinbasepro.addMACDBuySignals()
    df = coinbasepro.getDataFrame()

    # df_last contains the most recent entry
    df_last = df.tail(1)
    ema12gtema26 = bool(df_last['ema12gtema26'].values[0])
    ema12gtema26co = bool(df_last['ema12gtema26co'].values[0])
    macdgtsignal = bool(df_last['macdgtsignal'].values[0])
    ema12ltema26 = bool(df_last['ema12ltema26'].values[0])
    ema12ltema26co = bool(df_last['ema12ltema26co'].values[0])
    macdltsignal = bool(df_last['macdltsignal'].values[0])
    obv_pc = float(df_last['obv_pc'].values[0])
    obvsignal = bool(df_last['obvsignal'].values[0])

    # Criteria for a buy signal
    if (ema12gtema26co == True and macdgtsignal == True and obv_pc >= 2) or (ema12gtema26 == True and macdgtsignal == True and obv_pc >= 5) and last_action != 'buy':
        action = 'buy'
    # Criteria for a sell signal
    elif ema12ltema26co == True and macdltsignal == True and last_action != 'sell':
        action = 'sell'
    # Anything other than a buy or sell, just wait
    else:
        action = 'wait'

    # Polling is every 5 minutes (even for hourly intervals), but only process once per interval
    if (last_df_index != df_last.index.format()):
        # Informational output on the most recent entry  
        print(df_last.index.format(), 'ema12:' + str(df_last['ema12'].values[0]), 'ema26:' + str(df_last['ema26'].values[0]), 'above:(', ema12gtema26, ema12gtema26co, ')', 'below:(', ema12ltema26,
              ema12ltema26co, ')', 'macd:' + str(df_last['macd'].values[0]), 'signal:' + str(df_last['signal'].values[0]), 'above:(', macdgtsignal, ')', 'below:(', macdltsignal, ')', obv_pc, 'above:(', obvsignal, ')', action)

        # If a buy signal
        if action == 'buy':
            # If live
            if is_live == 1:
                print('>>> EXECUTING LIVE BUY! <<<')
                # Connect to Coinbase Pro API live
                model = CoinbaseProAPI(config['api_key'], config['api_secret'], config['api_pass'], config['api_url'])
                # Execute a live market buy
                resp = model.marketBuy(market, account.getBalance(fiatMarket))
                print(resp)
            # If not live
            else:
                print('>>> NON-LIVE SIMULATION BUY <<<')
            print(df_last)

        # If a sell signal
        elif action == 'sell':
            # If live
            if is_live == 1:
                print('>>> EXECUTING LIVE SELL! <<<')
                # Connect to Coinbase Pro API live
                model = CoinbaseProAPI(config['api_key'], config['api_secret'], config['api_pass'], config['api_url'])
                # Execute a live market sell
                resp = model.marketSell(market, account.getBalance(cryptoMarket))
                print(resp)
            # If not live
            else:
                print('>>> NON-LIVE SIMULATION SELL <<<')
            print(df_last)

        last_action = action
        last_df_index = df_last.index.format()

    # poll every 5 minutes
    s.enter(300, 1, executeJob, (sc, market, granularity))

try:
    print("Python Crypto Bot using Coinbase Pro API\n")
    print(datetime.now(), 'started for market',
          market, 'using interval', granularity)

    s = sched.scheduler(time.time, time.sleep)
    # run the first job immediately after starting
    s.enter(1, 1, executeJob, (s, market, granularity))
    s.run()

# catches a keyboard break of app, exits gracefully
except KeyboardInterrupt:
    print(datetime.now(), 'closed')
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)