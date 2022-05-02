import json
import pytest
import responses
import requests
import sys
import pandas

sys.path.append(".")
# pylint: disable=import-error
from models.exchange.ExchangesEnum import Exchange
from models.PyCryptoBot import PyCryptoBot
from models.exchange.binance import AuthAPI, PublicAPI

app = PyCryptoBot(exchange=Exchange.BINANCE)

@pytest.mark.skip
@responses.activate
def test_api_v3_account1():
    #global app
    api = AuthAPI(app.api_key, app.api_secret)

    with open("tests/unit_tests/responses/account1.json") as fh:
        responses.add(
            responses.GET,
            "https://api.binance.com/api/v3/account",
            json=json.load(fh),
            status=200,
        )
        df = api.getAccounts()
        fh.close()

        assert len(df) > 1
        assert df.columns.tolist() == [
            "index",
            "id",
            "currency",
            "balance",
            "hold",
            "available",
            "profile_id",
            "trading_enabled",
        ]
        assert df.dtypes["index"] == "int64"
        assert df.dtypes["id"] == "object"
        assert df.dtypes["currency"] == "object"
        assert df.dtypes["balance"] == "object"
        assert df.dtypes["hold"] == "object"
        assert df.dtypes["available"] == "object"
        assert df.dtypes["profile_id"] == "object"
        assert df.dtypes["trading_enabled"] == "bool"


def test_instantiate_authapi_without_error():
    global app
    exchange = AuthAPI(app.api_key, app.api_secret)
    assert type(exchange) is AuthAPI


def test_instantiate_authapi_with_api_key_error():
    global app
    api_key = "Invalid"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, app.api_secret)
    assert str(execinfo.value) == "Binance API key is invalid"


def test_instantiate_authapi_with_api_secret_error():
    global app
    api_secret = "Ivalid"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(app.api_key, api_secret)
    assert str(execinfo.value) == "Binance API secret is invalid"


def test_instantiate_authapi_with_api_url_error():
    global app
    api_url = "https://foo.com"

    with pytest.raises(ValueError) as execinfo:
        AuthAPI(app.api_key, app.api_secret, api_url)
    assert str(execinfo.value) == "Binance API URL is invalid"


def test_instantiate_publicapi_without_error():
    exchange = PublicAPI()
    assert type(exchange) is PublicAPI


@pytest.mark.skip
@responses.activate  # mocker response required
def test_get_fees_with_market():
    global app
    exchange = AuthAPI(app.api_key, app.api_secret)
    assert type(exchange) is AuthAPI

    df = exchange.getFees()
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) == 1

    actual = df.columns.to_list()
    expected = ["maker_fee_rate", "taker_fee_rate", "usd_volume", "market"]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])


@pytest.mark.skip
@responses.activate  # mocker response required
def test_get_taker_fee_with_market():
    global app
    exchange = AuthAPI(app.api_key, app.api_secret)
    assert type(exchange) is AuthAPI

    fee = exchange.getTakerFee()
    assert type(fee) is float
    assert fee == 0.0015


@pytest.mark.skip
@responses.activate  # mocker response required
def test_get_maker_fee_with_market():
    global app
    exchange = AuthAPI(app.api_key, app.api_secret)
    assert type(exchange) is AuthAPI

    fee = exchange.getMakerFee()
    assert type(fee) is float
    assert fee == 0.0015


@pytest.mark.skip
@responses.activate  # mocker response required
def test_get_orders():
    global app
    exchange = AuthAPI(app.api_key, app.api_secret)
    assert type(exchange) is AuthAPI

    df = exchange.getOrders()
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) > 0

    actual = df.columns.to_list()
    expected = [
        "created_at",
        "market",
        "action",
        "type",
        "size",
        "filled",
        "status",
        "price",
    ]
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff


# TODO
# add missing tests from prior unit_test file:
# def test_config_json_exists_and_valid(): -> imo obsolete/pointless, we are reading the config
#       when instantiating PyCryptoBot class
#
@pytest.fixture
def binance_orders_response():
    return [
        {
            "symbol": "LTCBTC",
            "orderId": 1,
            "orderListId": -1,
            "clientOrderId": "myOrder1",
            "price": "0.1",
            "origQty": "1.0",
            "executedQty": "0.0",
            "cummulativeQuoteQty": "0.0",
            "status": "NEW",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": "BUY",
            "stopPrice": "0.0",
            "icebergQty": "0.0",
            "time": 1499827319559,
            "updateTime": 1499827319559,
            "isWorking": "true",
            "origQuoteOrderQty": "0.000000",
        }
    ]
