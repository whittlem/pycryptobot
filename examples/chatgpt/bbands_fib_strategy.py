""" Idea from chatgpt implemented using PyCryptoBot """

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.exchange.ExchangesEnum import Exchange  # noqa: E402
from models.exchange.Granularity import Granularity  # noqa: E402
from models.Trading import TechnicalAnalysis  # noqa: E402

app = PyCryptoBot(exchange=Exchange.BINANCE)
app.market = "ADAUSDT"

# Load the data
# data = pd.read_csv("data.csv")
data = app.get_historical_data(app.market, app.granularity, None)

# Calculate the moving average
ma = data["close"].rolling(window=20).mean()

# Calculate the upper and lower Bollinger Bands
std = data["close"].rolling(window=20).std()
upper_band = ma + 2 * std
lower_band = ma - 2 * std

# Calculate the Fibonacci retracement levels
high = data["high"].max()
low = data["low"].min()
fibonacci_levels = [0.618, 0.786, 1.0]
fib_levels = [low + (high - low) * x for x in fibonacci_levels]

# Create the plot
plt.figure(figsize=(12, 6))
plt.subplot(111)
plt.suptitle(
    data.iloc[0]["market"] + " | " + str(data.iloc[0]["granularity"]),
    fontsize=12,
)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%Y"))
plt.gca().xaxis.set_major_locator(mdates.DayLocator())

plt.plot(data["date"], data["close"], label="Close")
plt.plot(ma, label="Moving Average")
plt.plot(upper_band, label="Upper Band")
plt.plot(lower_band, label="Lower Band")
plt.gcf().autofmt_xdate()
for level in fib_levels:
    plt.axhline(y=level, linestyle="--", alpha=0.5)
plt.legend(loc="upper left")
plt.ylabel("Price")
plt.xticks(rotation=90)
plt.tight_layout()
plt.show()
# plt.savefig("bbands_fib_strategy.png")


# Implement the trading strategy
def trade(data):
    buy_signals = []
    sell_signals = []
    for i in range(1, len(data)):
        if data["close"][i] > upper_band[i] and data["close"][i - 1] < upper_band[i - 1]:
            buy_signals.append(i)
        elif data["close"][i] < lower_band[i] and data["close"][i - 1] > lower_band[i - 1]:
            sell_signals.append(i)
    return buy_signals, sell_signals


buy_signals, sell_signals = trade(data)
print(f"Buy signals: {buy_signals}")
print(f"Sell signals: {sell_signals}")
