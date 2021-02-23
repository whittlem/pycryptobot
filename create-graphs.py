from models.PyCryptoBot import PyCryptoBot
from models.Trading import TechnicalAnalysis
from models.Binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI
from models.CoinbasePro import AuthAPI as CBAuthAPI, PublicAPI as CBPublicAPI
from views.TradingGraphs import TradingGraphs

app = PyCryptoBot()
tradingData = app.getHistoricalData(app.getMarket(), app.getGranularity())

technicalAnalysis = TechnicalAnalysis(tradingData)
technicalAnalysis.addAll()

tradinggraphs = TradingGraphs(technicalAnalysis)
tradinggraphs.renderFibonacciRetracement(True)
tradinggraphs.renderSupportResistance(True)
tradinggraphs.renderCandlesticks(30, True)
tradinggraphs.renderSeasonalARIMAModelPrediction(1, True)