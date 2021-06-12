import re

from .default_parser import isCurrencyValid, defaultConfigParse, merge_config_and_args

def isMarketValid(market) -> bool:
    if market == None:
        return False
    p = re.compile(r"^[0-9A-Z]{5,12}$")
    return p.match(market) is not None


def to_internal_granularity(granularity: str) -> int:
    return {'1m': 60, '5m': 300, '15m': 900, '1h': 3600, '6h': 21600, '1d': 86400}[granularity]


def parseMarket(market):
    base_currency = 'BTC'
    quote_currency = 'GBP'

    if not isMarketValid(market):
        raise ValueError('Binance market invalid: ' + market)

    quote_currencies = [
        'BTC', 'BNB', 'ETH', 'USDT', 'TUSD', 'BUSD', 'DAX', 'NGN', 'RUB', 'TRY', 'EUR',
        'GBP', 'ZAR', 'UAH', 'DAI', 'BIDR', 'AUD', 'US', 'NGN', 'BRL', 'BVND', 'VAI'
    ]

    for qc in quote_currencies:
        if market.endswith( qc ):
            base_currency = market.replace(qc, '')
            quote_currency = qc
            break

    if len(market) != len(base_currency) + len(quote_currency):
        raise ValueError('Binance market error.')

    return market, base_currency, quote_currency


def parser(app, binance_config, args={}):
    #print('Binance Configuration parse')

    if not binance_config:
        raise Exception('There is an error in your config dictionnary')

    if not app:
        raise Exception('No app is passed')

    if 'api_key' in binance_config and 'api_secret' in binance_config and 'api_url' in binance_config:
        # validates the api key is syntactically correct
        p = re.compile(r"^[A-z0-9]{64,64}$")
        if not p.match(binance_config['api_key']):
            raise TypeError('Binance API key is invalid')

        app.api_key = binance_config['api_key']

        # validates the api secret is syntactically correct
        p = re.compile(r"^[A-z0-9]{64,64}$")
        if not p.match(binance_config['api_secret']):
            raise TypeError('Binance API secret is invalid')

        app.api_secret = binance_config['api_secret']

        valid_urls = [
            'https://api.binance.com/',
            'https://testnet.binance.vision/api/',
            'https://api.binance.com',
            'https://testnet.binance.vision/api',
            'https://api.binance.us',
        ]

        # validate Binance API
        if binance_config['api_url'] not in valid_urls:
            raise ValueError('Binance API URL is invalid')

        app.api_url = binance_config['api_url']
        app.base_currency = 'BTC'
        app.quote_currency = 'GBP'

        config = merge_config_and_args(binance_config, args)

        defaultConfigParse(app, config)

        if 'base_currency' in config and config['base_currency'] is not None:
            if not isCurrencyValid(config['base_currency']):
                raise TypeError('Base currency is invalid.')
            app.base_currency = config['base_currency']

        if 'quote_currency' in config and config['quote_currency'] is not None:
            if not isCurrencyValid(config['quote_currency']):
                raise TypeError('Quote currency is invalid.')
            app.quote_currency = config['quote_currency']

        if 'market' in config and config['market'] is not None:
            app.market, app.base_currency, app.quote_currency = parseMarket(config['market'])

        if app.base_currency != '' and app.quote_currency != '':
            app.market = app.base_currency + app.quote_currency

        if 'granularity' in config and config['granularity'] is not None:
            if isinstance(config['granularity'], str):
                if config['granularity'] in ['1m', '5m', '15m', '1h', '6h', '1d']:
                    app.granularity = to_internal_granularity(config['granularity'])
                    app.smart_switch = 0

    else:
        raise Exception('There is an error in your config dictionary')
