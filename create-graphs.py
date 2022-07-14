from models.PyCryptoBot import PyCryptoBot
from models.Trading import TechnicalAnalysis
from views.TradingGraphs import TradingGraphs

#app = PyCryptoBot()
app = PyCryptoBot('binance')
trading_data = app.get_historical_data(app.market, app.granularity)

technicalAnalysis = TechnicalAnalysis(trading_data)
technicalAnalysis.addAll()

tradinggraphs = TradingGraphs(technicalAnalysis)
tradinggraphs.renderFibonacciRetracement(True)
tradinggraphs.renderSupportResistance(True)
tradinggraphs.renderCandlesticks(30, True)
tradinggraphs.renderArima_model_prediction(1, True)