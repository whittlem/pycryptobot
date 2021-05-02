import json, pandas, pytest, os, sys

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

def test_config_json_exists_and_valid():
    filename = 'config.json'
    assert os.path.exists(filename) == True
    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_passphrase = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_passphrase = config['api_pass']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_passphrase, api_url)
        elif 'api_key' in config['coinbasepro'] and 'api_secret' in config['coinbasepro'] and 'api_passphrase' in config['coinbasepro'] and 'api_url' in config['coinbasepro']:
            api_key = config['coinbasepro']['api_key']
            api_secret = config['coinbasepro']['api_secret']
            api_passphrase = config['coinbasepro']['api_passphrase']
            api_url = config['coinbasepro']['api_url']
            AuthAPI(api_key, api_secret, api_passphrase, api_url)
    pass

def test_getAccounts():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_passphrase = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_passphrase = config['api_pass']
            api_url = config['api_url']
            
        elif 'api_key' in config['coinbasepro'] and 'api_secret' in config['coinbasepro'] and 'api_passphrase' in config['coinbasepro'] and 'api_url' in config['coinbasepro']:
            api_key = config['coinbasepro']['api_key']
            api_secret = config['coinbasepro']['api_secret']
            api_passphrase = config['coinbasepro']['api_passphrase']
            api_url = config['coinbasepro']['api_url']

    exchange = AuthAPI(api_key, api_secret, api_passphrase, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.getAccounts()
    assert type(df) is pandas.core.frame.DataFrame

    actual = df.columns.to_list()
    expected = [ 'index', 'id', 'currency', 'balance', 'hold', 'available', 'profile_id', 'trading_enabled' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_getAccount():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_passphrase = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_passphrase = config['api_pass']
            api_url = config['api_url']
            
        elif 'api_key' in config['coinbasepro'] and 'api_secret' in config['coinbasepro'] and 'api_passphrase' in config['coinbasepro'] and 'api_url' in config['coinbasepro']:
            api_key = config['coinbasepro']['api_key']
            api_secret = config['coinbasepro']['api_secret']
            api_passphrase = config['coinbasepro']['api_passphrase']
            api_url = config['coinbasepro']['api_url']

    exchange = AuthAPI(api_key, api_secret, api_passphrase, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.getAccounts()

    assert len(df) > 0

    account = df[['id']].head(1).values[0][0]
    assert len(account) > 0

    df = exchange.getAccount(account)
    assert type(df) is pandas.core.frame.DataFrame

    assert len(df) == 1

    actual = df.columns.to_list()
    expected = [ 'id', 'currency', 'balance', 'hold', 'available', 'profile_id', 'trading_enabled' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])