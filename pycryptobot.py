import pandas as pd
import json, requests
from models.CoinbasePro import CoinbasePro
from models.CoinbaseProAPI import CoinbaseProAPI
from views.TradingGraphs import TradingGraphs

'''
with open('config.json') as config_file:
    config = json.load(config_file)

model = CoinbaseProAPI(config['api_key'], config['api_secret'], config['api_pass'], config['api_url'])
data = model.getAccounts()
data = model.getAccount('b0d0824f-01d4-42a3-bff8-365ea451907c')
print (data[['currency','balance']])
'''

coinbasepro = CoinbasePro('BTC-USD', 3600)
coinbasepro.addEMABuySignals()
coinbasepro.addMACDBuySignals()
df = coinbasepro.getDataFrame()

buysignals = (df.ema12gtema26co == True) & (df.macdgtsignal == True) & (df.obv_pc > 0)
sellsignals = (df.ema12ltema26co == True) & (df.macdltsignal == True) & (df.obv_pc < 0)
df_signals = df[(buysignals) | (sellsignals)]
#print (df_signals[['close','ema12','ema26','macd','signal','obv_pc','ema12gtema26co','macdgtsignal','ema12ltema26co','macdltsignal']])

action = ''
last_action = ''
for index, row in df_signals.iterrows():
    if row['ema12gtema26co'] == True and row['macdgtsignal'] == True and row['obv_pc'] >= 0:
        action = 'buy'
    elif row['ema12ltema26co'] == True and row['macdltsignal'] == True and row['obv_pc'] < 0:
        action = 'sell'

    if action != '' and action != last_action:
        print(action, index, row['close'], row['ema12'], row['ema26'], row['macd'], row['signal'], row['obv_pc'], row['ema12gtema26co'], row['macdgtsignal'], row['ema12ltema26co'], row['macdltsignal'])
        last_action = action

'''
#print (coinbasepro.getDataFrame())
#coinbasepro.addMomentumIndicators()
#print (coinbasepro.getDataFrame())
#print (coinbasepro.getSupportResistanceLevels())
#coinbasepro.saveCSV()

#tradinggraphs = TradingGraphs(coinbasepro)
#tradinggraphs.renderBuySellSignalEMA1226()
#tradinggraphs.renderBuySellSignalEMA1226MACD()
#tradinggraphs.renderPriceEMA12EMA26()
#tradinggraphs.renderPriceSupportResistance()
#tradinggraphs.renderEMAandMACD()
#tradinggraphs.renderSMAandMACD()
#tradinggraphs.renderSeasonalARIMAModel()
#tradinggraphs.renderSeasonalARIMAModelPredictionDays(30)
'''