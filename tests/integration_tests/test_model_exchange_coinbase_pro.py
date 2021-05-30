import json, pandas, pytest, os, sys, time
from datetime import datetime

sys.path.append('.')
# pylint: disable=import-error
from models.exchange.coinbase_pro import AuthAPI, PublicAPI
from models.helper.LogHelper import Logger
Logger.configure()

DEFAULT_ORDER_MARKET = 'BTC-GBP'

def getValidOrderMarket() -> str:
    filename = 'config.json'
    assert os.path.exists(filename) == True
    with open(filename) as config_file:
        config = json.load(config_file)

        if 'api_key' in config and 'api_secret' in config and ('api_pass' in config or 'api_passphrase' in config) and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            if 'api_pass' in config:
                api_passphrase = config['api_pass']
            else:
                api_passphrase = config['api_passphrase']
            api_url = config['api_url']
        elif 'coinbasepro' in config:
            if 'api_key' in config['coinbasepro'] and 'api_secret' in config['coinbasepro'] and 'api_passphrase' in config['coinbasepro'] and 'api_url' in config['coinbasepro']:
                api_key = config['coinbasepro']['api_key']
                api_secret = config['coinbasepro']['api_secret']
                api_passphrase = config['coinbasepro']['api_passphrase']
                api_url = config['coinbasepro']['api_url']
            else:
                return DEFAULT_ORDER_MARKET
        else:
            return DEFAULT_ORDER_MARKET

        time.sleep(0.5)
        exchange = AuthAPI(api_key, api_secret, api_passphrase, api_url)
        df = exchange.getOrders()
        if len(df) == 0:
            return DEFAULT_ORDER_MARKET

        return df['market'].tail(1).values[0]
    return DEFAULT_ORDER_MARKET

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

def test_getFeesWithoutMarket():
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

    df = exchange.getFees()
    assert type(df) is pandas.core.frame.DataFrame

    assert len(df) == 1

    actual = df.columns.to_list()
    expected = [ 'maker_fee_rate', 'taker_fee_rate', 'usd_volume', 'market' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_getFeesWithMarket():
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

    df = exchange.getFees(getValidOrderMarket())
    assert type(df) is pandas.core.frame.DataFrame

    assert len(df) == 1

    actual = df.columns.to_list()
    expected = [ 'maker_fee_rate', 'taker_fee_rate', 'usd_volume', 'market' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_getTakerFeeWithoutMarket():
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

    fee = exchange.getTakerFee()
    assert type(fee) is float
    assert fee > 0

def test_getTakerFeeWithMarket():
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

    fee = exchange.getTakerFee(getValidOrderMarket())
    assert type(fee) is float
    assert fee > 0

def test_getMakerFeeWithoutMarket():
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

    fee = exchange.getMakerFee()
    assert type(fee) is float
    assert fee > 0

def test_getMakerFeeWithMarket():
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

    fee = exchange.getMakerFee(getValidOrderMarket())
    assert type(fee) is float
    assert fee > 0

def test_getUSDVolume():
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

    fee = exchange.getUSDVolume()
    assert type(fee) is float
    assert fee > 0

def test_getOrders():
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

    df = exchange.getOrders()

    assert len(df) > 0

    actual = df.columns.to_list()
    expected = [ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_getOrdersInvalidMarket():
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

    with pytest.raises(ValueError) as execinfo:
        exchange.getOrders(market='ERROR')
    assert str(execinfo.value) == 'Coinbase Pro market is invalid.'

def test_getOrdersValidMarket():
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

    df = exchange.getOrders(market=getValidOrderMarket())

    assert len(df) > 0

    actual = df.columns.to_list()
    expected = [ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_getOrdersInvalidAction():
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

    with pytest.raises(ValueError) as execinfo:
        exchange.getOrders(action='ERROR')
    assert str(execinfo.value) == 'Invalid order action.'

def test_getOrdersValidActionBuy():
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

    df = exchange.getOrders(action='buy')

    assert len(df) >= 0

    actual = df.columns.to_list()
    expected = [ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_getOrdersValidActionSell():
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

    df = exchange.getOrders(action='sell')

    assert len(df) >= 0

    actual = df.columns.to_list()
    expected = [ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_getOrdersInvalidStatus():
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

    with pytest.raises(ValueError) as execinfo:
        exchange.getOrders(status='ERROR')
    assert str(execinfo.value) == 'Invalid order status.'

def test_getOrdersValidStatusAll():
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

    df = exchange.getOrders(status='all')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

def test_getOrdersValidStatusOpen():
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

    df = exchange.getOrders(status='open')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

def test_getOrdersValidStatusPending():
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

    df = exchange.getOrders(status='pending')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

def test_getOrdersValidStatusDone():
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

    df = exchange.getOrders(status='done')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

def test_getOrdersValidStatusActive():
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

    df = exchange.getOrders(status='active')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

def test_getTime():
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
    
    resp = exchange.getTime()
    assert type(resp) is datetime

def test_marketBuyInvalidMarket():
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

    with pytest.raises(ValueError) as execinfo:
        exchange.marketBuy('ERROR', -1)
    assert str(execinfo.value) == 'Coinbase Pro market is invalid.'  

def test_marketBuyInvalidAmount():
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

    with pytest.raises(ValueError) as execinfo:
        exchange.marketBuy('XXX-YYY', 0)
    assert str(execinfo.value) == 'Trade amount is too small (>= 10).'  