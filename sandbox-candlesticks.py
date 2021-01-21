import numpy as np
from models.CoinbasePro import CoinbasePro

coinbasepro = CoinbasePro('BTC-GBP', 3600)
df = coinbasepro.getDataFrame()

"""References
https://commodity.com/technical-analysis
https://www.investopedia.com
https://github.com/SpiralDevelopment/candlestick-patterns
"""

# The Inverted Hammer candlestick formation occurs mainly at the bottom of downtrends and can act as a warning of a potential bullish reversal 
# pattern. What happens on the next day after the Inverted Hammer pattern is what gives traders an idea as to whether or not prices will go 
# higher or lower. (green/clear hammer facing down)
df['inverted_hammer'] = (((df['high'] - df['low']) > 3 * (df['open'] - df['close'])) \
    & ((df['high'] - df['close']) / (.001 + df['high'] - df['low']) > 0.6) \
    & ((df['high'] - df['open']) / (.001 + df['high'] - df['low']) > 0.6))

# A shooting star is a bearish candlestick with a long upper shadow, little or no lower shadow, and a small real body near the low of the day.
# A shooting star is a type of candlestick that forms when a security opens, advances significantly, but then closes the day near the open again.
# (green/clear hammer facing up)
df['hammer'] = ((df['high'] - df['low']) > 3 * (df['open'] - df['close'])) \
    & (((df['close'] - df['low']) / (.001 + df['high'] - df['low'])) > 0.6) \
    & (((df['open'] - df['low']) / (.001 + df['high'] - df['low'])) > 0.6)

# The Shooting Star candlestick formation is viewed as a bearish reversal candlestick pattern that typically occurs at the top of uptrends. 
# (red/solid hammer facing down)
df['shooting_star'] = ((df['open'].shift(1) < df['close'].shift(1)) & (df['close'].shift(1) < df['open'])) \
    & (df['high'] - np.maximum(df['open'], df['close']) >= (abs(df['open'] - df['close']) * 3)) \
    & ((np.minimum(df['close'], df['open']) - df['low']) <= abs(df['open'] - df['close']))

# The Hanging Man candlestick pattern, as one could predict from the name, is viewed as a bearish reversal pattern.
# This pattern occurs mainly at the top of uptrends and can act as a warning of a potential reversal downward. (red/solid hammer facing up)
df['hanging_man'] = ((df['high'] - df['low']) > (4 * (df['open'] - df['close']))) \
    & (((df['close'] - df['low']) / (.001 + df['high'] - df['low'])) >= 0.75) \
    & (((df['open'] - df['low']) / (.001 + df['high'] - df['low'])) >= 0.75) \
    & (df['high'].shift(1) < df['open']) \
    & (df['high'].shift(2) < df['open'])

# Three white soldiers is a bullish candlestick pattern that is used to predict the reversal of the current downtrend in a pricing chart.
# The pattern consists of three consecutive long-bodied candlesticks that open within the previous candle's real body and a close that exceeds 
# the previous candle's high.
df['three_white_solidiers'] = ((df['open'] > df['open'].shift(1)) & (df['open'] < df['close'].shift(1))) \
    & (df['close'] > df['high'].shift(1)) \
    & (df['high'] - np.maximum(df['open'], df['close']) < (abs(df['open'] - df['close']))) \
    & ((df['open'].shift(1) > df['open'].shift(2)) & (df['open'].shift(1) < df['close'].shift(2))) \
    & (df['close'].shift(1) > df['high'].shift(2)) \
    & (df['high'].shift(1) - np.maximum(df['open'].shift(1), df['close'].shift(1)) < (abs(df['open'].shift(1) - df['close'].shift(1))))

# Three black crows indicate a bearish candlestick pattern that predicts the reversal of an uptrend.
# Candlestick charts show the opening, high, low, and the closing price on a particular security. 
# For stocks moving higher the candlestick is white or green. When moving lower, they are black or red.
df['three_black_crows'] = ((df['open'] < df['open'].shift(1)) & (df['open'] > df['close'].shift(1))) \
    & (df['close'] < df['low'].shift(1)) \
    & (df['low'] - np.maximum(df['open'], df['close']) < (abs(df['open'] - df['close']))) \
    & ((df['open'].shift(1) < df['open'].shift(2)) & (df['open'].shift(1) > df['close'].shift(2))) \
    & (df['close'].shift(1) < df['low'].shift(2)) \
    & (df['low'].shift(1) - np.maximum(df['open'].shift(1), df['close'].shift(1)) < (abs(df['open'].shift(1) - df['close'].shift(1)))) \

# The Doji is a transitional candlestick formation, signifying equality and/or indecision between bulls and bears.
# A Doji is quite often found at the bottom and top of trends and thus is considered as a sign of possible reversal of price direction, 
# but the Doji can be viewed as a continuation pattern as well.
df['dojo'] = ((abs(df['close'] - df['open']) / (df['high'] - df['low'])) < 0.1) \
    & ((df['high'] - np.maximum(df['close'], df['open'])) > (3 * abs(df['close'] - df['open']))) \
    & ((np.minimum(df['close'], df['open']) - df['low']) > (3 * abs(df['close'] - df['open'])))

#print (df[df['hammer'] == True])
#print (df[df['inverted_hammer'] == True])
#print (df[df['shooting_star'] == True])
#print (df[df['hanging_man'] == True])
#print (df[df['three_white_solidiers'] == True])
#print (df[df['three_black_crows'] == True])
#print (df[df['dojo'] == True])
print (df)