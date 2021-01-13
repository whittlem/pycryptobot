import pandas as pd
from datetime import datetime, timedelta
from models.CoinbasePro import CoinbasePro
from models.TradingAccount import TradingAccount
from views.TradingGraphs import TradingGraphs

market = 'BTC-GBP'
granularity = 3600
startDate = '2020-11-20T23:12:07.720258'
endDate = '2020-12-03T11:12:07.720258'
openingBalance = 1000
amountPerTrade = 100

account = TradingAccount()

coinbasepro = CoinbasePro(market, granularity, startDate, endDate)
coinbasepro.addEMABuySignals()
coinbasepro.addMACDBuySignals()
df = coinbasepro.getDataFrame()

buysignals = (df.ema12gtema26co == True) & (df.macdgtsignal == True) & (df.obv_pc >= 2)  # buy only if there is significant momentum
sellsignals = (df.ema12ltema26co == True) & (df.macdltsignal == True)
df_signals = df[(buysignals) | (sellsignals)]

multiplier = 1
if(granularity == 60):
    multiplier = 1
elif(granularity == 300):
    multiplier = 5
elif(granularity == 900):
    multiplier = 10
elif(granularity == 3600):
    multiplier = 60
elif(granularity == 21600):
    multiplier = 360
elif(granularity == 86400):
    multiplier = 1440

if startDate != '' and endDate == '':
    endDate  = str((datetime.strptime(startDate, '%Y-%m-%dT%H:%M:%S.%f') + timedelta(minutes=granularity * multiplier)).isoformat()) 

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
tradinggraphs.renderBuySellSignalEMA1226MACD()