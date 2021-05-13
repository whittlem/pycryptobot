from models.PyCryptoBot import PyCryptoBot
from models.Trading import TechnicalAnalysis
from views.TradingGraphs import TradingGraphs

app = PyCryptoBot()
trading_data = app.getHistoricalData(app.getMarket(), app.getGranularity())

ta = TechnicalAnalysis(trading_data)
ta.addAll()

df_data = ta.getDataFrame()
df_fib = ta.getFibonacciRetracementLevels()
df_sr = ta.getSupportResistanceLevels()

print (df_data)
print (df_fib)
print (df_sr)

graphs = TradingGraphs(ta)
#graphs.renderBuySellSignalEMA1226MACD(saveOnly=False)
#graphs = TradingGraphs(ta)
#graphs.renderPercentageChangeHistogram()
#graphs.renderCumulativeReturn()
#graphs.renderPercentageChangeScatterMatrix()
graphs.renderFibonacciBollingerBands(period=24)