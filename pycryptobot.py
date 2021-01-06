import random
from datetime import datetime, timedelta
from models.CoinbasePro import CoinbasePro
from views.TradingGraphs import TradingGraphs

coinbasepro = CoinbasePro()
print (coinbasepro.getDataFrame())
coinbasepro.addMomentumIndicators()
print (coinbasepro.getDataFrame())
print (coinbasepro.getSupportResistanceLevels())
#coinbasepro.saveCSV()

tradinggraphs = TradingGraphs(coinbasepro)
#tradinggraphs.renderBuySellSignalEMA1226()
#tradinggraphs.renderBuySellSignalEMA1226MACD()
#tradinggraphs.renderPriceEMA12EMA26()
#tradinggraphs.renderPriceSupportResistance()
#tradinggraphs.renderEMAandMACD()
#tradinggraphs.renderSMAandMACD()
#tradinggraphs.renderSeasonalARIMAModel()
tradinggraphs.renderSeasonalARIMAModelPredictionDays(30)