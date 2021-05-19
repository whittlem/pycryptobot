import sys

sys.path.append('.')
from models.helper.MarginHelper import calculate_margin


def test_margin_binance():
    # using VET-GBP
    buy_fee = 0.07434422700000001
    buy_filled = 74.344227
    buy_price = 0.1249
    buy_size = 595.23
    debug = True
    exchange = 'binance'
    sell_fee = 0.0
    sell_percent = 100
    sell_price = 0.1335
    sell_taker_fee = 0.001

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee,
                                                                     debug, exchange)

    assert actual_margin == 6.78
    assert actual_profit == 5.04
    assert actual_sell_fee == 0.07946321


def test_margin_coinbase_pro():
    # using LINK-GBP
    buy_fee = 1.080713753
    buy_filled = 8.95
    buy_price = 34.50004
    buy_size = 310.11
    debug = True
    exchange = 'coinbasepro'
    sell_fee = 0.0
    sell_percent = 100
    sell_price = 30.66693
    sell_taker_fee = 0.0035

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee,
                                                                     debug, exchange)

    assert actual_margin == -11.8
    assert actual_profit == -36.6
    assert actual_sell_fee == 0.96064158
