import json
import pandas
import pytest
import os
import sys
import urllib3
from os.path import exists
from datetime import datetime

# disable insecure ssl warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append(".")
# pylint: disable=import-error
from models.exchange.binance import AuthAPI
from models.exchange.binance import PublicAPI
from controllers.PyCryptoBot import PyCryptoBot

# api key file for unit tests
API_KEY_FILE = "binance.key"

# there is no dynamic way of retrieving a valid order market
VALID_ORDER_MARKET = "ADAUSDT"  # must contain at least one order


def test_instantiate_authapi_without_error():
    api_key = "0000000000000000000000000000000000000000000000000000000000000000"
    api_secret = "0000000000000000000000000000000000000000000000000000000000000000"
    api = AuthAPI(api_key, api_secret)
    assert type(api) is AuthAPI


def test_instantiate_authapi_with_api_key_error():
    api_key = "ERROR"
    api_secret = "0000000000000000000000000000000000000000000000000000000000000000"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret)
    assert str(execinfo.value) == "Binance API key is invalid"


def test_instantiate_authapi_with_api_secret_error():
    api_key = "0000000000000000000000000000000000000000000000000000000000000000"
    api_secret = "ERROR"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret)
    assert str(execinfo.value) == "Binance API secret is invalid"


def test_instantiate_authapi_with_api_url_error():
    api_key = "0000000000000000000000000000000000000000000000000000000000000000"
    api_secret = "0000000000000000000000000000000000000000000000000000000000000000"
    api_url = "ERROR"

    with pytest.raises(ValueError) as execinfo:
        AuthAPI(api_key, api_secret, api_url)
    assert str(execinfo.value) == "Binance API URL is invalid"


def test_instantiate_publicapi_without_error():
    api = PublicAPI()
    assert type(api) is PublicAPI


def test_get_account():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    df = api.get_account()
    assert type(api) is AuthAPI

    df = api.get_account()
    assert type(df) is pandas.core.frame.DataFrame

    actual = df.columns.to_list()
    expected = ["index", "id", "currency", "balance", "hold", "available", "profile_id", "trading_enabled"]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])


def test_get_usd_volume():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    resp = api.get_usd_volume()
    assert type(resp) is float
    assert resp > 0


def test_get_fees_without_market():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    df = api.get_fees()
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) == 1

    actual = df.columns.to_list()
    expected = ["maker_fee_rate", "taker_fee_rate", "usd_volume", "market"]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])


def test_get_fees_with_market():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    df = api.get_fees(VALID_ORDER_MARKET)
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) == 1

    actual = df.columns.to_list()
    expected = ["maker_fee_rate", "taker_fee_rate", "usd_volume", "market"]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])


def test_get_taker_fee_without_market():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    fee = api.get_taker_fee()
    assert type(fee) is float
    assert fee > 0


def test_get_taker_fee_with_market():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    fee = api.get_taker_fee(VALID_ORDER_MARKET)
    assert type(fee) is float
    assert fee > 0


def test_get_maker_fee_without_market():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    fee = api.get_maker_fee()
    assert type(fee) is float
    assert fee > 0


def test_get_maker_fee_with_market():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    fee = api.get_maker_fee(VALID_ORDER_MARKET)
    assert type(fee) is float
    assert fee > 0


def test_get_orders():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    df = api.get_orders(VALID_ORDER_MARKET)
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) > 0

    actual = df.columns.to_list()
    expected = ["created_at", "market", "action", "type", "size", "filled", "fees", "price", "status"]
    #  order is not important, but no duplicates
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff


def test_get_order_history():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    df = api.get_orders(order_history=[VALID_ORDER_MARKET])
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) > 0

    actual = df.columns.to_list()
    expected = ["created_at", "market", "action", "type", "size", "filled", "fees", "price", "status"]
    #  order is not important, but no duplicates
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff


def test_get_orders_invalid_market():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    assert type(api) is AuthAPI

    resp = api.get_orders(market="ERROR")
    assert type(resp) is str, "get_orders() should return a string with the error message"
    assert resp == "Invalid market."


def test_get_orders_valid_market():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    assert type(api) is AuthAPI

    df = api.get_orders(market=VALID_ORDER_MARKET)
    assert len(df) > 0

    actual = df.columns.to_list()
    expected = ["created_at", "market", "action", "type", "size", "filled", "fees", "price", "status"]
    #  order is not important, but no duplicate
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff


def test_get_orders_invalid_action():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    assert type(api) is AuthAPI

    with pytest.raises(ValueError) as execinfo:
        api.get_orders(action="ERROR")
    assert str(execinfo.value) == "Invalid order action."


def test_get_orders_valid_action_buy():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    assert type(api) is AuthAPI

    df = api.get_orders(market=VALID_ORDER_MARKET, action="buy")
    assert len(df) >= 0

    actual = df.columns.to_list()
    expected = ["created_at", "market", "action", "type", "size", "filled", "fees", "price", "status"]
    #  order is not important, but no duplicate
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff


def test_get_orders_valid_action_sell():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    assert type(api) is AuthAPI

    df = api.get_orders(market=VALID_ORDER_MARKET, action="sell")
    assert len(df) >= 0

    actual = df.columns.to_list()
    expected = ["created_at", "market", "action", "type", "size", "filled", "fees", "price", "status"]
    #  order is not important, but no duplicate
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff


def test_get_orders_invalid_status():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    assert type(api) is AuthAPI

    with pytest.raises(ValueError) as execinfo:
        api.get_orders(status="ERROR")
    assert str(execinfo.value) == "Invalid order status."


def test_get_orders_valid_status_all():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    assert type(api) is AuthAPI

    df = api.get_orders(market=VALID_ORDER_MARKET, status="all")

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = ["created_at", "market", "action", "type", "size", "filled", "fees", "price", "status"]
        #  order is not important, but no duplicate
        assert len(actual) == len(expected)
        diff = set(actual) ^ set(expected)
        assert not diff


def test_get_orders_valid_status_open():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    assert type(api) is AuthAPI

    df = api.get_orders(market=VALID_ORDER_MARKET, status="open")

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = ["created_at", "market", "action", "type", "size", "filled", "fees", "price", "status"]
        #  order is not important, but no duplicate
        assert len(actual) == len(expected)
        diff = set(actual) ^ set(expected)
        assert not diff


def test_get_orders_valid_status_pending():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    assert type(api) is AuthAPI

    df = api.get_orders(market=VALID_ORDER_MARKET, status="pending")

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = ["created_at", "market", "action", "type", "size", "filled", "fees", "price", "status"]
        #  order is not important, but no duplicate
        assert len(actual) == len(expected)
        diff = set(actual) ^ set(expected)
        assert not diff


def test_get_orders_valid_status_done():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    assert type(api) is AuthAPI

    df = api.get_orders(market=VALID_ORDER_MARKET, status="done")

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = ["created_at", "market", "action", "type", "size", "filled", "fees", "price", "status"]
        #  order is not important, but no duplicate
        assert len(actual) == len(expected)
        diff = set(actual) ^ set(expected)
        assert not diff


def test_get_orders_valid_status_active():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    assert type(api) is AuthAPI

    df = api.get_orders(market=VALID_ORDER_MARKET, status="active")

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = ["created_at", "market", "action", "type", "size", "filled", "fees", "price", "status"]
        #  order is not important, but no duplicate
        assert len(actual) == len(expected)
        diff = set(actual) ^ set(expected)
        assert not diff


def test_get_time():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
    assert type(api) is AuthAPI

    resp = api.get_time()
    assert type(resp) is datetime


def test_get_ticker():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = PublicAPI(app=app)
    assert type(api) is PublicAPI

    resp = api.get_ticker()
    assert type(resp) is tuple
    assert len(resp) == 2
    assert type(resp[0]) is str
    assert type(resp[1]) is float


def test_market_buy_invalid_market():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_url, app=app)

    resp = api.market_buy("ERROR", 0.0001, test=True)
    assert type(resp) is str, "market_buy() should return a string with the error message"
    assert resp == "Invalid market."


def test_historical_data_market_granularity_only():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = PublicAPI(app=app)
    assert type(api) is PublicAPI

    df = api.get_historical_data("BTCGBP", "1h")
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) == 300

    actual = df.columns.to_list()
    expected = ["date", "market", "granularity", "low", "high", "open", "close", "volume"]
    #  order is not important, but no duplicate
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff

def test_historical_data_invalid_market():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = PublicAPI(app=app)
    assert type(api) is PublicAPI

    df = api.get_historical_data("ERROR", "1h")
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) == 0

def test_historical_data_invalid_granularity():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = PublicAPI(app=app)
    assert type(api) is PublicAPI

    df = api.get_historical_data("BTCGBP", "ERROR")
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) == 0

def test_historical_data_market_granularity_date_range():
    app = PyCryptoBot(exchange="binance")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 2:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = PublicAPI(app=app)
    assert type(api) is PublicAPI

    df = api.get_historical_data("BTCGBP", "1h", None, "2020-06-19T10:00:00", "2020-06-19T14:00:00")
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) == 5

    actual = df.columns.to_list()
    expected = ["date", "market", "granularity", "low", "high", "open", "close", "volume"]
    #  order is not important, but no duplicate
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff
