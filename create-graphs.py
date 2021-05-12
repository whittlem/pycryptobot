from models.PyCryptoBot import PyCryptoBot
from models.Trading import TechnicalAnalysis
from views.TradingGraphs import TradingGraphs

#app = PyCryptoBot()
app = PyCryptoBot('binance')
tradingData = app.getHistoricalData(app.getMarket(), app.getGranularity())

technicalAnalysis = TechnicalAnalysis(tradingData)
technicalAnalysis.addAll()

tradinggraphs = TradingGraphs(technicalAnalysis)
tradinggraphs.renderFibonacciRetracement(True)
tradinggraphs.renderSupportResistance(True)
tradinggraphs.renderCandlesticks(30, True)
tradinggraphs.renderSeasonalARIMAModelPrediction(1, True)