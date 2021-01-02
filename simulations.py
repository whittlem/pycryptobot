from models.CoinbasePro import CoinbasePro
from views.TradingGraphs import TradingGraphs

coinbasepro = CoinbasePro('BTC-USD', 3600)
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

        print(action, index, row['close'], row['ema12'], row['ema26'], row['macd'], row['signal'],
              row['ema12gtema26co'], row['macdgtsignal'], row['ema12ltema26co'], row['macdltsignal'], diff)
        last_action = action
        last_close = row['close']
        total_diff = total_diff + diff

print ("\ntotal: ", total_diff)

tradinggraphs = TradingGraphs(coinbasepro)
tradinggraphs.renderBuySellSignalEMA1226MACD()