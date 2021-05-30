import sys

sys.path.append('.')
from models.helper.MarginHelper import calculate_margin
from models.helper.LogHelper import Logger
Logger.configure()


def test_margin_binance():
    # using VET-GBP
    buy_filled= 595.23
    buy_price = 0.1249
    buy_size = 74.344227 # round(buy_filled * buy_price, 8)
    buy_fee = 0.07434423  # round(buy_size * 0.001, 8)
    sell_percent = 100
    sell_price = 0.1335
    sell_size = 79.463205 # round((sell_percent / 100) * (sell_price * buy_filled), 8)
    sell_taker_fee = 0.001
    sell_filled = 79.38374179 # round((sell_size - round(sell_size * sell_taker_fee, 8)), 8)
    sell_fee = 0.0

    expected_sell_fee = 0.07946321 # round(sell_size * sell_taker_fee, 8)
    expected_profit = 5.03951479 # round(sell_filled - buy_size, 8)
    expected_margin = 6.77862289 # round((expected_profit / buy_size) * 100, 8)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee)

    assert round(actual_margin, 8) == round(expected_margin, 8)
    assert round(actual_profit, 8) == round(expected_profit, 8)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)


def test_margin_coinbase_pro():
    # using LINK-GBP
    buy_filled = 8.95
    buy_price = 34.50004
    buy_size = 308.775358 # round(buy_filled * buy_price, 8)
    buy_fee = 1.54387679 # round(buy_size * 0.005, 8)
    sell_percent = 100
    sell_price = 30.66693
    sell_size = 274.4690235 # round((sell_percent / 100) * (sell_price * buy_filled), 8)
    sell_taker_fee = 0.0035
    sell_filled = 273.50838192 # round((sell_size - round(sell_size * sell_taker_fee, 8)), 8)
    sell_fee = 0.0
    
    expected_sell_fee = 0.96064158 # round(sell_size * sell_taker_fee, 8)
    expected_profit = -35.26697608 # round(sell_filled - buy_size, 8)
    expected_margin = -11.42156431 # round((expected_profit / buy_size) * 100, 8)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee)

    assert round(actual_margin, 8) == round(expected_margin, 8)
    assert round(actual_profit, 8) == round(expected_profit, 8)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)


def test_calculate_negative_margin_on_binance_when_coin_price_over_1():
    # this test using BNB-USDT as market
    buy_filled = 0.067
    buy_price = 667.26
    buy_size  = 44.70642 # round(buy_filled * buy_price, 8)
    buy_fee = 0.04470642 # round(buy_size * 0.001, 8)
    sell_percent = 100
    sell_price = 590.34
    sell_size = 39.55278 # round((sell_percent / 100) * (sell_price * buy_filled), 8)
    sell_taker_fee = 0.001
    sell_filled = 39.51322722 # round((sell_size - round(sell_size * sell_taker_fee, 8)), 8)
    sell_fee = 0.0

    expected_sell_fee = 0.03955278 # round(sell_size * sell_taker_fee, 8)
    expected_profit = -5.19319278 # round(sell_filled - buy_size, 8)
    expected_margin = -11.61621257 # round((expected_profit / buy_size) * 100, 8)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee)

    assert round(actual_margin, 8) == round(expected_margin, 8)
    assert round(actual_profit, 8) == round(expected_profit, 8)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)


def test_calculate_negative_margin_on_binance_when_coin_price_over_1_2():
    buy_filled = 0.24944
    buy_price = 385.4
    buy_size = 96.134176 # round(buy_filled * buy_price, 8)
    buy_fee = 0.09613418 # round(buy_size * 0.001, 8)
    sell_percent = 100
    sell_price = 320.95
    sell_size = 80.057768 # round((sell_percent / 100) * (sell_price * buy_filled), 8)
    sell_taker_fee = 0.001
    sell_filled = 79.97771023 # round((sell_size - round(sell_size * sell_taker_fee, 8)), 8)
    sell_fee = 0.0

    expected_sell_fee = 0.08005777 # round(sell_size * sell_taker_fee, 8)
    expected_profit = -16.15646577 # round(sell_filled - buy_size, 8)
    expected_margin = -16.80616243 # round((expected_profit / buy_size) * 100, 8)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee)

    assert round(actual_margin, 8) == round(expected_margin, 8)
    assert round(actual_profit, 8) == round(expected_profit, 8)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)

def test_calculate_negative_margin_on_binance_when_coin_price_under_1():
    # this test is using CHZ-USDT as market
    
    buy_filled = 177.2
    buy_price = 0.4968600000000001
    buy_size = 88.043592 # round(buy_filled * buy_price, 8)
    buy_fee = 0.1772 # buy_filled(buy_size * 0.001, 8)
    sell_percent = 100
    sell_price = 0.43913 
    sell_size = 77.813836 # round((sell_percent / 100) * (sell_price * buy_filled), 8)
    sell_taker_fee = 0.001
    sell_filled = 77.73602216  # round((sell_size - round(sell_size * sell_taker_fee, 8)), 8)
    sell_fee = 0.0

    expected_sell_fee = 0.07781384 # round(sell_size * sell_taker_fee, 8)
    expected_profit = -10.30756984 # round(sell_filled - buy_size, 8)
    expected_margin = -11.70734815 # round((expected_profit / buy_size) * 100, 8)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee)

    assert round(actual_margin, 8) == round(expected_margin, 8)
    assert round(actual_profit, 8) == round(expected_profit, 8)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)

    
def test_binance_microtrading_1():
    # this test is using CHZ-USDT as market
    
    buy_filled = 99.9
    buy_price = 10.0
    buy_size = 1000 # round(buy_filled * buy_price, 8)
    buy_fee = 1 # round(buy_size * 0.001, 8)
    sell_percent = 100
    sell_price = 10.0
    sell_size = 999.0 # round((sell_percent / 100) * (sell_price * buy_filled), 8)
    sell_taker_fee = 0.001
    sell_filled = 998.001  # round((sell_size - round(sell_size * sell_taker_fee, 8)), 8)
    sell_fee = 0.0

    expected_sell_fee = 0.999 # round(sell_size * sell_taker_fee, 8)
    expected_profit = -1.999 # round(sell_filled - buy_size, 8)
    expected_margin = -0.1999 # round((expected_profit / buy_size) * 100, 8)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee)

    assert round(actual_margin, 8) == round(expected_margin, 8)
    assert round(actual_profit, 8) == round(expected_profit, 8)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)

def test_binance_microtrading_2():
    # this test is using CHZ-USDT as market
    
    buy_filled = 99.9
    buy_price = 10.0
    buy_size = 1000 # round(buy_filled * buy_price, 8)
    buy_fee = 1 # round(buy_size * 0.001, 8)
    sell_percent = 100
    sell_price = 10.0001
    sell_size = 999.00999 # round((sell_percent / 100) * (sell_price * buy_filled), 8)
    sell_taker_fee = 0.001
    sell_filled = 998.01098001  # round((sell_size - round(sell_size * sell_taker_fee, 8)), 8)
    sell_fee = 0.0

    expected_sell_fee = 0.99900999 # round(sell_size * sell_taker_fee, 8)
    expected_profit = -1.98901999 # round(sell_filled - buy_size, 8)
    expected_margin = -0.198902 # round((expected_profit / buy_size) * 100, 8)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee)

    assert round(actual_margin, 8) == round(expected_margin, 8)
    assert round(actual_profit, 8) == round(expected_profit, 8)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)


def test_binance_microtrading_3():
    # this test is using CHZ-USDT as market
    
    buy_filled = 99.9
    buy_price = 10.0
    buy_size = 1000 # round(buy_filled * buy_price, 8)
    buy_fee = 1 # round(buy_size * 0.001, 8)
    sell_percent = 100
    sell_price = 10.01
    sell_size = 999.999 # round((sell_percent / 100) * (sell_price * buy_filled), 8)
    sell_taker_fee = 0.001
    sell_filled = 998.999001  # round((sell_size - round(sell_size * sell_taker_fee, 8)), 8)
    sell_fee = 0.0

    expected_sell_fee = 0.999999 # round(sell_size * sell_taker_fee, 8)
    expected_profit = -1.000999 # round(sell_filled - buy_size, 8)
    expected_margin = -0.1000999 # round((expected_profit / buy_size) * 100, 8)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee)

    assert round(actual_margin, 8) == round(expected_margin, 8)
    assert round(actual_profit, 8) == round(expected_profit, 8)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)


def test_binance_microtrading_zero_margin():
    # this test is using CHZ-USDT as market
    
    buy_filled = 99.9
    buy_price = 10.0
    buy_size = 1000 # round(buy_filled * buy_price, 8)
    buy_fee = 1 # round(buy_size * 0.001, 8)
    sell_percent = 100
    sell_price = 10.02003004
    sell_size = 1001.001001 # round((sell_percent / 100) * (sell_price * buy_filled), 8)
    sell_taker_fee = 0.001
    sell_filled = 1000.0  # round((sell_size - round(sell_size * sell_taker_fee, 8)), 8)
    sell_fee = 0.0

    expected_sell_fee = 1.001001 # round(sell_size * sell_taker_fee, 8)
    expected_profit = 0.0 # round(sell_filled - buy_size, 8)
    expected_margin = 0.0 # round((expected_profit / buy_size) * 100, 8)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee)

    assert round(actual_margin, 8) == round(expected_margin, 8)
    assert round(actual_profit, 8) == round(expected_profit, 8)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)

def test_binance_microtrading_BNB_max_fee_test():
    # this test is using CHZ-USDT as market
    
    buy_size = 1000 # round(buy_filled * buy_price, 8)
    buy_fee = 0.75 # round(buy_size * 0.00075, 8)
    buy_price = 10.0
    buy_filled = 99.925
    sell_percent = 100
    sell_price = 10.016
    sell_size = 1000.8488 # round((sell_percent / 100) * (sell_price * buy_filled), 8)
    sell_taker_fee = 0.00075
    sell_filled = 1000.0981634  # round((sell_size - round(sell_size * sell_taker_fee, 8)), 8)
    sell_fee = 0.0

    expected_sell_fee = 0.7506366 # round(sell_size * sell_taker_fee, 8)
    expected_profit = 0.0981634 # round(sell_filled - buy_size, 8)
    expected_margin = 0.00981634 # round((expected_profit / buy_size) * 100, 8)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee)

    assert round(actual_margin, 8) == round(expected_margin, 8)
    assert round(actual_profit, 8) == round(expected_profit, 8)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)

def test_binance_microtrading_USDTRY_01():
    # this test is using CHZ-USDT as market
    
    buy_size = 9021.17796 # round(buy_filled * buy_price, 8)
    buy_fee = 9.02117796 # round(buy_size * 0.001, 8)
    buy_price = 8.628
    buy_filled = 1045.57
    sell_percent = 100
    sell_price = 8.639
    sell_size = 9032.67923 # round((sell_percent / 100) * (sell_price * buy_filled), 8)
    sell_taker_fee = 0.001
    sell_filled = 9023.64655077  # round((sell_size - round(sell_size * sell_taker_fee, 8)), 8)
    sell_fee = 9.03267923

    expected_sell_fee = 9.03267923 # round(sell_size * sell_taker_fee, 8)
    expected_profit = 2.46859077 # round(sell_filled - buy_size, 8)
    expected_margin = 0.02736439 # round((expected_profit / buy_size) * 100, 8)

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee)

    assert round(actual_margin, 8) == round(expected_margin, 8)
    assert round(actual_profit, 8) == round(expected_profit, 8)
    assert round(actual_sell_fee, 8) == round(expected_sell_fee, 8)    