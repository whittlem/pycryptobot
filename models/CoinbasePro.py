"""Retrieves data via the Coinbase Pro public API for analysis"""

import json
import numpy as np
import pandas as pd
import re
import requests
from datetime import datetime, timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX

class CoinbasePro():
    def __init__(self, market='BTC-GBP', granularity=86400, iso8601start='', iso8601end=''):
        """Coinbase Pro object model
    
        Parameters
        ----------
        market : str
            A valid market/product from the Coinbase Pro exchange. (Default: 'BTC-GBP')
        granularity : int
            A valid market interval {60, 300, 900, 3600, 21600, 86400} (Default: 86400 - 1 day)
        iso8601start : str, optional
            The start date of the data in ISO 8601 format. If excluded starts from the last 300 intervals
        iso8601end : str, optional
            The end date of the data in ISO 8601 format. If excluded ends at the current time
        """

        # set to True for verbose output
        self.debug = False

        # the DataFrame will only ever be 300 rows, uncomment the line below to output all 300 rows
        #pd.set_option('display.max_rows', None)

        '''
        NOTE: rounding potentially causing problems

        # conditional formatting for floats
        if market.endswith('EUR') or market.endswith('GBP') or market.endswith('USD'):
            # 2 decimal places for fiat
            pd.set_option('display.float_format','{:.2f}'.format)
        else:
            # 5 decimal places for crypto
            pd.set_option('display.float_format','{:.5f}'.format)
        '''

        # validates the market is syntactically correct
        p = re.compile(r"^[A-Z]{3,4}\-[A-Z]{3,4}$")
        if not p.match(market):
            raise TypeError('Coinbase Pro market required.')

        # validates granularity is an integer
        if not isinstance(granularity, int):
            raise TypeError('Granularity integer required.')

        # validates the granularity is supported by Coinbase Pro
        if not granularity in [60, 300, 900, 3600, 21600, 86400]:
            raise TypeError(
                'Granularity options: 60, 300, 900, 3600, 21600, 86400.')

        # validates the ISO 8601 start date is a string (if provided)
        if not isinstance(iso8601start, str):
            raise TypeError('ISO8601 start integer as string required.')

        # validates the ISO 8601 end date is a string (if provided)
        if not isinstance(iso8601end, str):
            raise TypeError('ISO8601 end integer as string required.')

        self.market = market
        self.granularity = granularity
        self.iso8601start = iso8601start
        self.iso8601end = iso8601end

        # if only a start date is provided
        if self.iso8601start != '' and self.iso8601end == '':
            multiplier = 1
            if(self.granularity == 60):
                multiplier = 1
            elif(self.granularity == 300):
                multiplier = 5
            elif(self.granularity == 900):
                multiplier = 10
            elif(self.granularity == 3600):
                multiplier = 60
            elif(self.granularity == 21600):
                multiplier = 360
            elif(self.granularity == 86400):
                multiplier = 1440

            # calculate the end date using the granularity
            self.iso8601end = str((datetime.strptime(self.iso8601start, '%Y-%m-%dT%H:%M:%S.%f') + timedelta(minutes=granularity * multiplier)).isoformat()) 

        # constructs the API url
        self.api_url = 'https://api.pro.coinbase.com/products/' + market + '/candles?granularity=' + \
            str(granularity) + '&start=' + self.iso8601start + '&end=' + self.iso8601end

        try:
            resp = requests.get(self.api_url)

            if resp.status_code != 200:
                raise Exception('GET ' + self.api_url + ' {}'.format(resp.status_code))

            resp.raise_for_status()

        except requests.ConnectionError as err:
            if self.debug:
                raise SystemExit(err)
            else:
                raise SystemExit('ConnectionError: ' + self.api_url)
        except requests.exceptions.HTTPError as err:
            if self.debug:
                raise SystemExit(err)
            else:
                raise SystemExit('HTTPError: ' + self.api_url)
        except requests.Timeout as err:
            if self.debug:
                raise SystemExit(err)
            else:
                raise SystemExit('Timeout: ' + self.api_url) 

        # convert the API response into a Pandas DataFrame
        self.df = pd.DataFrame(resp.json(), columns=['epoch', 'low', 'high', 'open', 'close', 'volume'])
        # reverse the order of the response with earliest last
        self.df = self.df.iloc[::-1].reset_index()

        if len(self.df) < 200:
            self.df = pd.DataFrame()
            raise Exception('Insufficient data between ' + self.iso8601start + ' and ' + self.iso8601end + ' (DataFrame length: ' + str(len(self.df)) + ')')

        if(granularity == 60):
            freq = 'T'
        elif(granularity == 300):
            freq = '5T'
        elif(granularity == 900):
            freq = '15T'
        elif(granularity == 3600):
            freq = 'H'
        elif(granularity == 21600):
            freq = '6H'
        else:
            freq = 'D'

        # convert the DataFrame into a time series with the date as the index/key
        try:
            tsidx = pd.DatetimeIndex(pd.to_datetime(self.df['epoch'], unit='s'), dtype='datetime64[ns]', freq=freq)
            self.df.set_index(tsidx, inplace=True)
            self.df = self.df.drop(columns=['epoch','index'])
            self.df.index.names = ['ts']
        except ValueError:
            tsidx = pd.DatetimeIndex(pd.to_datetime(self.df['epoch'], unit='s'), dtype='datetime64[ns]')
            self.df.set_index(tsidx, inplace=True)
            self.df = self.df.drop(columns=['epoch','index'])
            self.df.index.names = ['ts']           

        # close change percentage
        self.df['close_pc'] = self.df['close'].pct_change() * 100
        self.df['close_pc'] = np.round(self.df['close_pc'].fillna(0), 2)

        self.levels = [] 
        self.__calculateSupportResistenceLevels()
        levels_ts = {}
        for level in self.levels:
            levels_ts[self.df.index[level[0]]] = level[1]
        # add the support levels to the DataFrame
        self.levels_ts = pd.Series(levels_ts)

    """Getters"""

    def getAPI(self):
        """Returns the Coinbase Pro API URL"""
        return self.api_url

    def getDataFrame(self):
        """Returns the Pandas DataFrame"""
        return self.df

    def getMarket(self):
        """Returns the configured market"""
        return self.market

    def getGranularity(self):
        """Returns the configured granulatory"""
        return self.granularity

    def getISO8601Start(self):
        """Returns the configured ISO 8601 start date"""
        return self.iso8601start

    def getISO8601End(self):
        """Returns the configured ISO 8601 end date"""
        return self.iso8601end

    def getSeasonalARIMAModel(self, ts):
        """Returns the Seasonal ARIMA Model for price predictions"""
        if not isinstance(ts, pd.Series):
            raise TypeError('Pandas Time Series required.')

        if not isinstance(self.df, pd.DataFrame):
            raise TypeError('Pandas DataFrame required.')

        if not 'close' in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        """Parameters for SARIMAX"""
        model = SARIMAX(ts, trend='n', order=(0,1,0), seasonal_order=(1,1,1,12))
        return model.fit(disp=-1)

    def getSupportResistanceLevels(self):
        """Returns the calculated support levels in the DataFrame"""
        return self.levels

    def getSupportResistanceLevelsTimeSeries(self):
        """Returns the calculated support levels as time series"""
        return self.levels_ts

    """Setters"""

    def addEMABuySignals(self):
        """Adds the EMA12/EMA26 buy and sell signals to the DataFrame"""
        if not isinstance(self.df, pd.DataFrame):
            raise TypeError('Pandas DataFrame required.')

        if not 'close' in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not self.df['close'].dtype == 'float64' and not self.df['close'].dtype == 'int64':
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64.")

        if not 'ema12' or not 'ema26' in self.df.columns:
            self.addMovingAverages()

        # true if EMA12 is above the EMA26
        self.df['ema12gtema26'] = self.df.ema12 > self.df.ema26
        # true if the current frame is where EMA12 crosses over above
        self.df['ema12gtema26co'] = self.df.ema12gtema26.ne(self.df.ema12gtema26.shift())
        self.df.loc[self.df['ema12gtema26'] == False, 'ema12gtema26co'] = False

        # true if the EMA12 is below the EMA26
        self.df['ema12ltema26'] = self.df.ema12 < self.df.ema26
        # true if the current frame is where EMA12 crosses over below
        self.df['ema12ltema26co'] = self.df.ema12ltema26.ne(self.df.ema12ltema26.shift())
        self.df.loc[self.df['ema12ltema26'] == False, 'ema12ltema26co'] = False

    def addMACDBuySignals(self):
        """Adds the MACD/Signal buy and sell signals to the DataFrame"""
        if not isinstance(self.df, pd.DataFrame):
            raise TypeError('Pandas DataFrame required.')

        if not 'close' in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not self.df['close'].dtype == 'float64' and not self.df['close'].dtype == 'int64':
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64.")

        if not 'macd' or not 'signal' in self.df.columns:
            self.addMomentumIndicators()

        # true if MACD is above the Signal
        self.df['macdgtsignal'] = self.df.macd > self.df.signal
        # true if the current frame is where MACD crosses over above
        self.df['macdgtsignalco'] = self.df.macdgtsignal.ne(self.df.macdgtsignal.shift())
        self.df.loc[self.df['macdgtsignal'] == False, 'macdgtsignalco'] = False

        # true if the MACD is below the Signal
        self.df['macdltsignal'] = self.df.macd < self.df.signal
        # true if the current frame is where MACD crosses over below
        self.df['macdltsignalco'] = self.df.macdltsignal.ne(self.df.macdltsignal.shift())
        self.df.loc[self.df['macdltsignal'] == False, 'macdltsignalco'] = False

        # true if OBV is greater than 2%
        self.df['obvsignal'] = self.df.obv_pc > 2

    def addMovingAverages(self):
        """Appends CMA, EMA12, EMA26, SMA20, SMA50, and SMA200 moving averages to a dataframe."""

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
        """Appends RSI14 and MACD momentum indicators to a dataframe."""

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
        """Calculates the RSI on a Pandas series of closing prices."""

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
        """Saves the DataFrame to an uncompressed CSV."""

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
        """Support and Resistance levels. (private function)"""

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
        """Is support level? (privte function)"""

        c1 = df['low'][i] < df['low'][i - 1]
        c2 = df['low'][i] < df['low'][i + 1]
        c3 = df['low'][i + 1] < df['low'][i + 2]
        c4 = df['low'][i - 1] < df['low'][i - 2]
        support = c1 and c2 and c3 and c4
        return support

    def __isResistance(self, df, i):
        """Is resistance level? (private function)"""

        c1 = df['high'][i] > df['high'][i - 1]
        c2 = df['high'][i] > df['high'][i + 1]
        c3 = df['high'][i + 1] > df['high'][i + 2]
        c4 = df['high'][i - 1] > df['high'][i - 2]
        resistance = c1 and c2 and c3 and c4
        return resistance

    def __isFarFromLevel(self, l):
        """Is far from support level? (private function)"""

        s = np.mean(self.df['high'] - self.df['low'])
        return np.sum([abs(l-x) < s for x in self.levels]) == 0