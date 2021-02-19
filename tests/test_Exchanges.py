import pytest, json, sys
import pandas as pd
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('.')
# pylint: disable=import-error
from models.TradingAccount import TradingAccount

BINANCE_MARKET_WITH_ORDERS = 'DOGEBTC'
COINBASEPRO_MARKET_WITH_ORDERS = 'BTC-GBP'

def test_default_instantiates_without_error():
    account = TradingAccount()
    assert type(account) is TradingAccount
    assert account.getExchange() == 'coinbasepro'
    assert account.getMode() == 'test'

def test_coinbasepro_instantiates_without_error():
    config = {
        "api_url" : "https://api.pro.coinbase.com",
        "api_key" : "00000000000000000000000000000000",
        "api_secret" : "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000==",
        "api_pass" : "00000000000"
    }

    account = TradingAccount(config)
    assert type(account) is TradingAccount
    assert account.getExchange() == 'coinbasepro'
    assert account.getMode() == 'live'

def test_coinbasepro_api_url_error():
    config = {
        "api_url" : "error",
        "api_key" : "00000000000000000000000000000000",
        "api_secret" : "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000==",
        "api_pass" : "00000000000"
    }

    with pytest.raises(ValueError) as execinfo:
        TradingAccount(config)
    assert str(execinfo.value) == 'Coinbase Pro API URL is invalid'

def test_coinbasepro_api_key_error():
    config = {
        "api_url" : "https://api.pro.coinbase.com",
        "api_key" : "error",
        "api_secret" : "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000==",
        "api_pass" : "00000000000"
    }

    with pytest.raises(TypeError) as execinfo:
        TradingAccount(config)
    assert str(execinfo.value) == 'Coinbase Pro API key is invalid'

def test_coinbasepro_api_secret_error():
    config = {
        "api_url" : "https://api.pro.coinbase.com",
        "api_key" : "00000000000000000000000000000000",
        "api_secret" : "error",
        "api_pass" : "00000000000"
    }

    with pytest.raises(TypeError) as execinfo:
        TradingAccount(config)
    assert str(execinfo.value) == 'Coinbase Pro API secret is invalid'

def test_coinbasepro_api_pass_error():
    config = {
        "api_url" : "https://api.pro.coinbase.com",
        "api_key" : "00000000000000000000000000000000",
        "api_secret" : "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000==",
        "api_pass" : "error"
    }

    with pytest.raises(TypeError) as execinfo:
        TradingAccount(config)
    assert str(execinfo.value) == 'Coinbase Pro API passphrase is invalid'

def test_binance_instantiates_without_error():
    config = {
        "exchange" : "binance",
        "api_url" : "https://api.binance.com",
        "api_key" : "0000000000000000000000000000000000000000000000000000000000000000",
        "api_secret" : "0000000000000000000000000000000000000000000000000000000000000000"
    }

    account = TradingAccount(config)
    assert type(account) is TradingAccount
    assert account.getExchange() == 'binance'
    assert account.getMode() == 'live'

def test_binance_api_url_error():
    config = {
        "exchange" : "binance",
        "api_url" : "error",
        "api_key" : "0000000000000000000000000000000000000000000000000000000000000000",
        "api_secret" : "0000000000000000000000000000000000000000000000000000000000000000"
    }

    with pytest.raises(ValueError) as execinfo:
        TradingAccount(config)
    assert str(execinfo.value) == 'Binance API URL is invalid'

def test_binance_api_key_error():
    config = {
        "exchange" : "binance",
        "api_url" : "https://api.binance.com",
        "api_key" : "error",
        "api_secret" : "0000000000000000000000000000000000000000000000000000000000000000"
    }

    with pytest.raises(TypeError) as execinfo:
        TradingAccount(config)
    assert str(execinfo.value) == 'Binance API key is invalid'

def test_binance_api_secret_error():
    config = {
        "exchange" : "binance",
        "api_url" : "https://api.binance.com",
        "api_key" : "0000000000000000000000000000000000000000000000000000000000000000",
        "api_secret" : "error"
    }

    with pytest.raises(TypeError) as execinfo:
        TradingAccount(config)
    assert str(execinfo.value) == 'Binance API secret is invalid'

def test_binance_not_load():
    config = {
        "api_url" : "https://api.binance.com",
        "api_key" : "0000000000000000000000000000000000000000000000000000000000000000",
        "api_secret" : "0000000000000000000000000000000000000000000000000000000000000000"
    }

    account = TradingAccount(config)
    assert type(account) is TradingAccount
    assert account.getExchange() == 'coinbasepro'
    assert account.getMode() == 'test'

def test_dummy_balances():
    account = TradingAccount()
    actual = account.getBalance().columns.to_list()
    if len(actual) == 0:
        pytest.skip('No balances to perform test')
    assert type(actual) is list
    expected = [ 'currency', 'balance', 'hold', 'available' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])
    assert account.getExchange() == 'coinbasepro'
    assert account.getMode() == 'test'

def test_dummy_market_balance():
    account = TradingAccount()
    actual = account.getBalance('GBP')
    assert type(actual) is float
    assert account.getExchange() == 'coinbasepro'
    assert account.getMode() == 'test'

def test_coinbasepro_balances():
    try:
        with open('config-coinbasepro.json') as config_file:
            config = json.load(config_file)

        account = TradingAccount(config)
        assert type(account) is TradingAccount
        assert account.getExchange() == 'coinbasepro'
        assert account.getMode() == 'live'

        actual = account.getBalance().columns.to_list()
        if len(actual) == 0:
            pytest.skip('No balances to perform test')
        assert type(actual) is list
        expected = [ 'currency', 'balance', 'hold', 'available' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

    except IOError:
        pytest.skip('config-coinbasepro.json does not exist to perform test')

def test_coinbasepro_market_balance():
    try:
        with open('config-coinbasepro.json') as config_file:
            config = json.load(config_file)

        account = TradingAccount(config)
        actual = account.getBalance('BTC')
        assert type(actual) is float
        assert account.getExchange() == 'coinbasepro'
        assert account.getMode() == 'live'

    except IOError:
        pytest.skip('config-coinbasepro.json does not exist to perform test')

def test_binance_balances():
    try:
        with open('config-binance.json') as config_file:
            config = json.load(config_file)

        account = TradingAccount(config)
        assert type(account) is TradingAccount
        assert account.getExchange() == 'binance'
        assert account.getMode() == 'live'

        actual = account.getBalance().columns.to_list()
        if len(actual) == 0:
            pytest.skip('No orders to perform test')
        assert type(actual) is list
        expected = [ 'currency', 'balance', 'hold', 'available' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

    except IOError:
        pytest.skip('config-binance.json does not exist to perform test')

def test_binance_market_balance():
    try:
        with open('config-binance.json') as config_file:
            config = json.load(config_file)

        account = TradingAccount(config)
        actual = account.getBalance('BTC')
        assert type(actual) is float
        assert account.getExchange() == 'binance'
        assert account.getMode() == 'live'

    except IOError:
        pytest.skip('config-binance.json does not exist to perform test')

def test_dummy_orders():
    account = TradingAccount()
    account.buy('BTC', 'GBP', 1000, 30000)
    actual = account.getOrders().columns.to_list()
    if len(actual) == 0:
        pytest.skip('No orders to perform test')
    expected = [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])
    assert account.getExchange() == 'coinbasepro'
    assert account.getMode() == 'test'

def test_coinbasepro_all_orders():
    try:
        with open('config-coinbasepro.json') as config_file:
            config = json.load(config_file)

        account = TradingAccount(config)
        assert type(account) is TradingAccount
        assert account.getExchange() == 'coinbasepro'
        assert account.getMode() == 'live'

        actual = account.getOrders().columns.to_list()
        if len(actual) == 0:
            pytest.skip('No orders to perform test')
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

    except IOError:
        pytest.skip('config-coinbasepro.json does not exist to perform test')

def test_coinbasepro_market_orders():
    try:
        with open('config-coinbasepro.json') as config_file:
            config = json.load(config_file)

        account = TradingAccount(config)
        assert type(account) is TradingAccount
        assert account.getExchange() == 'coinbasepro'
        assert account.getMode() == 'live'

        actual = account.getOrders(COINBASEPRO_MARKET_WITH_ORDERS).columns.to_list()
        if len(actual) == 0:
            pytest.skip('No orders to perform test')
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

    except IOError:
        pytest.skip('config-coinbasepro.json does not exist to perform test')

def test_binance_market_orders():
    try:
        with open('config-binance.json') as config_file:
            config = json.load(config_file)

        account = TradingAccount(config)
        assert type(account) is TradingAccount
        assert account.getExchange() == 'binance'
        assert account.getMode() == 'live'

        actual = account.getOrders(BINANCE_MARKET_WITH_ORDERS).columns.to_list()
        if len(actual) == 0:
            pytest.skip('No orders to perform test')
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

    except IOError:
        pytest.skip('config-binance.json does not exist to perform test')

def test_binance_market_buy_insufficient_funds():
    try:
        with open('config-binance.json') as config_file:
            config = json.load(config_file)

        account = TradingAccount(config)
        with pytest.raises(Exception) as execinfo:
            account.buy('DOGE', 'BTC', 1000000, 0.000025)
        assert str(execinfo.value) == 'APIError(code=-2010): Account has insufficient balance for requested action.'

    except IOError:
        pytest.skip('config-binance.json does not exist to perform test')

def test_coinbasepro_market_buy_insufficient_funds():
    with open('config-coinbasepro.json') as config_file:
        config = json.load(config_file)

    account = TradingAccount(config)
    resp = account.buy('BTC', 'GBP', 20000)
    assert str(resp) == 'None'