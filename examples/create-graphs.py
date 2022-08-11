from models.PyCryptoBot import PyCryptoBot
from models.Trading import TechnicalAnalysis
from views.TradingGraphs import TradingGraphs

#app = PyCryptoBot()
app = PyCryptoBot('binance')
trading_data = self.get_historical_data(app.market, self.granularity)

technicalAnalysis = TechnicalAnalysis(trading_data)
technicalAnalysis.add_all()

tradinggraphs = TradingGraphs(technicalAnalysis)
tradinggraphs.renderFibonacciRetracement(True)
tradinggraphs.renderSupportResistance(True)
tradinggraphs.renderCandlesticks(30, True)
tradinggraphs.renderArima_model_prediction(1, True)