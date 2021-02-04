"""Trading Graphs object model examples"""

import pandas as pd
from models.Trading import TechnicalAnalysis
from models.CoinbasePro import PublicAPI
from views.TradingGraphs import TradingGraphs

api = PublicAPI()
tradingData = api.getHistoricalData('BTC-GBP', 3600)

technicalAnalysis = TechnicalAnalysis(tradingData)
technicalAnalysis.addAll()

tradinggraphs = TradingGraphs(technicalAnalysis)

"""Uncomment the diagram to display"""

tradinggraphs.renderPriceEMA12EMA26()

#tradinggraphs.renderEMAandMACD()
#tradinggraphs.renderSMAandMACD()

#tradinggraphs.renderBuySellSignalEMA1226()
#tradinggraphs.renderBuySellSignalEMA1226MACD()

#tradinggraphs.renderPriceSupportResistance()

#tradinggraphs.renderSeasonalARIMAModel()
#tradinggraphs.renderSeasonalARIMAModelPredictionDays(5)