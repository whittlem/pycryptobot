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
from models.exchange.coinbase_pro import AuthAPI
from models.exchange.coinbase_pro import PublicAPI
from controllers.PyCryptoBot import PyCryptoBot

# api key file for unit tests
API_KEY_FILE = "coinbasepro.key"

# there is no dynamic way of retrieving a valid order market
VALID_ORDER_MARKET = "BTC-GBP"  # must contain at least one order


def test_instantiate_authapi_without_error():
    api_key = "00000000000000000000000000000000"
    api_secret = "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000=="
    api_passphrase = "00000000000"
    exchange = AuthAPI(api_key, api_secret, api_passphrase)
    assert type(exchange) is AuthAPI


def test_instantiate_authapi_with_api_key_error():
    api_key = "ERROR"
    api_secret = "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000=="
    api_passphrase = "00000000000"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase)
    assert str(execinfo.value) == "Coinbase Pro API key is invalid"


def test_instantiate_authapi_with_api_secret_error():
    api_key = "00000000000000000000000000000000"
    api_secret = "ERROR"
    api_passphrase = "00000000000"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase)
    assert str(execinfo.value) == "Coinbase Pro API secret is invalid"


def test_instantiate_authapi_with_api_passphrase_error():
    api_key = "00000000000000000000000000000000"
    api_secret = "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000=="
    api_passphrase = "ERROR"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase)
    assert str(execinfo.value) == "Coinbase Pro API passphrase is invalid"


def test_instantiate_authapi_with_api_url_error():
    api_key = "00000000000000000000000000000000"
    api_secret = "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000=="
    api_passphrase = "00000000000"
    api_url = "ERROR"

    with pytest.raises(ValueError) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase, api_url)
    assert str(execinfo.value) == "Coinbase Pro API URL is invalid"


def test_instantiate_publicapi_without_error():
    exchange = PublicAPI()
    assert type(exchange) is PublicAPI


def test_config_json_exists_and_valid():
    filename = "config.json"
    assert os.path.exists(filename) is True

    with open(filename) as config_file:
        config = json.load(config_file)

        if "coinbasepro" not in config:
            pytest.skip("config.json does not contain coinbasepro")

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
        elif "api_key" in config["coinbasepro"] and "api_secret" in config["coinbasepro"] and "api_passphrase" in config["coinbasepro"] and "api_url" in config["coinbasepro"]:
            api_key = config["coinbasepro"]["api_key"]
            api_secret = config["coinbasepro"]["api_secret"]
            api_passphrase = config["coinbasepro"]["api_passphrase"]
            api_url = config["coinbasepro"]["api_url"]
            AuthAPI(api_key, api_secret, api_passphrase, api_url)
    pass


def test_get_accounts():
    app = PyCryptoBot(exchange="coinbasepro")

    if not exists(app.api_key_file):
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not exist!')

    key_file = open(app.api_key_file, "r")
    file_api_keys = key_file.readlines()

    if len(file_api_keys) != 3:
        pytest.skip(f'api key file "{app.api_key_file}" for unit tests does not contain a valid api key and secret!')

    api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
    df = api.get_accounts()
    assert type(df) is pandas.core.frame.DataFrame

    actual = df.columns.to_list()
    expected = ["index", "id", "currency", "balance", "hold", "available", "profile_id", "trading_enabled"]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])
