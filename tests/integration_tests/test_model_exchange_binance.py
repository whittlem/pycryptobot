import json, pandas, pytest, os, sys, urllib3
from datetime import datetime
# disable insecure ssl warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('.')
# pylint: disable=import-error
from models.exchange.binance import AuthAPI, PublicAPI


# there is no dynamic way of retrieving a valid order market
VALID_ORDER_MARKET = 'DOGEUSDT'

def test_instantiate_authapi_without_error():
    api_key = "0000000000000000000000000000000000000000000000000000000000000000"
    api_secret = "0000000000000000000000000000000000000000000000000000000000000000"
    exchange = AuthAPI(api_key, api_secret)
    assert type(exchange) is AuthAPI

def test_instantiate_authapi_with_api_key_error():
    api_key = "ERROR"
    api_secret = "0000000000000000000000000000000000000000000000000000000000000000"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret)
    assert str(execinfo.value) == 'Binance API key is invalid'

def test_instantiate_authapi_with_api_secret_error():
    api_key = "0000000000000000000000000000000000000000000000000000000000000000"
    api_secret = "ERROR"

    with pytest.raises(SystemExit) as execinfo:
        AuthAPI(api_key, api_secret)
    assert str(execinfo.value) == 'Binance API secret is invalid'

def test_instantiate_authapi_with_api_url_error():
    api_key = "0000000000000000000000000000000000000000000000000000000000000000"
    api_secret = "0000000000000000000000000000000000000000000000000000000000000000"
    api_url = "ERROR"

    with pytest.raises(ValueError) as execinfo:
        AuthAPI(api_key, api_secret, api_url)
    assert str(execinfo.value) == 'Binance API URL is invalid'

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
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

def test_getAccount():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.get_account()
    assert type(df) is pandas.core.frame.DataFrame

    actual = df.columns.to_list()
    expected = ['currency', 'balance', 'hold', 'available']
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_get_fees_without_market():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.get_fees()
    assert type(df) is pandas.core.frame.DataFrame

    assert len(df) > 1

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
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.get_fees(VALID_ORDER_MARKET)
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
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    fees = exchange.get_taker_fee()
    assert type(fees) is pandas.core.frame.DataFrame
    assert len(fees) > 0

def test_get_taker_fee_with_market():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    fee = exchange.get_taker_fee(VALID_ORDER_MARKET)
    assert type(fee) is float
    assert fee > 0

def test_get_maker_fee_without_market():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    fees = exchange.get_maker_fee()
    assert type(fees) is pandas.core.frame.DataFrame
    assert len(fees) > 0

def test_get_maker_fee_with_market():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    fee = exchange.get_maker_fee(VALID_ORDER_MARKET)
    assert type(fee) is float
    assert fee > 0

def test_get_orders():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.get_orders(VALID_ORDER_MARKET)

    assert len(df) > 0

    actual = df.columns.to_list()
    expected = ['created_at', 'market', 'action', 'type', 'size', 'filled', 'status', 'price']
    #  order is not important, but no duplicate
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff

def test_get_ordersInvalidMarket():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    with pytest.raises(ValueError) as execinfo:
        exchange.get_orders(market='ERROR')
    assert str(execinfo.value) == 'Binance market is invalid.'

def test_get_orders_valid_market():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.get_orders(market=VALID_ORDER_MARKET)

    assert len(df) > 0

    actual = df.columns.to_list()
    expected = ['created_at', 'market', 'action', 'type', 'size', 'filled', 'status', 'price']
    #  order is not important, but no duplicate
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff

def test_get_orders_invalid_action():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
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
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.get_orders(market=VALID_ORDER_MARKET, action='buy')

    assert len(df) >= 0

    actual = df.columns.to_list()
    expected = ['created_at', 'market', 'action', 'type', 'size', 'filled', 'status', 'price']
    #  order is not important, but no duplicate
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff

def test_get_orders_valid_action_sell():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.get_orders(market=VALID_ORDER_MARKET, action='sell')

    assert len(df) >= 0

    actual = df.columns.to_list()
    expected = ['created_at', 'market', 'action', 'type', 'size', 'filled', 'status', 'price']
    #  order is not important, but no duplicate
    assert len(actual) == len(expected)
    diff = set(actual) ^ set(expected)
    assert not diff

def test_get_orders_invalid_status():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
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
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.get_orders(market=VALID_ORDER_MARKET, status='all')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = ['created_at', 'market', 'action', 'type', 'size', 'filled', 'status', 'price']
        #  order is not important, but no duplicate
        assert len(actual) == len(expected)
        diff = set(actual) ^ set(expected)
        assert not diff

def test_get_orders_valid_status_open():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.get_orders(market=VALID_ORDER_MARKET, status='open')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = ['created_at', 'market', 'action', 'type', 'size', 'filled', 'status', 'price']
        #  order is not important, but no duplicate
        assert len(actual) == len(expected)
        diff = set(actual) ^ set(expected)
        assert not diff

def test_get_orders_valid_status_pending():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.get_orders(market=VALID_ORDER_MARKET, status='pending')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = ['created_at', 'market', 'action', 'type', 'size', 'filled', 'status', 'price']
        #  order is not important, but no duplicate
        assert len(actual) == len(expected)
        diff = set(actual) ^ set(expected)
        assert not diff

def test_get_orders_valid_status_done():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.get_orders(market=VALID_ORDER_MARKET, status='done')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = ['created_at', 'market', 'action', 'type', 'size', 'filled', 'status', 'price']
        #  order is not important, but no duplicate
        assert len(actual) == len(expected)
        diff = set(actual) ^ set(expected)
        assert not diff

def test_get_orders_valid_status_active():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    df = exchange.get_orders(market=VALID_ORDER_MARKET, status='active')

    if len(df) == 0:
        pass
    else:
        actual = df.columns.to_list()
        expected = ['created_at', 'market', 'action', 'type', 'size', 'filled', 'status', 'price']
        #  order is not important, but no duplicate
        assert len(actual) == len(expected)
        diff = set(actual) ^ set(expected)
        assert not diff

def test_get_time():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    resp = exchange.get_time()
    assert type(resp) is datetime

def test_market_buy_invalid_market():
    filename = 'config.json'

    with open(filename) as config_file:
        config = json.load(config_file)

        api_key = ''
        api_secret = ''
        api_url = ''
        if 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
            api_key = config['api_key']
            api_secret = config['api_secret']
            api_url = config['api_url']
            AuthAPI(api_key, api_secret, api_url)
        elif 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            api_url = config['binance']['api_url']
            AuthAPI(api_key, api_secret, api_url)

    exchange = AuthAPI(api_key, api_secret, api_url)
    assert type(exchange) is AuthAPI

    with pytest.raises(ValueError) as execinfo:
        exchange.market_buy('ERROR', -1)
    assert str(execinfo.value) == 'Binance market is invalid.'