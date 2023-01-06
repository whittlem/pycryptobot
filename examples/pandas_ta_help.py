import sys

sys.path.insert(0, ".")

import pandas as pd  # noqa: E402
import pandas_ta as ta  # noqa: E402

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402

app = PyCryptoBot()
df = app.get_historical_data(app.market, app.granularity, None)

# help(ta)
# help(ta.eri)
# help(ta.bbands)

bbands20 = df.ta.bbands(length=20, std=2, mamode="sma", fillna=df.close)
print(bbands20)

sys.exit()

# List Indicators
df.ta.indicators()

rsi = ta.rsi(df["close"], length=14, fillna=50)
print(rsi)

df.ta.rsi(length=14, append=True, fillna=50)

df.ta.ema(length=12, append=True, fillna=df.close)
df.ta.ema(length=26, append=True, fillna=df.close)

df["ema12"] = ta.ema(df["close"], length=12, fillna=df.close)
df["ema26"] = ta.ema(df["close"], length=12, fillna=df.close)

sma10 = df.ta.sma(10, fillna=df.close)
sma50 = df.ta.sma(50, fillna=df.close)
sma100 = df.ta.sma(100, fillna=df.close)
df = pd.concat([df, sma10, sma50, sma100], axis=1)

df.ta.cdl_pattern(name="doji", append=True)
# df.ta.donchian(lower_length=10, upper_length=15, append=True)

# print(self.df)
# print(self.df.shift())

print(df.columns)
print(df.head())
# print(rsi)
