#import numpy as np
#import matplotlib.pyplot as plt
#import matplotlib.ticker as ticker
from models.PyCryptoBot import PyCryptoBot
from models.Trading import TechnicalAnalysis
from models.Binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI
from models.CoinbasePro import AuthAPI as CBAuthAPI, PublicAPI as CBPublicAPI
from views.TradingGraphs import TradingGraphs

app = PyCryptoBot()
tradingData = app.getHistoricalData(app.getMarket(), app.getGranularity())

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
technicalAnalysis.addCandleMorningDojiStar()
technicalAnalysis.addCandleEveningDojiStar()
technicalAnalysis.addCandleThreeLineStrike()
technicalAnalysis.addCandleTwoBlackGapping()
technicalAnalysis.addCandleMorningStar()
technicalAnalysis.addCandleEveningStar()
technicalAnalysis.addCandleAbandonedBaby()
df = technicalAnalysis.getDataFrame()

tradinggraphs = TradingGraphs(technicalAnalysis)
tradinggraphs.renderCandlesticks()
#tradinggraphs.rrenderCandlestickss(30, True)