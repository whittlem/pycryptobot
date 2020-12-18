import json
import numpy as np
import pandas as pd
import re
import requests
from datetime import datetime
from statsmodels.tsa.statespace.sarimax import SARIMAX

class CoinbasePro():
    def __init__(self, market='BTC-GBP', granularity=86400, iso8601start='', iso8601end=''):
        p = re.compile(r"^[A-Z]{3,4}\-[A-Z]{3,4}$")
        if not p.match(market):
            raise TypeError('Coinbase Pro market required.')

        if not isinstance(granularity, int):
            raise TypeError('Granularity integer required.')

        if not granularity in [60, 300, 900, 3600, 21600, 86400]:
            raise TypeError(
                'Granularity options: 60, 300, 900, 3600, 21600, 86400.')

        if not isinstance(iso8601start, str):
            raise TypeError('ISO8601 start integer as string required.')

        if not isinstance(iso8601end, str):
            raise TypeError('ISO8601 end integer as string required.')

        self.market = market
        self.granularity = granularity
        self.iso8601start = iso8601start
        self.iso8601end = iso8601end

        self.api = 'https://api.pro.coinbase.com/products/' + market + '/candles?granularity=' + \
            str(granularity) + '&start=' + iso8601start + '&end=' + iso8601end
        resp = requests.get(self.api)
        if resp.status_code != 200:
            raise Exception('GET ' + self.api + ' {}'.format(resp.status_code))

        self.df = pd.DataFrame(resp.json(), columns=['epoch', 'low', 'high', 'open', 'close', 'volume'])
        self.df = self.df.iloc[::-1].reset_index()

        datetimeidx = pd.DatetimeIndex(pd.to_datetime(self.df['epoch'], unit='s'), dtype='datetime64[ns]', freq='D')
        self.df.set_index(datetimeidx, inplace=True)
        self.df = self.df.drop(columns=['epoch','index'])
        self.df.index.names = ['datetime']

        # close change percentage
        self.df['close_pc'] = self.df['close'].pct_change() * 100
        self.df['close_pc'] = np.round(self.df['close_pc'].fillna(0), 2)

        self.levels = [] 
        self.__calculateSupportResistenceLevels()

    def getAPI(self):
        return self.api

    def getDataFrame(self):
        return self.df

    def getMarket(self):
        return self.market

    def getGranularity(self):
        return self.granularity

    def getISO8601Start(self):
        return self.iso8601start

    def getISO8601End(self):
        return self.iso8601end

    def getSeasonalARIMAModel(self, ts):
        if not isinstance(ts, pd.Series):
            raise TypeError('Pandas Time Series required.')

        if not isinstance(self.df, pd.DataFrame):
            raise TypeError('Pandas DataFrame required.')

        if not 'close' in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        model = SARIMAX(ts, trend='n', order=(0,1,0), seasonal_order=(1,1,1,12))
        return model.fit(disp=-1)

    def getSupportResistanceLevels(self):
        return self.levels

    def addMovingAverages(self):
        '''Appends CMA, EMA12, EMA26, SMA20, SMA50, and SMA200 moving averages to a dataframe.'''

        if not isinstance(self.df, pd.DataFrame):
            raise TypeError('Pandas DataFrame required.')

        if not 'close' in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not self.df['close'].dtype == 'float64' and not self.df['close'].dtype == 'int64':
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64.")

        # calculate cumulative moving average
        self.df['cma'] = self.df.close.expanding().mean()

        # calculate exponential moving averages
        self.df['ema12'] = self.df.close.ewm(span=12, adjust=False).mean()
        self.df['ema26'] = self.df.close.ewm(span=26, adjust=False).mean()

        # calculate simple moving averages
        self.df['sma20'] = self.df.close.rolling(20, min_periods=1).mean()
        self.df['sma50'] = self.df.close.rolling(50, min_periods=1).mean()
        self.df['sma200'] = self.df.close.rolling(200, min_periods=1).mean()

    def addMomentumIndicators(self):
        '''Appends RSI14 and MACD momentum indicators to a dataframe.'''

        if not isinstance(self.df, pd.DataFrame):
            raise TypeError('Pandas DataFrame required.')

        if not 'close' in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not self.df['close'].dtype == 'float64' and not self.df['close'].dtype == 'int64':
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64.")

        if not 'ema12' in self.df.columns:
            self.df['ema12'] = self.df.close.ewm(span=12, adjust=False).mean()

        if not 'ema26' in self.df.columns:
            self.df['ema26'] = self.df.close.ewm(span=26, adjust=False).mean()

        if not self.df['ema12'].dtype == 'float64' and not self.df['ema12'].dtype == 'int64':
            raise AttributeError(
                "Pandas DataFrame 'ema12' column not int64 or float64.")

        if not self.df['ema26'].dtype == 'float64' and not self.df['ema26'].dtype == 'int64':
            raise AttributeError(
                "Pandas DataFrame 'ema26' column not int64 or float64.")

        # calculate relative strength index
        self.df['rsi14'] = self.calculateRelativeStrengthIndex(
            self.df['close'], 14)
        # default to midway-50 for first entries
        self.df['rsi14'] = self.df['rsi14'].fillna(50)

        # calculate moving average convergence divergence
        self.df['macd'] = self.df['ema12'] - self.df['ema26']
        self.df['signal'] = self.df['macd'].ewm(span=9, adjust=False).mean()

        # calculate on-balance volume (obv)
        self.df['obv'] = np.where(self.df['close'] > self.df['close'].shift(1), self.df['volume'], 
        np.where(self.df['close'] < self.df['close'].shift(1), -self.df['volume'], self.df.iloc[0]['volume'])).cumsum()

        # obv change percentage
        self.df['obv_pc'] = self.df['obv'].pct_change() * 100
        self.df['obv_pc'] = np.round(self.df['obv_pc'].fillna(0), 2)

    def calculateRelativeStrengthIndex(self, series, interval=14):
        '''Calculates the RSI on a Pandas series of closing prices.'''

        if not isinstance(series, pd.Series):
            raise TypeError('Pandas Series required.')

        if not isinstance(interval, int):
            raise TypeError('Interval integer required.')

        if(len(series) < interval):
            raise IndexError('Pandas Series smaller than interval.')

        diff = series.diff(1).dropna()

        sum_gains = 0 * diff
        sum_gains[diff > 0] = diff[diff > 0]
        avg_gains = sum_gains.ewm(com=interval-1, min_periods=interval).mean()

        sum_losses = 0 * diff
        sum_losses[diff < 0] = diff[diff < 0]
        avg_losses = sum_losses.ewm(
            com=interval-1, min_periods=interval).mean()

        rs = abs(avg_gains / avg_losses)
        rsi = 100 - 100 / (1 + rs)

        return rsi

    def saveCSV(self, filename='cbpGetHistoricRates.csv'):
        '''Saves the DataFrame to an uncompressed CSV.'''

        p = re.compile(r"^[\w\-. ]+$")
        if not p.match(filename):
            raise TypeError('Filename required.')

        if not isinstance(self.df, pd.DataFrame):
            raise TypeError('Pandas DataFrame required.')

        try:
            self.df.to_csv(filename)
        except OSError:
            print('Unable to save: ', filename)

    def __calculateSupportResistenceLevels(self):
        '''Support and Resistance levels.'''

        for i in range(2, self.df.shape[0] - 2):
            if self.__isSupport(self.df, i):
                l = self.df['low'][i]
                if self.__isFarFromLevel(l):
                    self.levels.append((i, l))
            elif self.__isResistance(self.df, i):
                l = self.df['high'][i]
                if self.__isFarFromLevel(l):
                    self.levels.append((i, l))
        return self.levels

    def __isSupport(self, df, i):
        '''Private function'''

        c1 = df['low'][i] < df['low'][i - 1]
        c2 = df['low'][i] < df['low'][i + 1]
        c3 = df['low'][i + 1] < df['low'][i + 2]
        c4 = df['low'][i - 1] < df['low'][i - 2]
        support = c1 and c2 and c3 and c4
        return support

    def __isResistance(self, df, i):
        '''Private function'''

        c1 = df['high'][i] > df['high'][i - 1]
        c2 = df['high'][i] > df['high'][i + 1]
        c3 = df['high'][i + 1] > df['high'][i + 2]
        c4 = df['high'][i - 1] > df['high'][i - 2]
        resistance = c1 and c2 and c3 and c4
        return resistance

    def __isFarFromLevel(self, l):
        '''Private function'''

        s = np.mean(self.df['high'] - self.df['low'])
        return np.sum([abs(l-x) < s for x in self.levels]) == 0
