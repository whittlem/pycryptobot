"""Trading Graphs object model examples"""

import pandas as pd
from datetime import datetime
from models.Trading import TechnicalAnalysis
from models.CoinbasePro import PublicAPI
from views.TradingGraphs import TradingGraphs

api = PublicAPI()
tradingData = api.getHistoricalData('BTC-GBP', 3600)

technicalAnalysis = TechnicalAnalysis(tradingData)
technicalAnalysis.addAll()

tradinggraphs = TradingGraphs(technicalAnalysis)

"""Uncomment the diagram to display"""

#tradinggraphs.renderEMAandMACD()
#tradinggraphs.renderEMAandMACD(24)
ts = datetime.now().timestamp()
filename = 'BTC-GBP_3600_' + str(ts) + '.png'
tradinggraphs.renderEMAandMACD(24, 'graphs/' + filename, True)

#tradinggraphs.renderPriceEMA12EMA26()

#tradinggraphs.renderEMAandMACD()
#tradinggraphs.renderSMAandMACD()

#tradinggraphs.renderBuySellSignalEMA1226()
#tradinggraphs.renderBuySellSignalEMA1226MACD()

#tradinggraphs.renderPriceSupportResistance()

#tradinggraphs.renderSeasonalARIMAModel()
#tradinggraphs.renderSeasonalARIMAModelPredictionDays(5)