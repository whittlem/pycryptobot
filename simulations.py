import random, re
import pandas as pd
from datetime import datetime, timedelta
from models.CoinbasePro import CoinbasePro
from models.TradingAccount import TradingAccount
from views.TradingGraphs import TradingGraphs

MARKET = 'BTC-GBP'
GRANULARITY = 3600
OPENING_BALANCE = 1000
AMOUNT_PER_TRADE = 100
EXPERIMENTS = 3

def runExperiment(id, market='BTC-GBP', granularity=3600, openingBalance=1000, amountPerTrade=100, mostRecent=True):
    if not isinstance(id, int):
        raise TypeError('ID not numeric.')

    if id < 0:
        raise TypeError('ID is invalid.')

    p = re.compile(r"^[A-Z]{3,4}\-[A-Z]{3,4}$")
    if not p.match(market):
        raise TypeError('Coinbase Pro market required.')

    if not isinstance(granularity, int):
        raise TypeError('Granularity integer required.')

    if not granularity in [60, 300, 900, 3600, 21600, 86400]:
        raise TypeError(
            'Granularity options: 60, 300, 900, 3600, 21600, 86400.')

    if not isinstance(openingBalance, int) and not isinstance(openingBalance, float):
        raise TypeError('Opening balance not numeric.')

    if openingBalance <= 0 or openingBalance < amountPerTrade:
        raise TypeError('Insufficient opening balance.')

    if amountPerTrade <= 0 or openingBalance < amountPerTrade:
        raise TypeError('Insufficient amount per trade.')

    if not isinstance(openingBalance, int) and not isinstance(openingBalance, float):
        raise TypeError('Amount per trade not numeric.')

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

    account = TradingAccount()

    coinbasepro = CoinbasePro(market, granularity, startDate, endDate)
    coinbasepro.addEMABuySignals()
    coinbasepro.addMACDBuySignals()
    df = coinbasepro.getDataFrame()

    buysignals = (df.ema12gtema26co == True) & (df.macdgtsignal == True) & (df.obv_pc >= 2)  # buy only if there is significant momentum
    sellsignals = (df.ema12ltema26co == True) & (df.macdltsignal == True)
    df_signals = df[(buysignals) | (sellsignals)]

    diff = 0
    action = ''
    last_action = ''
    last_close = 0
    total_diff = 0
    events = []
    for index, row in df_signals.iterrows():
        df_orders = account.getOrders()

        if df.iloc[-1]['sma50'] > df.iloc[-1]['sma200'] and row['ema12gtema26co'] == True and row['macdgtsignal'] == True:
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
                account.buy('BTC', 'GBP', amountPerTrade, row['close'])
            elif action == 'sell':
                account.sell('BTC', 'GBP', df_orders.iloc[[-1]]['size'].values[0], row['close'])

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

    events_df = pd.DataFrame(events)
    print(events_df)

    addBalance = 0
    df_orders = account.getOrders()
    if len(df_orders) > 0 and df_orders.iloc[[-1]]['action'].values[0] == 'buy':
        # last trade is still open, add to closing balance
        addBalance = df_orders.iloc[[-1]]['value'].values[0]
    
    print('')
    print(df_orders)

    result = '{:.2f}'.format(round((account.getBalance() + addBalance) - openingBalance, 2))

    print('')
    print("Opening balance:", '{:.2f}'.format(openingBalance))
    print("Closing balance:", '{:.2f}'.format(round(account.getBalance() + addBalance, 2)))
    print("         Result:", result)
    print('')

    tradinggraphs = TradingGraphs(coinbasepro)
    tradinggraphs.renderBuySellSignalEMA1226MACD('experiments/experiment' + str(id) + '_' + str(result) + '.png', True)

    result_dict = {
        'market': market,
        'granularity': granularity,
        'start': startDate,
        'end': endDate,
        'open': '{:.2f}'.format(openingBalance),
        'close': '{:.2f}'.format(round(account.getBalance() + addBalance, 2)),
        'result': result
    }

    return result_dict

results = []
for num in range(EXPERIMENTS):
    if num == 0:
        results.append(runExperiment(num, MARKET, GRANULARITY, OPENING_BALANCE, AMOUNT_PER_TRADE, True))
    else:
        results.append(runExperiment(num, MARKET, GRANULARITY, OPENING_BALANCE, AMOUNT_PER_TRADE, False))

try:
    results_df = pd.DataFrame(results)
    results_df.to_csv('experiments/experiments.csv', index=False)
except OSError:
    raise SystemExit('Unable to save: experiments/experiments.csv')  