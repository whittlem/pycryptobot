import pytest, sys

sys.path.append('.')
# pylint: disable=import-error
from models.CoinbasePro import AuthAPI, PublicAPI

def test_instantiate_authapi_without_error():
    api_key = "00000000000000000000000000000000"
    api_secret = "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000=="
    api_passphrase = "00000000000"
    exchange = AuthAPI(api_key, api_secret, api_passphrase)
    assert type(exchange) is AuthAPI

def test_instantiate_authapi_with_api_key_error():
    api_key = "ERROR"
    api_secret = "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000=="
    api_passphrase = "00000000000"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase)
    assert str(execinfo.value) == 'Coinbase Pro API key is invalid'

def test_instantiate_authapi_with_api_secret_error():
    api_key = "00000000000000000000000000000000"
    api_secret = "ERROR"
    api_passphrase = "00000000000"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase)
    assert str(execinfo.value) == 'Coinbase Pro API secret is invalid'

def test_instantiate_authapi_with_api_passphrase_error():
    api_key = "00000000000000000000000000000000"
    api_secret = "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000=="
    api_passphrase = "ERROR"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase)
    assert str(execinfo.value) == 'Coinbase Pro API passphrase is invalid'

def test_instantiate_authapi_with_api_url_error():
    api_key = "00000000000000000000000000000000"
    api_secret = "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000=="
    api_passphrase = "00000000000"
    api_url = "ERROR"

    with pytest.raises(ValueError) as execinfo:
        AuthAPI(api_key, api_secret, api_passphrase, api_url)
    assert str(execinfo.value) == 'Coinbase Pro API URL is invalid'

def test_instantiate_publicapi_without_error():
    exchange = PublicAPI()
    assert type(exchange) is PublicAPI