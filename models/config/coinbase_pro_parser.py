import re, logging

from .default_parser import isCurrencyValid, defaultConfigParse, merge_config_and_args

def isMarketValid(market):
    p = re.compile(r"^[1-9A-Z]{2,5}\-[1-9A-Z]{2,5}$")
    return p.match(market)

def parseMarket(market):
    if not isMarketValid(market):
        raise ValueError('Coinbase Pro market invalid: ' + market)

    base_currency, quote_currency = market.split('-',  2)
    return market, base_currency, quote_currency

def parser(app, coinbase_config, args = {}):
    logging.info('CoinbasePro Configuration parse')

    app.granularity = 3600

    if not coinbase_config:
        raise Exception('There is an error in your config dictionnary')
    
    if not app:
        raise Exception('No app is passed')

    if 'api_key' in coinbase_config and 'api_secret' in coinbase_config and 'api_passphrase' in coinbase_config and 'api_url' in coinbase_config:

        # validates the api key is syntactically correct
        p = re.compile(r"^[a-f0-9]{32}$")
        if not p.match(coinbase_config['api_key']):
            raise TypeError('Coinbase Pro API key is invalid')

        app.api_key = coinbase_config['api_key']

        # validates the api secret is syntactically correct
        p = re.compile(r"^[A-z0-9+\/]+==$")
        if not p.match(coinbase_config['api_secret']):
            raise TypeError('Coinbase Pro API secret is invalid')

        app.api_secret = coinbase_config['api_secret']

        # validates the api passphrase is syntactically correct
        p = re.compile(r"^[a-z0-9]{10,11}$")
        if not p.match(coinbase_config['api_passphrase']):
            raise TypeError('Coinbase Pro API passphrase is invalid')

        app.api_passphrase = coinbase_config['api_passphrase']

        valid_urls = [
            'https://api.pro.coinbase.com/',
            'https://api.pro.coinbase.com'
        ]

        # validate Coinbase Pro API
        if coinbase_config['api_url'] not in valid_urls:
            raise ValueError('Coinbase Pro API URL is invalid')

        app.api_url = coinbase_config['api_url']

        config = merge_config_and_args(coinbase_config, args)

        defaultConfigParse(app, config)

        if 'base_currency' in config and config['base_currency'] != None:
            if not isCurrencyValid(config['base_currency']):
                raise TypeError('Base currency is invalid.')
            app.base_currency = config['base_currency']

        if 'quote_currency' in config and config['quote_currency'] != None:
            if not isCurrencyValid(config['quote_currency']):
                raise TypeError('Quote currency is invalid.')
            app.quote_currency = config['quote_currency']

        if 'market' in config and config['market'] != None:
            app.market, app.base_currency, app.quote_currency = parseMarket(config['market'])

        if app.base_currency != '' and app.quote_currency != '':
            app.market = app.base_currency + '-' + app.quote_currency

        if 'granularity' in config and config['granularity'] != None:
            granularity = 0
            if isinstance(config['granularity'], str) and config['granularity'].isnumeric() is True:
                granularity = int(config['granularity'])
            elif isinstance(config['granularity'], int):
                granularity = config['granularity']

            if granularity in [60, 300, 900, 3600, 21600, 86400]:
                app.granularity = config['granularity']
                app.smart_switch = 0


    else:
        raise Exception('There is an error in your config dictionnary')
