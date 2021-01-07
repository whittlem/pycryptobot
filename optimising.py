import pandas as pd
from models.CoinbasePro import CoinbasePro
from models.TradingAccount import TradingAccount
from views.TradingGraphs import TradingGraphs

market = 'BTC-GBP'
granularity = 3600
startDate = '2019-05-13T13:19:56.639996'
endDate = '2019-05-26T01:19:56.639996'
openingBalance = 1000
amountPerTrade = 100

account = TradingAccount('optimisation')
account.depositFIAT(openingBalance)

coinbasepro = CoinbasePro(market, granularity, startDate, endDate)
coinbasepro.addEMABuySignals()
coinbasepro.addMACDBuySignals()
df = coinbasepro.getDataFrame()

buysignals = (df.ema12gtema26co == True) & (df.macdgtsignal == True) & (df.obv_pc >= 5)  # buy only if there is significant momentum
sellsignals = (df.ema12ltema26co == True) & (df.macdltsignal == True)
df_signals = df[(buysignals) | (sellsignals)]

diff = 0
action = ''
last_action = ''
last_close = 0
total_diff = 0
events = []
for index, row in df_signals.iterrows():
    if row['ema12gtema26co'] == True and row['macdgtsignal'] == True:
        action = 'buy'
    elif row['ema12ltema26co'] == True and row['macdltsignal'] == True:
        # ignore sell if close is lower than previous buy
        if len(account.getActivity()) > 0 and account.getActivity()[-1][2] == 'buy' and row['close'] > account.getActivity()[-1][4]:
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
            lastBuy = account.getActivity()[-1][3]
            account.sell('BTC', 'GBP', lastBuy, row['close'])

        data_dict = {
            'market': market,
            'granularity': granularity,
            'start': startDate,
            'end': endDate,
            'action': action,
            'index': str(index),
            'close': row['close'],
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
if account.getActivity()[-1][2] == 'buy':
    # last trade is still open, add to closing balance
    addBalance = account.getActivity()[-1][3] * account.getActivity()[-1][4]

print('')
trans_df = pd.DataFrame(account.getActivity(), columns=[
                        'date', 'balance', 'action', 'amount', 'value'])
print(trans_df)

result = '{:.2f}'.format(
    round((account.getBalanceFIAT() + addBalance) - openingBalance, 2))

print('')
print("Opening balance:", '{:.2f}'.format(openingBalance))
print("Closing balance:", '{:.2f}'.format(
    round(account.getBalanceFIAT() + addBalance, 2)))
print("         Result:", result)
print('')

tradinggraphs = TradingGraphs(coinbasepro)
tradinggraphs.renderBuySellSignalEMA1226MACD()