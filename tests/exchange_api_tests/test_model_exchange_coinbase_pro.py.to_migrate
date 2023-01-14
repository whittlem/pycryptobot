import json, pandas, pytest, os, sys, time
from datetime import datetime

sys.path.append('.')
# pylint: disable=import-error
from models.exchange.coinbase_pro import AuthAPI, PublicAPI

DEFAULT_ORDER_MARKET = 'BTC-GBP'

def get_valid_order_market() -> str:
    filename = 'config.json'
    assert os.path.exists(filename) is True
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
        df = exchange.get_orders()
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
    assert os.path.exists(filename) is True
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

def test_get_accounts():
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

    df = exchange.get_accounts()
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

    df = exchange.get_accounts()

    assert len(df) > 0

    account = df[['id']].head(1).values[0][0]
    assert len(account) > 0

    df = exchange.get_account(account)
    assert type(df) is pandas.core.frame.DataFrame

    assert len(df) == 1

    actual = df.columns.to_list()
    expected = [ 'id', 'currency', 'balance', 'hold', 'available', 'profile_id', 'trading_enabled' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_get_fees_without_market():
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

    df = exchange.get_fees()
    assert type(df) is pandas.core.frame.DataFrame

    assert len(df) == 1

    actual = df.columns.to_list()
    expected = [ 'maker_fee_rate', 'taker_fee_rate', 'usd_volume', 'market' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_get_fees_with_market():
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

    df = exchange.get_fees(get_valid_order_market())
    assert type(df) is pandas.core.frame.DataFrame

    assert len(df) == 1

    actual = df.columns.to_list()
    expected = [ 'maker_fee_rate', 'taker_fee_rate', 'usd_volume', 'market' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_get_taker_fee_without_market():
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

    fee = exchange.get_taker_fee()
    assert type(fee) is float
    assert fee > 0

def test_get_taker_fee_with_market():
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

    fee = exchange.get_taker_fee(get_valid_order_market())
    assert type(fee) is float
    assert fee > 0

def test_get_maker_fee_without_market():
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

    fee = exchange.get_maker_fee()
    assert type(fee) is float
    assert fee > 0

def test_get_maker_fee_with_market():
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

    fee = exchange.get_maker_fee(get_valid_order_market())
    assert type(fee) is float
    assert fee > 0

def test_get_usd_volume():
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

    fee = exchange.get_usd_volume()
    assert type(fee) is float
    assert fee > 0

def test_get_orders():
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

    df = exchange.get_orders()

    assert len(df) > 0

    actual = df.columns.to_list()
    expected = [ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_get_ordersInvalidMarket():
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
        exchange.get_orders(market='ERROR')
    assert str(execinfo.value) == 'Coinbase Pro market is invalid.'

def test_get_orders_valid_market():
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

    df = exchange.get_orders(market=get_valid_order_market())

    assert len(df) > 0

    actual = df.columns.to_list()
    expected = [ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_get_orders_invalid_action():
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
        exchange.get_orders(action='ERROR')
    assert str(execinfo.value) == 'Invalid order action.'

def test_get_orders_valid_action_buy():
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

    df = exchange.get_orders(action='buy')

    assert len(df) >= 0

    actual = df.columns.to_list()
    expected = [ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_get_orders_valid_action_sell():
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

    df = exchange.get_orders(action='sell')

    assert len(df) >= 0

    actual = df.columns.to_list()
    expected = [ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_get_orders_invalid_status():
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
        exchange.get_orders(status='ERROR')
    assert str(execinfo.value) == 'Invalid order status.'

def test_get_orders_valid_status_all():
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

    df = exchange.get_orders(status='all')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

def test_get_orders_valid_status_open():
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

    df = exchange.get_orders(status='open')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

def test_get_orders_valid_status_pending():
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

    df = exchange.get_orders(status='pending')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

def test_get_orders_valid_status_done():
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

    df = exchange.get_orders(status='done')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

def test_get_orders_valid_status_active():
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

    df = exchange.get_orders(status='active')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price' ]
        assert len(actual) == len(expected)
        assert all([a == b for a, b in zip(actual, expected)])

def test_get_time():
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

    resp = exchange.get_time()
    assert type(resp) is datetime

def test_market_buy_invalid_market():
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
        exchange.market_buy('ERROR', -1)
    assert str(execinfo.value) == 'Coinbase Pro market is invalid.'

def test_market_buy_invalid_amount():
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
        exchange.market_buy('XXX-YYY', 0)
    assert str(execinfo.value) == 'Trade amount is too small (>= 10).'
