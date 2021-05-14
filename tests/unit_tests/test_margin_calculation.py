import sys
sys.path.append('.')
from models.helper.MarginHelper import calculate_margin


def test_calculate_negative_margin_on_binance_when_coin_price_over_1():
    # this test using BNB-USDT as market
    buy_fee = 0.044706420000000004
    buy_filled = 44.70642
    buy_price = 667.26
    buy_size = 0.067
    debug = False
    sell_fee = 0.0
    sell_percent = 100
    sell_price = 570.92
    sell_taker_fee = 0.005
    exchange = 'binance'

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee,
                                                                     debug, exchange)
    assert actual_margin == -14.443925260064464
    assert actual_profit == -96.38499305219739
    assert actual_sell_fee == 0.00028663219734436355


def test_calculate_negative_margin_on_binance_when_coin_price_under_1():
    # this test is using CHZ-USDT as market
    # 2021-05-14 10:00:00 | CHZUSDT | 1h | Close: 0.43 | ^ EMA12/26: 0.43 > 0.42 ^ | ^ MACD: 0.0 > -0.01 ^ | WAIT | Last Action: BUY | -148.05% (delta: -0.06)
    buy_fee = 0.22
    buy_filled = 88.043592
    buy_price = 0.4968600000000001
    buy_size = 177.2
    debug = False
    exchange = 'binance'
    sell_fee = 0.0
    sell_percent = 100
    sell_price = 0.43828
    sell_taker_fee = 0.005

    actual_margin, actual_profit, actual_sell_fee = calculate_margin(buy_size, buy_filled, buy_price, buy_fee,
                                                                     sell_percent, sell_price, sell_fee, sell_taker_fee,
                                                                     debug, exchange)
    # sell_size = (sell_percent / 100) * ((sell_price / buy_price) * buy_size) == 156.3080465322223
    # buy_value = buy_price + buy_fee == 0.71686
    # sell_value = sell_price - sell_fee == -0.3432602326611115  ::: Note: sell_fee == 0.7815402326611115
    # margin = (profit / buy_value) * 100 ::: (-1.0601202326611117 / 0.71686) * 100 == -147.88385914419993
    assert actual_margin == -147.88385914419993
    assert actual_profit == -1.0601202326611117
    assert actual_sell_fee == 0.7815402326611115
