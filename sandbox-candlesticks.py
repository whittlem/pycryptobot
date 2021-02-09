import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from models.Trading import TechnicalAnalysis
from models.CoinbasePro import PublicAPI
from views.TradingGraphs import TradingGraphs

market = 'BTC-GBP'
granularity = 3600

api = PublicAPI()
tradingData = api.getHistoricalData(market, granularity)
technicalAnalysis = TechnicalAnalysis(tradingData)
technicalAnalysis.addEMA(12)
technicalAnalysis.addEMA(26)
technicalAnalysis.addCandleHammer()
technicalAnalysis.addCandleInvertedHammer()
technicalAnalysis.addCandleShootingStar()
technicalAnalysis.addCandleHangingMan()
technicalAnalysis.addCandleThreeWhiteSoldiers()
technicalAnalysis.addCandleThreeBlackCrows()
technicalAnalysis.addCandleDoji()
technicalAnalysis.addCandleThreeLineStrike()
technicalAnalysis.addCandleTwoBlackGapping()
technicalAnalysis.addCandleEveningStar()
technicalAnalysis.addCandleAbandonedBaby()
df = technicalAnalysis.getDataFrame()

tradinggraphs = TradingGraphs(technicalAnalysis)
tradinggraphs.renderEMA12EMA26CloseCandles()
#tradinggraphs.renderEMA12EMA26CloseCandles(30, 'candles.png')