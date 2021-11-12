from pycryptobot.models.PyCryptoBot import PyCryptoBot
from pycryptobot.models.Trading import TechnicalAnalysis
from pycryptobot.views.TradingGraphs import TradingGraphs
from cement import TestApp

with TestApp() as cementApp:
    cementApp.run()
    app = PyCryptoBot(cementApp, 'binance')
    tradingData = app.getHistoricalData(app.getMarket(), app.getGranularity(), websocket=None)

    technicalAnalysis = TechnicalAnalysis(tradingData)
    technicalAnalysis.addAll()

    tradinggraphs = TradingGraphs(technicalAnalysis)
    tradinggraphs.renderFibonacciRetracement(True)
    tradinggraphs.renderSupportResistance(True)
    tradinggraphs.renderCandlesticks(30, True)
    tradinggraphs.renderSeasonalARIMAModelPrediction(1, True)