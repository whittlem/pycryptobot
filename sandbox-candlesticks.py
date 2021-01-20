import numpy as np
from models.CoinbasePro import CoinbasePro

coinbasepro = CoinbasePro('BTC-GBP', 3600)
df = coinbasepro.getDataFrame()

# buy signal: green/clear hammer facing down
df['inverted_hammer'] = (((df['high'] - df['low']) > 3 * (df['open'] - df['close'])) \
    & ((df['high'] - df['close']) / (.001 + df['high'] - df['low']) > 0.6) \
    & ((df['high'] - df['open']) / (.001 + df['high'] - df['low']) > 0.6))

# sell signal: green/clear hammer facing up
df['hammer'] = ((df['high'] - df['low']) > 3 * (df['open'] - df['close'])) \
    & (((df['close'] - df['low']) / (.001 + df['high'] - df['low'])) > 0.6) \
    & (((df['open'] - df['low']) / (.001 + df['high'] - df['low'])) > 0.6)

# buy signal: red/solid hammer facing down
df['shooting_star'] = ((df['open'].shift(1) < df['close'].shift(1)) & (df['close'].shift(1) < df['open'])) \
    & (df['high'] - np.maximum(df['open'], df['close']) >= (abs(df['open'] - df['close']) * 3)) \
    & ((np.minimum(df['close'], df['open']) - df['low']) <= abs(df['open'] - df['close']))

# sell signal: red/solid hammer facing up
df['hanging_man'] = ((df['high'] - df['low']) > (4 * (df['open'] - df['close']))) \
    & (((df['close'] - df['low']) / (.001 + df['high'] - df['low'])) >= 0.75) \
    & (((df['open'] - df['low']) / (.001 + df['high'] - df['low'])) >= 0.75) \
    & (df['high'].shift(1) < df['open']) \
    & (df['high'].shift(2) < df['open'])

# buy signal: three positive candles (price reversal)
df['three_white_solidiers'] = ((df['open'] > df['open'].shift(1)) & (df['open'] < df['close'].shift(1))) \
    & (df['close'] > df['high'].shift(1)) \
    & (df['high'] - np.maximum(df['open'], df['close']) < (abs(df['open'] - df['close']))) \
    & ((df['open'].shift(1) > df['open'].shift(2)) & (df['open'].shift(1) < df['close'].shift(2))) \
    & (df['close'].shift(1) > df['high'].shift(2)) \
    & (df['high'].shift(1) - np.maximum(df['open'].shift(1), df['close'].shift(1)) < (abs(df['open'].shift(1) - df['close'].shift(1))))

# sell signal: three negative candles (price reversal)
df['three_black_crows'] = ((df['open'] < df['open'].shift(1)) & (df['open'] > df['close'].shift(1))) \
    & (df['close'] < df['low'].shift(1)) \
    & (df['low'] - np.maximum(df['open'], df['close']) < (abs(df['open'] - df['close']))) \
    & ((df['open'].shift(1) < df['open'].shift(2)) & (df['open'].shift(1) > df['close'].shift(2))) \
    & (df['close'].shift(1) < df['low'].shift(2)) \
    & (df['low'].shift(1) - np.maximum(df['open'].shift(1), df['close'].shift(1)) < (abs(df['open'].shift(1) - df['close'].shift(1)))) \
 
#print (df[df['hammer'] == True])
#print (df[df['inverted_hammer'] == True])
#print (df[df['shooting_star'] == True])
#print (df[df['hanging_man'] == True])
#print (df[df['three_white_solidiers'] == True])
print (df[df['three_black_crows'] == True])
#print (df)