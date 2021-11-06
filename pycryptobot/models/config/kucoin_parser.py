import re
import ast
import json
import os.path
import sys

from .default_parser import isCurrencyValid, defaultConfigParse, merge_config_and_args

def isMarketValid(market) -> bool:
    p = re.compile(r"^[1-9A-Z]{2,5}\-[1-9A-Z]{2,5}$")
    return p.match(market) is not None

def to_internal_granularity(granularity: str) -> int:
    return {'1min': 60, '5min': 300, '15min': 900, '1hour': 3600, '6hour': 21600, '1day': 86400}[granularity]

def parseMarket(market):
    if not isMarketValid(market):
        raise ValueError('Kucoin market invalid: ' + market)

    base_currency, quote_currency = market.split('-', 2)
    return market, base_currency, quote_currency

def parser(app, Kucoin_config, args={}):
    #print('Kucoin Configuration parse')

    if not app:
        raise Exception('No app is passed')

    if isinstance(Kucoin_config, dict):
        if 'api_key' in Kucoin_config or 'api_secret' in Kucoin_config:
            print('>>> migrating api keys to Kucoin.key <<<', "\n")

            # create 'Kucoin.key'
            fh = open('Kucoin.key', 'w')
            fh.write(Kucoin_config['api_key'] + "\n" + Kucoin_config['api_secret'])
            fh.close()

            if os.path.isfile('config.json') and os.path.isfile('Kucoin.key'):
                Kucoin_config['api_key_file'] = Kucoin_config.pop('api_key')
                Kucoin_config['api_key_file'] = 'Kucoin.key'
                Kucoin_config['api_secret']

                # read 'Kucoin' element from config.json
                fh = open('config.json', 'r')
                config_json = ast.literal_eval(fh.read())
                config_json['kucoin'] = Kucoin_config
                fh.close()

                # write new 'Kucoin' element
                fh = open('config.json', 'w')
                fh.write(json.dumps(config_json, indent=4))
                fh.close()
            else:
                print ('migration failed (io error)', "\n")

        if 'api_key_file' in Kucoin_config:
            try :
                with open( Kucoin_config['api_key_file'], 'r') as f :
                    key = f.readline().strip()
                    secret = f.readline().strip()
                    password = f.readline().strip()
                Kucoin_config['api_key'] = key
                Kucoin_config['api_secret'] = secret
                Kucoin_config['api_passphrase'] = password
            except :
                raise RuntimeError('Unable to read ' + Kucoin_config['api_key_file'])

        if 'api_key' in Kucoin_config and 'api_secret' in Kucoin_config and \
                'api_passphrase' in Kucoin_config and 'api_url' in Kucoin_config:
            # validates the api key is syntactically correct
            p = re.compile(r"^[A-z0-9]{24,24}$")
            if not p.match(Kucoin_config['api_key']):
                raise TypeError('Kucoin API key is invalid')

            app.api_key = Kucoin_config['api_key']

            # validates the api secret is syntactically correct
            p = re.compile(r"^[A-z0-9-]{36,36}$")
            if not p.match(Kucoin_config['api_secret']):
                raise TypeError('Kucoin API secret is invalid')

            app.api_secret = Kucoin_config['api_secret']

            # validates the api passphrase is syntactically correct
            p = re.compile(r"^[A-z0-9#$%=@!{},`~&*()<>?.:;_|^/+\[\]]{8,32}$")
            if not p.match(Kucoin_config['api_passphrase']):
                raise TypeError('Kucoin API passphrase is invalid')

            app.api_passphrase = Kucoin_config['api_passphrase']

            valid_urls = [
                'https://api.kucoin.com/',
                'https://api.kucoin.com',
                'https://openapi-sandbox.kucoin.com/',
                'https://openapi-sandbox.kucoin.com',
            ]

            # validate Kucoin API
            if Kucoin_config['api_url'] not in valid_urls:
                raise ValueError('Kucoin API URL is invalid')

            app.api_url = Kucoin_config['api_url']
            app.base_currency = 'BTC'
            app.quote_currency = 'GBP'
    else:
        Kucoin_config = {}

    config = merge_config_and_args(Kucoin_config, args)

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
        app.market = app.base_currency + '-' + app.quote_currency

    if 'granularity' in config and config['granularity'] is not None:
        if isinstance(config['granularity'], str):
            if config['granularity'] in ['1min', '5min', '15min', '1hour', '6hour', '1day']:
                app.granularity = to_internal_granularity(config['granularity'])
                app.smart_switch = 0
            else:
                app.granularity = int(config['granularity'])
                app.smart_switch = 0
            # else:
            #     raise ValueError('granularity supplied is not supported.')