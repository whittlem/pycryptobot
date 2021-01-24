import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from models.CoinbasePro import CoinbasePro

market = 'BTC-GBP'
granularity = 3600

coinbasepro = CoinbasePro(market, granularity)
df = coinbasepro.getDataFrame()
coinbasepro.addMovingAverages()
coinbasepro.addMomentumIndicators()

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
    & (df['low'].shift(1) - np.maximum(df['open'].shift(1), df['close'].shift(1)) < (abs(df['open'].shift(1) - df['close'].shift(1))))

# The Doji is a transitional candlestick formation, signifying equality and/or indecision between bulls and bears.
# A Doji is quite often found at the bottom and top of trends and thus is considered as a sign of possible reversal of price direction, 
# but the Doji can be viewed as a continuation pattern as well.
df['dojo'] = ((abs(df['close'] - df['open']) / (df['high'] - df['low'])) < 0.1) \
    & ((df['high'] - np.maximum(df['close'], df['open'])) > (3 * abs(df['close'] - df['open']))) \
    & ((np.minimum(df['close'], df['open']) - df['low']) > (3 * abs(df['close'] - df['open'])))

# The bullish three line strike reversal pattern carves out three black candles within a downtrend. Each bar posts a lower low and closes 
# near the intrabar low. The fourth bar opens even lower but reverses in a wide-range outside bar that closes above the high of the first 
# candle in the series.
df['three_line_strike'] = ((df['open'].shift(1) < df['open'].shift(2)) & (df['open'].shift(1) > df['close'].shift(2))) \
    & (df['close'].shift(1) < df['low'].shift(2)) \
    & (df['low'].shift(1) - np.maximum(df['open'].shift(1), df['close'].shift(1)) < (abs(df['open'].shift(1) - df['close'].shift(1)))) \
    & ((df['open'].shift(2) < df['open'].shift(3)) & (df['open'].shift(2) > df['close'].shift(3))) \
    & (df['close'].shift(2) < df['low'].shift(3)) \
    & (df['low'].shift(2) - np.maximum(df['open'].shift(2), df['close'].shift(2)) < (abs(df['open'].shift(2) - df['close'].shift(2)))) \
    & ((df['open'] < df['low'].shift(1)) & (df['close'] > df['high'].shift(3)))

# The bearish two black gapping continuation pattern appears after a notable top in an uptrend, with a gap down that yields two black bars 
# posting lower lows. This pattern predicts that the decline will continue to even lower lows, perhaps triggering a broader-scale downtrend. 
df['two_black_gapping'] = ((df['open'] < df['open'].shift(1)) & (df['open'] > df['close'].shift(1))) \
    & (df['close'] < df['low'].shift(1)) \
    & (df['low'] - np.maximum(df['open'], df['close']) < (abs(df['open'] - df['close']))) \
    & (df['high'].shift(1) < df['low'].shift(2))

# The bearish evening star reversal pattern starts with a tall white bar that carries an uptrend to a new high. The market gaps higher on
# the next bar, but fresh buyers fail to appear, yielding a narrow range candlestick. A gap down on the third bar completes the pattern,
# which predicts that the decline will continue to even lower lows, perhaps triggering a broader-scale downtrend. 
df['evening_star'] = ((np.minimum(df['open'].shift(1), df['close'].shift(1)) > df['close'].shift(2)) & (df['close'].shift(2) > df['open'].shift(2))) \
    & ((df['close'] < df['open']) & (df['open'] < np.minimum(df['open'].shift(1), df['close'].shift(1))))

# The bullish abandoned baby reversal pattern appears at the low of a downtrend, after a series of black candles print lower lows. The
# market gaps lower on the next bar, but fresh sellers fail to appear, yielding a narrow range doji candlestick with opening and closing 
# prints at the same price. A bullish gap on the third bar completes the pattern, which predicts that the recovery will continue to even 
# higher highs, perhaps triggering a broader-scale uptrend.
df['abandoned_baby'] = (df['open'] < df['close']) \
    & (df['high'].shift(1) < df['low']) \
    & (df['open'].shift(2) > df['close'].shift(2)) \
    & (df['high'].shift(1) < df['low'].shift(2))

#print (df[df['hammer'] == True])
#print (df[df['inverted_hammer'] == True])
#print (df[df['shooting_star'] == True])
#print (df[df['hanging_man'] == True])
#print (df[df['three_white_solidiers'] == True])
#print (df[df['three_black_crows'] == True])
#print (df[df['dojo'] == True])
#print (df[df['three_line_strike'] == True])
#print (df[df['two_black_gapping'] == True])
#print (df[df['evening_star'] == True])
#print (df[df['abandoned_baby'] == True])
#print (df)

lastDays = 24
df_subset = df.iloc[-lastDays::]

date = df_subset.index.date.astype('O')

def format_date(x, pos=None):
    thisind = np.clip(int(x + 0.5), 0, len(df_subset) - 1)
    return date[thisind].strftime('%Y-%m-%d %H:%M:%S')

fig, axes = plt.subplots(ncols=1, figsize=(12, 6))
fig.autofmt_xdate()
ax1 = plt.subplot(111)
ax1.set_title(f"{market} - {granularity} granularity")
ax1.xaxis.set_major_formatter(ticker.FuncFormatter(format_date))
plt.style.use('seaborn')
plt.plot(df_subset['close'], label='price', color='royalblue')
plt.plot(df_subset['ema12'], label='ema12', color='orange')
plt.plot(df_subset['ema26'], label='ema26', color='purple')

df_candlestick = df[df['three_white_solidiers'] == True]
df_candlestick_in_range = df_candlestick[df_candlestick.index >= np.min(df_subset.index)]
for idx in df_candlestick_in_range.index.tolist():
    plt.plot(idx, df_candlestick_in_range.loc[idx]['close'], 'gx')

df_candlestick = df[df['three_black_crows'] == True]
df_candlestick_in_range = df_candlestick[df_candlestick.index >= np.min(df_subset.index)]
for idx in df_candlestick_in_range.index.tolist():
    plt.plot(idx, df_candlestick_in_range.loc[idx]['close'], 'rx')  

df_candlestick = df[df['inverted_hammer'] == True]
df_candlestick_in_range = df_candlestick[df_candlestick.index >= np.min(df_subset.index)]
for idx in df_candlestick_in_range.index.tolist():
    plt.plot(idx, df_candlestick_in_range.loc[idx]['close'], 'g^') 

df_candlestick = df[df['hammer'] == True]
df_candlestick_in_range = df_candlestick[df_candlestick.index >= np.min(df_subset.index)]
for idx in df_candlestick_in_range.index.tolist():
    plt.plot(idx, df_candlestick_in_range.loc[idx]['close'], 'rv')

df_candlestick = df[df['hanging_man'] == True]
df_candlestick_in_range = df_candlestick[df_candlestick.index >= np.min(df_subset.index)]
for idx in df_candlestick_in_range.index.tolist():
    plt.plot(idx, df_candlestick_in_range.loc[idx]['close'], 'go') 

df_candlestick = df[df['shooting_star'] == True]
df_candlestick_in_range = df_candlestick[df_candlestick.index >= np.min(df_subset.index)]
for idx in df_candlestick_in_range.index.tolist():
    plt.plot(idx, df_candlestick_in_range.loc[idx]['close'], 'r*')  

df_candlestick = df[df['dojo'] == True]
df_candlestick_in_range = df_candlestick[df_candlestick.index >= np.min(df_subset.index)]
for idx in df_candlestick_in_range.index.tolist():
    plt.plot(idx, df_candlestick_in_range.loc[idx]['close'], 'yd')  

df_candlestick = df[df['three_line_strike'] == True]
df_candlestick_in_range = df_candlestick[df_candlestick.index >= np.min(df_subset.index)]
for idx in df_candlestick_in_range.index.tolist():
    plt.plot(idx, df_candlestick_in_range.loc[idx]['close'], 'y^')  

df_candlestick = df[df['two_black_gapping'] == True]
df_candlestick_in_range = df_candlestick[df_candlestick.index >= np.min(df_subset.index)]
for idx in df_candlestick_in_range.index.tolist():
    plt.plot(idx, df_candlestick_in_range.loc[idx]['close'], 'yv')  

df_candlestick = df[df['evening_star'] == True]
df_candlestick_in_range = df_candlestick[df_candlestick.index >= np.min(df_subset.index)]
for idx in df_candlestick_in_range.index.tolist():
    plt.plot(idx, df_candlestick_in_range.loc[idx]['close'], 'mv')  

df_candlestick = df[df['abandoned_baby'] == True]
df_candlestick_in_range = df_candlestick[df_candlestick.index >= np.min(df_subset.index)]
for idx in df_candlestick_in_range.index.tolist():
    plt.plot(idx, df_candlestick_in_range.loc[idx]['close'], 'm^')  

plt.ylabel('Price')
plt.xticks(rotation=90)
plt.tight_layout()
plt.legend()
#plt.savefig('candlesticks.png')
plt.show()