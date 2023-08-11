import sys

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.Trading import TechnicalAnalysis  # noqa: E402
from views.TradingGraphs import TradingGraphs  # noqa: E402

# app = PyCryptoBot()
app = PyCryptoBot("binance")
trading_data = app.get_historical_data(app.market, app.granularity, None)

technical_analysis = TechnicalAnalysis(trading_data, app=app)
technical_analysis.add_all()

tradinggraphs = TradingGraphs(technical_analysis, app)
# tradinggraphs.render_fibonacci_retracement(True)
# tradinggraphs.render_support_resistance(True)
# tradinggraphs.render_candle_sticks(30, True)
tradinggraphs.render_bollinger_bands()
