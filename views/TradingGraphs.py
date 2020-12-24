import datetime
import sys
sys.path.append('.')
from models.CoinbasePro import CoinbasePro
import matplotlib.pyplot as plt
import pandas as pd

class TradingGraphs():
    def __init__(self, coinbasepro):
        if not isinstance(coinbasepro, CoinbasePro):
            raise TypeError('Coinbase Pro model required.')

        self.coinbasepro = coinbasepro
        self.df = coinbasepro.getDataFrame()
        self.levels = coinbasepro.getSupportResistanceLevels()

    def renderPriceEMA12EMA26(self):
        ''' Render Price, EMA12 and EMA26 '''

        plt.subplot(111)
        plt.plot(self.df.close, label="price")
        plt.plot(self.df.ema12, label="ema12")
        plt.plot(self.df.ema26, label="ema26")
        plt.legend()
        plt.ylabel('Price')
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.show()

    def renderPriceSupportResistance(self):
        ''' Render Price, Support and Resistance Levels '''

        plt.subplot(111)
        plt.plot(self.df.close)
        plt.legend()
        plt.ylabel('Price')
        plt.xlabel('Days')

        print (self.levels)

        for level in self.levels:
            plt.hlines(level[1], xmin=level[0], xmax=len(self.df), colors='blue')
       
        plt.show()

    def renderEMAandMACD(self):
        ''' Render Price, EMA12, EMA26 and MACD '''

        ax1 = plt.subplot(211)
        plt.plot(self.df.close, label="price")
        plt.plot(self.df.ema12, label="ema12")
        plt.plot(self.df.ema26, label="ema26")
        plt.xticks(self.df.close, rotation='vertical')
        plt.legend()
        plt.ylabel('Price')
        plt.subplot(212, sharex=ax1)
        plt.plot(self.df.macd, label="macd")
        plt.plot(self.df.signal, label="signal")
        plt.legend()
        plt.ylabel('Divergence')
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.show()

    def renderSeasonalARIMAModel(self):
        ''' Render Seasonal ARIMA Model '''

        ts = self.df['close']
        results_ARIMA = self.coinbasepro.getSeasonalARIMAModel(ts)

        plt.plot(ts, label='original')
        plt.plot(results_ARIMA.fittedvalues, color='red', label='fitted')
        plt.title('RSS: %.4f'% sum((results_ARIMA.fittedvalues-ts)**2))
        plt.legend()
        plt.ylabel('Price')
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.show()

    def renderSeasonalARIMAModelPredictionDays(self, days=30):
        ''' Render Seasonal ARIMA Model Prediction '''

        ts = self.df['close']
        results_ARIMA = self.coinbasepro.getSeasonalARIMAModel(ts)

        df = pd.DataFrame(ts)
        start_date = df.last_valid_index()
        end_date = start_date + datetime.timedelta(days=days)
        pred = results_ARIMA.predict(start=str(start_date), end=str(end_date), dynamic=True)

        plt.plot(pred, label='prediction')
        plt.ylabel('Price')
        plt.xlabel('Days')
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.show()

    def renderSMAandMACD(self):
        ''' Render Price, SMA20, SMA50, and SMA200 '''

        ax1 = plt.subplot(211)
        plt.plot(self.df.close, label="price")
        plt.plot(self.df.sma20, label="sma20")
        plt.plot(self.df.sma50, label="sma50")
        plt.plot(self.df.sma200, label="sma200")
        plt.legend()
        plt.ylabel('Price')
        plt.xticks(rotation=90)
        plt.subplot(212, sharex=ax1)
        plt.plot(self.df.macd, label="macd")
        plt.plot(self.df.signal, label="signal")
        plt.legend()
        plt.ylabel('Price')
        plt.xlabel('Days')
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.show()
