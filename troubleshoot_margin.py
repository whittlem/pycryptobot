import sys

sys.path.append('.')
from models.helper.MarginHelper import calculate_margin

# Scenario 1.1: Coinbase Pro passing in actual free in quote currency

buy_size = 1500
buy_fee = 2.99
buy_filled = 5.98802395
buy_price = 250.00

sell_percent = 100

sell_size = 5.98800000
sell_filled = 5.98800000
sell_price = 250.69
sell_fee = 3.00
sell_taker_fee_rate = 0 # not used if sell_fee is set

actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee, sell_percent, sell_price, sell_fee, sell_taker_fee_rate, True)

print ("---\n")

# Scenario 1.2: Coinbase Pro passing in actual free in quote currency

buy_size = 157.72000000
buy_fee = 0.55
buy_filled = 1.13463691
buy_price = 138.52

sell_percent = 100

sell_filled = 1.13460000
sell_price = 138.97
sell_size = 1.13460000
sell_taker_fee_rate_rate = 0 # not used if sell_taker_fee_rate is supplied, which is the fee rate
sell_fee = 0.55

actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee, sell_percent, sell_price, sell_fee, sell_taker_fee_rate, True)

print ("---\n")

# Scenario 2.1: Coinbase Pro passing in exchange fee rate

buy_size = 1500
buy_fee = 2.99
buy_filled = 5.98802395
buy_price = 250.00

sell_percent = 100

sell_size = 5.98800000
sell_filled = 5.98800000
sell_price = 250.69
sell_fee = 0 # not used if sell_taker_fee_rate is supplied, which is the fee rate
sell_taker_fee_rate = 0.002

actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee, sell_percent, sell_price, sell_fee, sell_taker_fee_rate, True)

print ("---\n")