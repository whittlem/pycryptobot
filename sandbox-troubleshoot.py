import pandas as pd
from models.Trading import TechnicalAnalysis
from models.CoinbasePro import PublicAPI

api = PublicAPI()
data = api.getHistoricalData('BCH-GBP', 3600)

ta = TechnicalAnalysis(data)
ta.addEMA(12)
ta.addEMA(26)
ta.addMACD()
ta.addOBV()
ta.addEMABuySignals()
ta.addMACDBuySignals()

df = ta.getDataFrame()
print (df.iloc[247:291][['close','ema12','ema26','ema12gtema26','ema12gtema26co','ema12ltema26','ema12ltema26co','macd','signal','macdgtsignal','macdltsignal','obv_pc']])