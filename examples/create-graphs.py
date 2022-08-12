import sys
sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.Trading import TechnicalAnalysis  # noqa: E402
from views.TradingGraphs import TradingGraphs  # noqa: E402

# app = PyCryptoBot()
app = PyCryptoBot('binance')
trading_data = app.get_historical_data(app.market, app.granularity, None)

technicalAnalysis = TechnicalAnalysis(trading_data)
technicalAnalysis.add_all()

tradinggraphs = TradingGraphs(technicalAnalysis)
tradinggraphs.renderFibonacciRetracement(True)
tradinggraphs.renderSupportResistance(True)
tradinggraphs.renderCandlesticks(30, True)
tradinggraphs.renderArima_model_prediction(1, True)
