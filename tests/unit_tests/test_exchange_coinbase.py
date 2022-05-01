import json
import pytest
import responses
import requests
import sys
import pandas

sys.path.append('.')
# pylint: disable=import-error
from models.exchange.ExchangesEnum import Exchange
from models.PyCryptoBot import PyCryptoBot
from models.exchange.coinbase_pro import AuthAPI, PublicAPI

app = PyCryptoBot(exchange= Exchange.COINBASEPRO)

def test_instantiate_authapi_without_error():
    global app
    api_key = app.getAPIKey()
    api_secret = app.getAPISecret()
    api_passphrase = app.getAPIPassphrase()
    exchange = AuthAPI(api_key, api_secret, api_passphrase)
    assert type(exchange) is AuthAPI


def test_instantiate_authapi_with_api_key_error():
    global app
    api_key = "Invalid"
    api_secret = app.getAPISecret()
    api_passphrase = app.getAPIPassphrase()

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret)
    assert str(execinfo.value) == 'Coinbase Pro API key is invalid'


def test_instantiate_authapi_with_api_secret_error():
    global app
    api_key = app.getAPIKey()
    api_secret = "Ivalid"
    api_passphrase = app.getAPIPassphrase()

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase)
    assert str(execinfo.value) == 'Coinbase Pro API secret is invalid'


def test_instantiate_authapi_with_api_url_error():
    api_key = app.getAPIKey()
    api_secret = app.getAPISecret()
    api_passphrase = app.getAPIPassphrase()
    api_url = "https://foo.com"

    with pytest.raises(ValueError) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase, api_url)
    assert str(execinfo.value) == 'Coinbase Pro API URL is invalid'


def test_instantiate_publicapi_without_error():
    exchange = PublicAPI()
    assert type(exchange) is PublicAPI



def test_get_taker_fee_with_market():
    api_key = app.getAPIKey()
    api_secret = app.getAPISecret()
    api_passphrase = app.getAPIPassphrase()
    api_url = "https://public.sandbox.pro.coinbase.com"
    exchange = AuthAPI(api_key, api_secret, api_passphrase, api_url)
    assert type(exchange) is AuthAPI

    fee = exchange.getTakerFee()
    assert type(fee) is float
    assert fee == 0.005


def test_get_maker_fee_with_market():
    api_key = app.getAPIKey()
    api_secret = app.getAPISecret()
    api_passphrase = app.getAPIPassphrase()
    api_url = "https://public.sandbox.pro.coinbase.com"
    exchange = AuthAPI(api_key, api_secret, api_passphrase, api_url)
    assert type(exchange) is AuthAPI

    fee = exchange.getMakerFee()
    assert type(fee) is float
    assert fee == 0.005


## TODO: fix tests below
# this is more or less copy pasted from binance
@pytest.mark.skip
@responses.activate
def test_api_v3_account1():
    global app
    api_key = app.getAPIKey()
    api_secret = app.getAPISecret()
    api_passphrase = app.getAPIPassphrase()
    api_url = "https://public.sandbox.pro.coinbase.com"
    api = AuthAPI(api_key, api_secret, api_passphrase, api_url)

    with open('tests/unit_tests/responses/account1.json') as fh:
        responses.add(responses.GET, f'{api_url}/account', json=json.load(fh), status=200)
        df = api.getAccounts()
        fh.close()

        assert len(df) > 1
        assert df.columns.tolist() == [ 'index', 'id', 'currency', 'balance', 'hold', 'available', 'profile_id', 'trading_enabled' ]
        assert df.dtypes['index'] == 'int64'
        assert df.dtypes['id'] == 'object'
        assert df.dtypes['currency'] == 'object'
        assert df.dtypes['balance'] == 'object'
        assert df.dtypes['hold'] == 'object'
        assert df.dtypes['available'] == 'object'
        assert df.dtypes['profile_id'] == 'object'
        assert df.dtypes['trading_enabled'] == 'bool'


@pytest.mark.skip
def test_get_orders():
    api_key = app.getAPIKey()
    api_secret = app.getAPISecret()
    api_passphrase = app.getAPIPassphrase()
    api_url = "https://public.sandbox.pro.coinbase.com"
    exchange = AuthAPI(api_key, api_secret, api_passphrase, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.getOrders()
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) > 0
    actual = df.columns.to_list()
    expected = ['created_at', 'market', 'action', 'type', 'size', 'filled', 'status', 'price']
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff

@pytest.mark.skip
def test_get_fees_with_market():
    api_key = app.getAPIKey()
    api_secret = app.getAPISecret()
    api_passphrase = app.getAPIPassphrase()
    api_url = "https://public.sandbox.pro.coinbase.com"
    exchange = AuthAPI(api_key, api_secret, api_passphrase, api_url)
    assert type(exchange) is AuthAPI
    df = exchange.getFees()
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) == 1
    actual = df.columns.to_list()
    expected = ['maker_fee_rate', 'taker_fee_rate', 'usd_volume', 'market']
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])
