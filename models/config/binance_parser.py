import re, logging

from .default_parser import isCurrencyValid, defaultConfigParse, merge_config_and_args

def isMarketValid(market):
    if market == None:
        return False
    p = re.compile(r"^[0-9A-Z]{6,12}$")
    return p.match(market)

def parseMarket(market):
    base_currency = 'BTC'
    quote_currency = 'GBP'

    if not isMarketValid(market):
        raise ValueError('Binance market invalid: ' + market)

    if market.endswith('BTC'):
        base_currency = market.replace('BTC', '')
        quote_currency = 'BTC'
    elif market.endswith('BNB'):
        base_currency = market.replace('BNB', '')
        quote_currency = 'BNB'
    elif market.endswith('ETH'):
        base_currency = market.replace('ETH', '')
        quote_currency = 'ETH'
    elif market.endswith('USDT'):
        base_currency = market.replace('USDT', '')
        quote_currency = 'USDT'
    elif market.endswith('TUSD'):
        base_currency = market.replace('TUSD', '')
        quote_currency = 'TUSD'
    elif market.endswith('BUSD'):
        base_currency = market.replace('BUSD', '')
        quote_currency = 'BUSD'
    elif market.endswith('DAX'):
        base_currency = market.replace('DAX', '')
        quote_currency = 'DAX'
    elif market.endswith('NGN'):
        base_currency = market.replace('NGN', '')
        quote_currency = 'NGN'
    elif market.endswith('RUB'):
        base_currency = market.replace('RUB', '')
        quote_currency = 'RUB'
    elif market.endswith('TRY'):
        base_currency = market.replace('TRY', '')
        quote_currency = 'TRY'
    elif market.endswith('EUR'):
        base_currency = market.replace('EUR', '')
        quote_currency = 'EUR'
    elif market.endswith('GBP'):
        base_currency = market.replace('GBP', '')
        quote_currency = 'GBP'
    elif market.endswith('ZAR'):
        base_currency = market.replace('ZAR', '')
        quote_currency = 'ZAR'
    elif market.endswith('UAH'):
        base_currency = market.replace('UAH', '')
        quote_currency = 'UAH'
    elif market.endswith('DAI'):
        base_currency = market.replace('DAI', '')
        quote_currency = 'DAI'
    elif market.endswith('BIDR'):
        base_currency = market.replace('BIDR', '')
        quote_currency = 'BIDR'
    elif market.endswith('AUD'):
        base_currency = market.replace('AUD', '')
        quote_currency = 'AUD'
    elif market.endswith('US'):
        base_currency = market.replace('US', '')
        quote_currency = 'US'
    elif market.endswith('NGN'):
        base_currency = market.replace('NGN', '')
        quote_currency = 'NGN'
    elif market.endswith('BRL'):
        base_currency = market.replace('BRL', '')
        quote_currency = 'BRL'
    elif market.endswith('BVND'):
        base_currency = market.replace('BVND', '')
        quote_currency = 'BVND'
    elif market.endswith('VAI'):
        base_currency = market.replace('VAI', '')
        quote_currency = 'VAI'

    if len(market) != len(base_currency) + len(quote_currency):
        raise ValueError('Binance market error.')

    return market, base_currency, quote_currency

def parser(app, binance_config, args = {}):
    logging.info('Binance Configuration parse')

    app.granularity = '1h'

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
            'https://testnet.binance.vision/api'
        ]

        # validate Binance API
        if binance_config['api_url'] not in valid_urls:
            raise ValueError('Binance API URL is invalid')

        app.api_url = binance_config['api_url']
        app.base_currency = 'BTC'
        app.quote_currency = 'GBP'
        app.granularity = '1h'

        config = merge_config_and_args(binance_config, args)

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
            app.market = app.base_currency + app.quote_currency

        if 'granularity' in config and config['granularity'] != None:
            if isinstance(config['granularity'], str):
                if config['granularity'] in ['1m', '5m', '15m', '1h', '6h', '1d']:
                    app.granularity = config['granularity']
                    app.smart_switch = 0

    else:
        raise Exception('There is an error in your config dictionnary')
