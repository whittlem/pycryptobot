"""Runs x number of simulations using random time frames"""

import math
import random, re
import pandas as pd
from datetime import datetime, timedelta
from models.CoinbasePro import CoinbasePro
from models.TradingAccount import TradingAccount
from views.TradingGraphs import TradingGraphs

"Paramters of the experiments"

market = 'BTC-GBP'
granularity = 3600
experiments = 100 # 1 or more

def runExperiment(id, market='BTC-GBP', granularity=3600, mostRecent=True):
    """Run an experiment

    Parameters
    ----------
    market : str
        A valid market/product from the Coinbase Pro exchange. (Default: 'BTC-GBP')
    granularity : int
        A valid market interval {60, 300, 900, 3600, 21600, 86400} (Default: 86400 - 1 day)
    """

    if not isinstance(id, int):
        raise TypeError('ID not numeric.')

    if id < 0:
        raise TypeError('ID is invalid.')

    p = re.compile(r"^[A-Z]{3,4}\-[A-Z]{3,4}$")
    if not p.match(market):
        raise TypeError('Coinbase Pro market required.')

    cryptoMarket, fiatMarket = market.split('-',2)

    if not isinstance(granularity, int):
        raise TypeError('Granularity integer required.')

    if not granularity in [60, 300, 900, 3600, 21600, 86400]:
        raise TypeError(
            'Granularity options: 60, 300, 900, 3600, 21600, 86400.')

    if not isinstance(mostRecent, bool):
        raise TypeError('Most recent is a boolean.')

    print ('Experiment #' + str(id) + "\n")

    endDate = datetime.now() - timedelta(hours=random.randint(0,8760 * 3)) # 3 years in hours
    startDate = endDate - timedelta(hours=300)

    if mostRecent == True:
        startDate = ''
        endDate = ''
        print ('Start date:', (datetime.now() - timedelta(hours=300)).isoformat())
        print ('  End date:', datetime.now().isoformat())
        print ('')
    else:
        startDate = str(startDate.isoformat())
        endDate = str(endDate.isoformat())
        print ('Start date:', startDate)
        print ('  End date:', endDate)
        print ('')

    # instantiate a non-live trade account
    account = TradingAccount()

    # instantiate a CoinbassePro object with desired criteria
    coinbasepro = CoinbasePro(market, granularity, startDate, endDate)

    # adds buy and sell signals to Pandas DataFrame
    coinbasepro.addEMABuySignals()
    coinbasepro.addMACDBuySignals()

    # stores the Pandas Dataframe in df
    df = coinbasepro.getDataFrame()

    # defines the buy and sell signals and consolidates into df_signals
    buysignals = ((df.ema12gtema26co == True) & (df.macdgtsignal == True) & (df.obv_pc > 0)) | ((df.ema12gtema26 == True) & (df.ema12gtema26 == True) & (df.macdgtsignal == True) & (df.obv_pc >= 2))
    sellsignals = (((df.ema12ltema26co == True) & (df.macdltsignal == True)) | ((df.ema12gtema26 == True) & ((df.macdltsignal == True) & (df.obv_pc < 0))))
    df_signals = df[(buysignals) | (sellsignals)]

    diff = 0
    action = ''
    last_action = ''
    last_close = 0
    total_diff = 0
    events = []
    # iterate through the DataFrame buy and sell signals
    for index, row in df_signals.iterrows():
        df_orders = account.getOrders()

        # determine if the df_signal is a buy or sell, just a high level check
        if row['ema12gtema26'] == True and row['macdgtsignal'] == True:
            action = 'buy'
        elif row['ema12ltema26co'] == True and row['macdltsignal'] == True:
            # ignore sell if close is lower than previous buy
            if len(df_orders) > 0 and df_orders.iloc[[-1]]['action'].values[0] == 'buy' and row['close'] > df_orders.iloc[[-1]]['price'].values[0]:
                action = 'sell'

        if action != '' and action != last_action and not (last_action == '' and action == 'sell'):
            if last_action != '':
                if action == 'sell':
                    diff = row['close'] - last_close
                else:
                    diff = 0.00

            if action == 'buy':
                account.buy(cryptoMarket, fiatMarket, 100, row['close'])
            elif action == 'sell':
                account.sell(cryptoMarket, fiatMarket, account.getBalance(cryptoMarket), row['close'])

            data_dict = {
                'market': market,
                'granularity': granularity,
                'start': startDate,
                'end': endDate,
                'action': action,
                'index': str(index),
                'close': row['close'],
                'sma200': row['sma200'],
                'ema12': row['ema12'],
                'ema26': row['ema26'],
                'macd': row['macd'],
                'signal': row['signal'],
                'ema12gtema26co': row['ema12gtema26co'],
                'macdgtsignal': row['macdgtsignal'],
                'ema12ltema26co': row['ema12ltema26co'],
                'macdltsignal': row['macdltsignal'],
                'obv_pc': row['obv_pc'],
                'diff': diff
            }

            events.append(data_dict)

            last_action = action
            last_close = row['close']
            total_diff = total_diff + diff

    # displays the events from the simulation
    events_df = pd.DataFrame(events)
    print(events_df)

    # if the last transation was a buy retrieve open amount
    addBalance = 0
    df_orders = account.getOrders()
    if len(df_orders) > 0 and df_orders.iloc[[-1]]['action'].values[0] == 'buy':
        # last trade is still open, add to closing balance
        addBalance = df_orders.iloc[[-1]]['value'].values[0]
    
    # displays the orders from the simulation
    print('')
    print(df_orders)

    def truncate(f, n):
        return math.floor(f * 10 ** n) / 10 ** n

    # if the last transaction was a buy add the open amount to the closing balance
    result = truncate(round((account.getBalance(fiatMarket) + addBalance) - 1000, 2), 2)

    print('')
    print("Opening balance:", 1000)
    print("Closing balance:", truncate(round(account.getBalance(fiatMarket) + addBalance, 2), 2))
    print("         Result:", result)
    print('')

    # saves the rendered diagram for the DataFrame (without displaying)
    tradinggraphs = TradingGraphs(coinbasepro)
    tradinggraphs.renderBuySellSignalEMA1226MACD('experiments/experiment' + str(id) + '_' + str(result) + '.png', True)

    result_dict = {
        'market': market,
        'granularity': granularity,
        'start': startDate,
        'end': endDate,
        'open': 1000,
        'close': '{:.2f}'.format(round(account.getBalance(fiatMarket) + addBalance, 2)),
        'result': result
    }

    return result_dict

results = []
# iterate through experiments
for num in range(experiments):
    # append experiment results
    if num == 0:
        # first experiment is always the most recent data
        results.append(runExperiment(num, market, granularity, True))
    else:
        # all other experiments use random time intervals going back years
        results.append(runExperiment(num, market, granularity, False))

try:
    results_df = pd.DataFrame(results)
    # store the DataFrame to experiments/experiments.csv
    results_df.to_csv('experiments/experiments.csv', index=False)
except OSError:
    raise SystemExit('Unable to save: experiments/experiments.csv')  