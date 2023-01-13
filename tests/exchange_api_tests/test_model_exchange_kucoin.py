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
    assert str(execinfo.value) == 'Kucoin API key is invalid'

def test_instantiate_authapi_with_api_secret_error():
    api_key = "000000000000000000000000"
    api_secret = "ERROR"
    api_passphrase = "00000000"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase)
    assert str(execinfo.value) == 'Kucoin API secret is invalid'

def test_instantiate_authapi_with_api_passphrase_error():
    api_key = "000000000000000000000000"
    api_secret = "000000000000000000000000000000000000"
    api_passphrase = "ERROR"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase)
    assert str(execinfo.value) == 'Kucoin API passphrase is invalid'

def test_instantiate_authapi_with_api_url_error():
    api_key = "000000000000000000000000"
    api_secret = "000000000000000000000000000000000000"
    api_passphrase = "00000000"
    api_url = "ERROR"

    with pytest.raises(ValueError) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase, api_url)
    assert str(execinfo.value) == 'Kucoin API URL is invalid'

def test_instantiate_publicapi_without_error():
    exchange = PublicAPI()
    assert type(exchange) is PublicAPI
