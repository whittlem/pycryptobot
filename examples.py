import random
from datetime import datetime, timedelta
from models.CoinbasePro import CoinbasePro
from views.TradingGraphs import TradingGraphs

coinbasepro = CoinbasePro()
#coinbasepro = CoinbasePro('BTC-GBP',3600)
coinbasepro.addMovingAverages()
coinbasepro.addMomentumIndicators()
coinbasepro.addEMABuySignals()
coinbasepro.addMACDBuySignals()
print (coinbasepro.getDataFrame())
print (coinbasepro.getSupportResistanceLevels())

tradinggraphs = TradingGraphs(coinbasepro)
#tradinggraphs.renderBuySellSignalEMA1226()
#tradinggraphs.renderBuySellSignalEMA1226MACD()
tradinggraphs.renderPriceEMA12EMA26()
#tradinggraphs.renderPriceSupportResistance()
#tradinggraphs.renderEMAandMACD()
#tradinggraphs.renderSMAandMACD()
#tradinggraphs.renderSeasonalARIMAModel()
#tradinggraphs.renderSeasonalARIMAModelPredictionDays(5)