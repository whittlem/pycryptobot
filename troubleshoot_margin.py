import sys

sys.path.append('.')
from models.helper.MarginHelper import calculate_margin

buy_filled = 1.13463691
buy_price = 138.52
buy_size = 160.37000000
buy_fee = 0.55

sell_percent = 100

sell_filled = 1.13460000
sell_price = 138.97
sell_size = 1.13460000
sell_taker_fee = 0.55
sell_fee = 0.0

actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee, sell_percent, sell_price, sell_fee, sell_taker_fee, True)