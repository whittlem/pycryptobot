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


def test_calculate_negative_margin_on_binance_when_coin_price_over_1():
    # this test using BNB-USDT as market
    buy_size = 0.067
    buy_fee = 0.000067 # round(buy_size * 0.001, 8)
    buy_price = 667.26
    buy_filled = 44.70642 # round(buy_size * buy_price, 8)
    debug = True
    sell_percent = 100
    sell_price = 590.34
    sell_size = 39.55278 # round((sell_percent / 100) * (sell_price * buy_size), 8)
    sell_taker_fee = 0.001
    sell_filled = 39.51322722 # round((sell_size - (sell_size * sell_taker_fee)), 8)
    sell_fee = 0.0
    exchange = 'binance'

    expected_sell_fee = 0.03955278 # round(sell_size * sell_taker_fee, 8)
    expected_profit = -5.19 # round(sell_filled - buy_filled, 2)
    expected_margin = -11.61 # round((expected_profit / buy_filled) * 100, 2)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee,
                                                                     debug, exchange)

    assert round(actual_margin, 2) == round(expected_margin, 2)
    assert round(actual_profit, 2) == round(expected_profit, 2)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)


def test_calculate_negative_margin_on_binance_when_coin_price_over_1_2():
    buy_size = 0.24944
    buy_fee = 0.00024944 # round(buy_size * 0.001, 8)
    buy_price = 385.4
    buy_filled = 96.134176 # round(buy_size * buy_price, 8)
    debug = False
    sell_percent = 100
    sell_price = 320.95
    sell_size = 80.057768 # round((sell_percent / 100) * (sell_price * buy_size), 8)
    sell_taker_fee = 0.001
    sell_filled = 79.97771023 # round((sell_size - (sell_size * sell_taker_fee)), 8)
    sell_fee = 0.0
    exchange = 'binance'

    expected_sell_fee = 0.08005777 # round(sell_size * sell_taker_fee, 8)
    expected_profit = -16.16 # round(sell_filled - buy_filled, 2)
    expected_margin = -16.81 # round((expected_profit / buy_filled) * 100, 2)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee,
                                                                     debug, exchange)

    assert round(actual_margin, 2) == round(expected_margin, 2)
    assert round(actual_profit, 2) == round(expected_profit, 2)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)

def test_calculate_negative_margin_on_binance_when_coin_price_under_1():
    # this test is using CHZ-USDT as market
    
    buy_size = 177.2
    buy_fee = 0.1772 # round(buy_size * 0.001, 8)
    buy_price = 0.4968600000000001
    buy_filled = 88.043592 # round(buy_size * buy_price, 8)
    debug = True
    sell_percent = 100
    sell_price = 0.43913 
    sell_size = 77.813836 # round((sell_percent / 100) * (sell_price * buy_size), 8)
    sell_taker_fee = 0.001
    sell_filled = 77.73602216  # round((sell_size - (sell_size * sell_taker_fee)), 8) 
    sell_fee = 0.0
    exchange = 'binance'

    expected_sell_fee = 0.07781384 # round(sell_size * sell_taker_fee, 8)
    expected_profit = -10.31 # round(sell_filled - buy_filled, 2)
    expected_margin = -11.71 # round((expected_profit / buy_filled) * 100, 2)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee,
                                                                     debug, exchange)

    assert round(actual_margin, 2) == round(expected_margin, 2)
    assert round(actual_profit, 2) == round(expected_profit, 2)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)
