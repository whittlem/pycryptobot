import pandas as pd

from models.CoinbasePro import CoinbasePro
from views.TradingGraphs import TradingGraphs

coinbasepro = CoinbasePro('BTC-USD', 3600)
coinbasepro.addEMABuySignals()
#coinbasepro.addMACDBuySignals()

print (coinbasepro.getDataFrame())
#coinbasepro.addMomentumIndicators()
#print (coinbasepro.getDataFrame())
#print (coinbasepro.getSupportResistanceLevels())
#coinbasepro.saveCSV()

#tradinggraphs = TradingGraphs(coinbasepro)
#tradinggraphs.renderPriceEMA12EMA26()
#tradinggraphs.renderPriceSupportResistance()
#tradinggraphs.renderEMAandMACD()
#tradinggraphs.renderSMAandMACD()
#tradinggraphs.renderSeasonalARIMAModel()
#tradinggraphs.renderSeasonalARIMAModelPredictionDays(30)