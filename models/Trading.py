"""Technical analysis on a trading Pandas DataFrame"""

import json
import numpy as np
import pandas as pd
import re
from statsmodels.tsa.statespace.sarimax import SARIMAX
from models.CoinbasePro import AuthAPI

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

        self.addCandleHammer()
        self.addCandleInvertedHammer()
        self.addCandleShootingStar()
        self.addCandleHangingMan()
        self.addCandleThreeWhiteSoldiers()
        self.addCandleThreeBlackCrows()
        self.addCandleDojo()
        self.addCandleThreeLineStrike()
        self.addCandleTwoBlackGapping()
        self.addCandleEveningStar()
        self.addCandleAbandonedBaby()

    """Candlestick References
    https://commodity.com/technical-analysis
    https://www.investopedia.com
    https://github.com/SpiralDevelopment/candlestick-patterns
    """

    def candleHammer(self):
        """A shooting star is a bearish candlestick with a long upper shadow, little or no lower shadow, and a small real body near the low of the day.
           A shooting star is a type of candlestick that forms when a security opens, advances significantly, but then closes the day near the open again.
           (green/clear hammer facing up)"""

        return ((self.df['high'] - self.df['low']) > 3 * (self.df['open'] - self.df['close'])) \
            & (((self.df['close'] - self.df['low']) / (.001 + self.df['high'] - self.df['low'])) > 0.6) \
            & (((self.df['open'] - self.df['low']) / (.001 + self.df['high'] - self.df['low'])) > 0.6)

    def addCandleHammer(self):
        self.df['hammer'] = self.candleHammer()

    def candleInvertedHammer(self):
        """The Inverted Hammer candlestick formation occurs mainly at the bottom of downtrends and can act as a warning of a potential bullish reversal 
           pattern. What happens on the next day after the Inverted Hammer pattern is what gives traders an idea as to whether or not prices will go 
           higher or lower. (green/clear hammer facing down)"""

        return (((self.df['high'] - self.df['low']) > 3 * (self.df['open'] - self.df['close'])) \
            & ((self.df['high'] - self.df['close']) / (.001 + self.df['high'] - self.df['low']) > 0.6) \
            & ((self.df['high'] - self.df['open']) / (.001 + self.df['high'] - self.df['low']) > 0.6))

    def addCandleInvertedHammer(self):
        self.df['inverted_hammer'] = self.candleInvertedHammer()

    def candleShootingStar(self):
        """The Shooting Star candlestick formation is viewed as a bearish reversal candlestick pattern that typically occurs at the top of uptrends. 
           (red/solid hammer facing down)"""

        return ((self.df['open'].shift(1) < self.df['close'].shift(1)) & (self.df['close'].shift(1) < self.df['open'])) \
            & (self.df['high'] - np.maximum(self.df['open'], self.df['close']) >= (abs(self.df['open'] - self.df['close']) * 3)) \
            & ((np.minimum(self.df['close'], self.df['open']) - self.df['low']) <= abs(self.df['open'] - self.df['close']))

    def addCandleShootingStar(self):
        self.df['shooting_star'] = self.candleShootingStar()

    def candleHangingMan(self):
        """The Hanging Man candlestick pattern, as one could predict from the name, is viewed as a bearish reversal pattern.
           This pattern occurs mainly at the top of uptrends and can act as a warning of a potential reversal downward. (red/solid hammer facing up)"""

        return ((self.df['high'] - self.df['low']) > (4 * (self.df['open'] - self.df['close']))) \
            & (((self.df['close'] - self.df['low']) / (.001 + self.df['high'] - self.df['low'])) >= 0.75) \
            & (((self.df['open'] - self.df['low']) / (.001 + self.df['high'] - self.df['low'])) >= 0.75) \
            & (self.df['high'].shift(1) < self.df['open']) \
            & (self.df['high'].shift(2) < self.df['open'])

    def addCandleHangingMan(self):
        self.df['hanging_man'] = self.candleHangingMan()

    def candleThreeWhiteSoldiers(self):
        """Three white soldiers is a bullish candlestick pattern that is used to predict the reversal of the current downtrend in a pricing chart.
           The pattern consists of three consecutive long-bodied candlesticks that open within the previous candle's real body and a close that exceeds 
           the previous candle's high."""

        return ((self.df['open'] > self.df['open'].shift(1)) & (self.df['open'] < self.df['close'].shift(1))) \
            & (self.df['close'] > self.df['high'].shift(1)) \
            & (self.df['high'] - np.maximum(self.df['open'], self.df['close']) < (abs(self.df['open'] - self.df['close']))) \
            & ((self.df['open'].shift(1) > self.df['open'].shift(2)) & (self.df['open'].shift(1) < self.df['close'].shift(2))) \
            & (self.df['close'].shift(1) > self.df['high'].shift(2)) \
            & (self.df['high'].shift(1) - np.maximum(self.df['open'].shift(1), self.df['close'].shift(1)) < (abs(self.df['open'].shift(1) - self.df['close'].shift(1))))

    def addCandleThreeWhiteSoldiers(self):
        self.df['three_white_solidiers'] = self.candleThreeWhiteSoldiers()

    def candleThreeBlackCrows(self):
        """Three black crows indicate a bearish candlestick pattern that predicts the reversal of an uptrend.
           Candlestick charts show the opening, high, low, and the closing price on a particular security. 
           For stocks moving higher the candlestick is white or green. When moving lower, they are black or red."""

        return ((self.df['open'] < self.df['open'].shift(1)) & (self.df['open'] > self.df['close'].shift(1))) \
            & (self.df['close'] < self.df['low'].shift(1)) \
            & (self.df['low'] - np.maximum(self.df['open'], self.df['close']) < (abs(self.df['open'] - self.df['close']))) \
            & ((self.df['open'].shift(1) < self.df['open'].shift(2)) & (self.df['open'].shift(1) > self.df['close'].shift(2))) \
            & (self.df['close'].shift(1) < self.df['low'].shift(2)) \
            & (self.df['low'].shift(1) - np.maximum(self.df['open'].shift(1), self.df['close'].shift(1)) < (abs(self.df['open'].shift(1) - self.df['close'].shift(1))))

    def addCandleThreeBlackCrows(self):
        self.df['three_black_crows'] = self.candleThreeBlackCrows()

    def candleDojo(self):
        """The Doji is a transitional candlestick formation, signifying equality and/or indecision between bulls and bears.
           A Doji is quite often found at the bottom and top of trends and thus is considered as a sign of possible reversal of price direction, 
           but the Doji can be viewed as a continuation pattern as well."""

        return ((abs(self.df['close'] - self.df['open']) / (self.df['high'] - self.df['low'])) < 0.1) \
            & ((self.df['high'] - np.maximum(self.df['close'], self.df['open'])) > (3 * abs(self.df['close'] - self.df['open']))) \
            & ((np.minimum(self.df['close'], self.df['open']) - self.df['low']) > (3 * abs(self.df['close'] - self.df['open'])))

    def addCandleDojo(self):
        self.df['dojo'] = self.candleDojo()

    def candleThreeLineStrike(self):
        """The bullish three line strike reversal pattern carves out three black candles within a downtrend. Each bar posts a lower low and closes 
            near the intrabar low. The fourth bar opens even lower but reverses in a wide-range outside bar that closes above the high of the first 
            candle in the series."""

        return ((self.df['open'].shift(1) < self.df['open'].shift(2)) & (self.df['open'].shift(1) > self.df['close'].shift(2))) \
            & (self.df['close'].shift(1) < self.df['low'].shift(2)) \
            & (self.df['low'].shift(1) - np.maximum(self.df['open'].shift(1), self.df['close'].shift(1)) < (abs(self.df['open'].shift(1) - self.df['close'].shift(1)))) \
            & ((self.df['open'].shift(2) < self.df['open'].shift(3)) & (self.df['open'].shift(2) > self.df['close'].shift(3))) \
            & (self.df['close'].shift(2) < self.df['low'].shift(3)) \
            & (self.df['low'].shift(2) - np.maximum(self.df['open'].shift(2), self.df['close'].shift(2)) < (abs(self.df['open'].shift(2) - self.df['close'].shift(2)))) \
            & ((self.df['open'] < self.df['low'].shift(1)) & (self.df['close'] > self.df['high'].shift(3)))

    def addCandleThreeLineStrike(self):
        self.df['three_line_strike'] = self.candleThreeLineStrike()

    def candleTwoBlackGapping(self):
        """The bearish two black gapping continuation pattern appears after a notable top in an uptrend, with a gap down that yields two black bars 
           posting lower lows. This pattern predicts that the decline will continue to even lower lows, perhaps triggering a broader-scale downtrend."""

        return ((self.df['open'] < self.df['open'].shift(1)) & (self.df['open'] > self.df['close'].shift(1))) \
            & (self.df['close'] < self.df['low'].shift(1)) \
            & (self.df['low'] - np.maximum(self.df['open'], self.df['close']) < (abs(self.df['open'] - self.df['close']))) \
            & (self.df['high'].shift(1) < self.df['low'].shift(2))

    def addCandleTwoBlackGapping(self):
        self.df['two_black_gapping'] = self.candleTwoBlackGapping()

    def candleEveningStar(self):
        """The bearish evening star reversal pattern starts with a tall white bar that carries an uptrend to a new high. The market gaps higher on
           the next bar, but fresh buyers fail to appear, yielding a narrow range candlestick. A gap down on the third bar completes the pattern,
           which predicts that the decline will continue to even lower lows, perhaps triggering a broader-scale downtrend."""

        return ((np.minimum(self.df['open'].shift(1), self.df['close'].shift(1)) > self.df['close'].shift(2)) & (self.df['close'].shift(2) > self.df['open'].shift(2))) \
            & ((self.df['close'] < self.df['open']) & (self.df['open'] < np.minimum(self.df['open'].shift(1), self.df['close'].shift(1))))

    def addCandleEveningStar(self):
        self.df['evening_star'] = self.candleEveningStar()

    def candleAbandonedBaby(self):
        """The bullish abandoned baby reversal pattern appears at the low of a downtrend, after a series of black candles print lower lows. The
           market gaps lower on the next bar, but fresh sellers fail to appear, yielding a narrow range doji candlestick with opening and closing
           prints at the same price. A bullish gap on the third bar completes the pattern, which predicts that the recovery will continue to even 
           higher highs, perhaps triggering a broader-scale uptrend."""

        return (self.df['open'] < self.df['close']) \
            & (self.df['high'].shift(1) < self.df['low']) \
            & (self.df['open'].shift(2) > self.df['close'].shift(2)) \
            & (self.df['high'].shift(1) < self.df['low'].shift(2))

    def addCandleAbandonedBaby(self):
        self.df['abandoned_baby'] = self.candleAbandonedBaby()

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

        return np.where(self.df['close'] == self.df['close'].shift(1), 0, np.where(self.df['close'] > self.df['close'].shift(1), self.df['volume'], 
        np.where(self.df['close'] < self.df['close'].shift(1), -self.df['volume'], self.df.iloc[0]['volume']))).cumsum()

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