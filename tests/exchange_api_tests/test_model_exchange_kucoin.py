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
from models.exchange.kucoin import AuthAPI
from models.exchange.kucoin import PublicAPI
from controllers.PyCryptoBot import PyCryptoBot

# api key file for unit tests
API_KEY_FILE = "kucoin.key"

# there is no dynamic way of retrieving a valid order market
VALID_ORDER_MARKET = "ADAUSDT"  # must contain at least one order


def test_instantiate_authapi_without_error():
    api_key = "000000000000000000000000"
    api_secret = "000000000000000000000000000000000000"
    api_passphrase = "00000000"
    exchange = AuthAPI(api_key, api_secret, api_passphrase)
    assert type(exchange) is AuthAPI


def test_instantiate_authapi_with_api_key_error():
    api_key = "ERROR"
    api_secret = "000000000000000000000000000000000000"
    api_passphrase = "00000000"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase)
    assert str(execinfo.value) == "Kucoin API key is invalid"


def test_instantiate_authapi_with_api_secret_error():
    api_key = "000000000000000000000000"
    api_secret = "ERROR"
    api_passphrase = "00000000"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase)
    assert str(execinfo.value) == "Kucoin API secret is invalid"


def test_instantiate_authapi_with_api_passphrase_error():
    api_key = "000000000000000000000000"
    api_secret = "000000000000000000000000000000000000"
    api_passphrase = "ERROR"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase)
    assert str(execinfo.value) == "Kucoin API passphrase is invalid"


def test_instantiate_authapi_with_api_url_error():
    api_key = "000000000000000000000000"
    api_secret = "000000000000000000000000000000000000"
    api_passphrase = "00000000"
    api_url = "ERROR"

    with pytest.raises(ValueError) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase, api_url)
    assert str(execinfo.value) == "Kucoin API URL is invalid"


def test_instantiate_publicapi_without_error():
    exchange = PublicAPI()
    assert type(exchange) is PublicAPI


def test_config_json_exists_and_valid():
    filename = "config.json"
    assert os.path.exists(filename) is True

    with open(filename) as config_file:
        config = json.load(config_file)

        if "kucoin" not in config:
            pytest.skip("config.json does not contain kucoin")

        api_key = ""
        api_secret = ""
        api_passphrase = ""
        api_url = ""
        if "api_key" in config and "api_secret" in config and "api_pass" in config and "api_url" in config:
            api_key = config["api_key"]
            api_secret = config["api_secret"]
            api_passphrase = config["api_pass"]
            api_url = config["api_url"]
            AuthAPI(api_key, api_secret, api_passphrase, api_url)
        elif "api_key" in config["kucoin"] and "api_secret" in config["kucoin"] and "api_passphrase" in config["kucoin"] and "api_url" in config["kucoin"]:
            api_key = config["kucoin"]["api_key"]
            api_secret = config["kucoin"]["api_secret"]
            api_passphrase = config["kucoin"]["api_passphrase"]
            api_url = config["kucoin"]["api_url"]
            AuthAPI(api_key, api_secret, api_passphrase, api_url)
    pass


def test_get_accounts():
    app = PyCryptoBot(exchange="kucoin")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 3:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
    df = api.get_accounts()
    assert type(df) is pandas.core.frame.DataFrame

    if len(df) == 0:
        pytest.skip("skipping test as no account data is available")

    actual = df.columns.to_list()
    expected = ["index", "id", "currency", "type", "balance", "available", "holds"]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_get_fees_without_market():
    app = PyCryptoBot(exchange="kucoin")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 3:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
    df = api.get_fees()
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) == 1

    actual = df.columns.to_list()
    expected = ["takerFeeRate", "makerFeeRate", "market"]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])


def test_get_fees_with_market():
    app = PyCryptoBot(exchange="kucoin")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 3:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
    df = api.get_fees(VALID_ORDER_MARKET)
    assert type(df) is pandas.core.frame.DataFrame
    assert len(df) == 1

    actual = df.columns.to_list()
    expected = ["takerFeeRate", "makerFeeRate", "market"]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_get_taker_fee_without_market():
    app = PyCryptoBot(exchange="kucoin")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 3:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
    fee = api.get_taker_fee()
    assert type(fee) is float
    assert fee > 0


def test_get_taker_fee_with_market():
    app = PyCryptoBot(exchange="kucoin")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 3:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
    fee = api.get_taker_fee(VALID_ORDER_MARKET)
    assert type(fee) is float
    assert fee > 0


def test_get_maker_fee_without_market():
    app = PyCryptoBot(exchange="kucoin")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 3:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
    fee = api.get_maker_fee()
    assert type(fee) is float
    assert fee > 0


def test_get_maker_fee_with_market():
    app = PyCryptoBot(exchange="kucoin")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 3:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
    fee = api.get_maker_fee(VALID_ORDER_MARKET)
    assert type(fee) is float
    assert fee > 0
