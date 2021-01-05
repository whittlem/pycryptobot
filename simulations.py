import random
import pandas as pd
from datetime import datetime, timedelta
from models.CoinbasePro import CoinbasePro
from models.TradingAccount import TradingAccount
from views.TradingGraphs import TradingGraphs

endDate = datetime.now() - timedelta(hours=random.randint(0,8760 * 3)) # 3 years in hours
startDate = endDate - timedelta(hours=300)

openingBalance = 1000

account = TradingAccount('experiment1')
account.depositFIAT(openingBalance)

coinbasepro = CoinbasePro('BTC-GBP', 3600, str(startDate.isoformat()), str(endDate.isoformat()))
coinbasepro.addEMABuySignals()
coinbasepro.addMACDBuySignals()
df = coinbasepro.getDataFrame()

buysignals = (df.ema12gtema26co == True) & (df.macdgtsignal == True)
sellsignals = (df.ema12ltema26co == True) & (df.macdltsignal == True)
df_signals = df[(buysignals) | (sellsignals)]

diff = 0
action = ''
last_action = ''
last_close = 0
total_diff = 0
for index, row in df_signals.iterrows():
    if row['ema12gtema26co'] == True and row['macdgtsignal'] == True:
        action = 'buy'
    elif row['ema12ltema26co'] == True and row['macdltsignal'] == True:
        action = 'sell'

    if action != '' and action != last_action and not (last_action == '' and action == 'sell'):
        if last_action != '':
            diff = row['close'] - last_close

        if action == 'buy':
            account.buy('BTC', 'GBP', 100, row['close'])
        elif action == 'sell':
            lastBuy = account.getActivity()[-1][3]
            account.sell('BTC', 'GBP', lastBuy, row['close'])

        print(action, index, row['close'], row['ema12'], row['ema26'], row['macd'], row['signal'],
            row['ema12gtema26co'], row['macdgtsignal'], row['ema12ltema26co'], row['macdltsignal'], diff)

        last_action = action
        last_close = row['close']
        total_diff = total_diff + diff

addBalance = 0
if account.getActivity()[-1][2] == 'buy':
    # last trade is still open, add to closing balance
    addBalance = account.getActivity()[-1][3] * account.getActivity()[-1][4]

print ('')
df = pd.DataFrame(account.getActivity(), columns=['date','balance','action','amount','value'])
print (df)

print ('')
print ("Opening balance:", '{:.2f}'.format(openingBalance))
print ("Closing balance:", '{:.2f}'.format(round(account.getBalanceFIAT() + addBalance, 2)))

tradinggraphs = TradingGraphs(coinbasepro)
tradinggraphs.renderBuySellSignalEMA1226MACD()