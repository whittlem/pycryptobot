"""Technical analysis on a trading Pandas DataFrame"""

import json
import numpy as np
import pandas as pd
import re
from statsmodels.tsa.statespace.sarimax import SARIMAX
from models.CoinbaseProAPI import AuthAPI

class TechnicalAnalysis():
    def __init__(self, data=pd.DataFrame()):
        """Technical Analysis object model
    
        Parameters
        ----------
        data : Pandas Time Series
            data[ts] = ['low', 'high', 'open', 'close', 'volume']
        """

        if not isinstance(data, pd.DataFrame):
            raise TypeError('Data is not a Pandas dataframe.')

        if list(data.keys()) != ['low', 'high', 'open', 'close', 'volume']:
            raise ValueError('Data not not contain low, high, open, close, volume')

        if not 'close' in data.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not data['close'].dtype == 'float64' and not data['close'].dtype == 'int64':
            raise AttributeError("Pandas DataFrame 'close' column not int64 or float64.")

        self.df = data
        self.levels = []

    def getDataFrame(self):
        """Returns the Pandas DataFrame"""

        return self.df

    def addAll(self):
        """Adds analysis to the DataFrame"""

        self.addChangePct()
        self.addCMA()
        self.addSMA(20)
        self.addSMA(50)
        self.addSMA(200)
        self.addEMA(12)
        self.addEMA(26)
        self.addRSI(14)
        self.addMACD()
        self.addOBV()
        self.addEMABuySignals()
        self.addMACDBuySignals()       

    def changePct(self):
        """Close change percentage"""

        close_pc = self.df['close'].pct_change() * 100
        close_pc = np.round(close_pc.fillna(0), 2)
        return close_pc
    
    def addChangePct(self):
        """Adds the close percentage to the DataFrame"""

        self.df['close_pc'] = self.changePct()

    def cumulativeMovingAverage(self):
        """Calculates the Cumulative Moving Average (CMA)"""

        return self.df.close.expanding().mean()

    def addCMA(self):
        """Adds the Cumulative Moving Average (CMA) to the DataFrame"""

        self.df['cma'] = self.cumulativeMovingAverage()

    def exponentialMovingAverage(self, period):
        """Calculates the Exponential Moving Average (EMA)"""

        if not isinstance(period, int):
            raise TypeError('Period parameter is not perioderic.')

        if period < 5 or period > 200:
            raise ValueError('Period is out of range')

        if len(self.df) < period:
            raise Exception('Data range too small.')

        return self.df.close.ewm(span=period, adjust=False).mean()

    def addEMA(self, period):
        """Adds the Exponential Moving Average (EMA) the DateFrame"""

        if not isinstance(period, int):
            raise TypeError('Period parameter is not perioderic.')

        if period < 5 or period > 200:
            raise ValueError('Period is out of range')

        if len(self.df) < period:
            raise Exception('Data range too small.')

        self.df['ema' + str(period)] = self.exponentialMovingAverage(period)

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
        avg_losses = sum_losses.ewm(com=interval-1, min_periods=interval).mean()

        rs = abs(avg_gains / avg_losses)
        rsi = 100 - 100 / (1 + rs)

        return rsi

    def movingAverageConvergenceDivergence(self):
        """Calculates the Moving Average Convergence Divergence (MACD)"""

        if len(self.df) < 26:
            raise Exception('Data range too small.')

        if not self.df['ema12'].dtype == 'float64' and not self.df['ema12'].dtype == 'int64':
            raise AttributeError("Pandas DataFrame 'ema12' column not int64 or float64.")

        if not self.df['ema26'].dtype == 'float64' and not self.df['ema26'].dtype == 'int64':
            raise AttributeError("Pandas DataFrame 'ema26' column not int64 or float64.")

        df = pd.DataFrame()
        df['macd'] = self.df['ema12'] - self.df['ema26']
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()        
        return df

    def addMACD(self):
        """Adds the Moving Average Convergence Divergence (MACD) to the DataFrame"""

        df = self.movingAverageConvergenceDivergence()
        self.df['macd'] = df['macd']
        self.df['signal'] = df['signal']

    def onBalanceVolume(self):
        """Calculate On-Balance Volume (OBV)"""

        return np.where(self.df['close'] > self.df['close'].shift(1), self.df['volume'], 
        np.where(self.df['close'] < self.df['close'].shift(1), -self.df['volume'], self.df.iloc[0]['volume'])).cumsum()

    def addOBV(self):
        """Add the On-Balance Volume (OBV) to the DataFrame"""

        self.df['obv'] = self.onBalanceVolume()
        self.df['obv_pc'] = self.df['obv'].pct_change() * 100
        self.df['obv_pc'] = np.round(self.df['obv_pc'].fillna(0), 2)  

    def relativeStrengthIndex(self, period):
        """Calculate the Relative Strength Index (RSI)"""

        if not isinstance(period, int):
            raise TypeError('Period parameter is not perioderic.')

        if period < 7 or period > 21:
            raise ValueError('Period is out of range')

        # calculate relative strength index
        rsi = self.calculateRelativeStrengthIndex(self.df['close'], period)
        # default to midway-50 for first entries
        rsi = rsi.fillna(50)
        return rsi

    def addRSI(self, period):
        """Adds the Relative Strength Index (RSI) to the DataFrame"""

        if not isinstance(period, int):
            raise TypeError('Period parameter is not perioderic.')

        if period < 7 or period > 21:
            raise ValueError('Period is out of range')

        self.df['rsi' + str(period)] = self.relativeStrengthIndex(period)   
        self.df['rsi' + str(period)] = self.df['rsi' + str(period)].replace(np.nan, 50)

    def seasonalARIMAModel(self):
        """Returns the Seasonal ARIMA Model for price predictions"""

        # parameters for SARIMAX
        model = SARIMAX(self.df['close'], trend='n', order=(0,1,0), seasonal_order=(1,1,1,12))
        return model.fit(disp=-1)

    def seasonalARIMAModelFittedValues(self):
        """Returns the Seasonal ARIMA Model for price predictions"""

        return self.seasonalARIMAModel().fittedvalues

    def simpleMovingAverage(self, period):
        """Calculates the Simple Moving Average (SMA)"""

        if not isinstance(period, int):
            raise TypeError('Period parameter is not perioderic.')

        if period < 5 or period > 200:
            raise ValueError('Period is out of range')

        if len(self.df) < period:
            raise Exception('Data range too small.')

        return self.df.close.rolling(period, min_periods=1).mean()

    def addSMA(self, period):
        """Add the Simple Moving Average (SMA) to the DataFrame"""

        if not isinstance(period, int):
            raise TypeError('Period parameter is not perioderic.')

        if period < 5 or period > 200:
            raise ValueError('Period is out of range')

        if len(self.df) < period:
            raise Exception('Data range too small.')

        self.df['sma' + str(period)] = self.simpleMovingAverage(period)   

    def supportResistanceLevels(self):
        """Calculate the Support and Resistance Levels"""

        self.levels = [] 
        self.__calculateSupportResistenceLevels()
        levels_ts = {}
        for level in self.levels:
            levels_ts[self.df.index[level[0]]] = level[1]
        # add the support levels to the DataFrame
        return pd.Series(levels_ts)

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
            self.addEMA(12)
            self.addEMA(26)

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
            raise AttributeError("Pandas DataFrame 'close' column not int64 or float64.")

        if not 'macd' or not 'signal' in self.df.columns:
            self.addMACD()
            self.addOBV()

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

    def saveCSV(self, filename='tradingdata.csv'):
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