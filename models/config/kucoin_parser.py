import re
import ast
import json
import os.path
import sys

from .default_parser import isCurrencyValid, defaultConfigParse, merge_config_and_args
from models.exchange.Granularity import Granularity

def isMarketValid(market) -> bool:
    p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
    return p.match(market) is not None

def parseMarket(market):
    if not isMarketValid(market):
        raise ValueError('Kucoin market invalid: ' + market)

    base_currency, quote_currency = market.split('-', 2)
    return market, base_currency, quote_currency

def parser(app, kucoin_config, args={}):
    #print('Kucoin Configuration parse')

    if not app:
        raise Exception('No app is passed')

    if isinstance(kucoin_config, dict):
        if 'api_key' in kucoin_config or 'api_secret' in kucoin_config or 'api_passphrase' in kucoin_config:
            print('>>> migrating api keys to kucoin.key <<<', "\n")

            # create 'kucoin.key'
            fh = open('kucoin.key', 'w', encoding='utf8')
            fh.write(kucoin_config['api_key'] + "\n" + kucoin_config['api_secret'] + "\n" + kucoin_config['api_passphrase'])
            fh.close()

            if os.path.isfile('config.json') and os.path.isfile('kucoin.key'):
                kucoin_config['api_key_file'] = kucoin_config.pop('api_key')
                kucoin_config['api_key_file'] = 'kucoin.key'
                del kucoin_config['api_secret']
                del kucoin_config['api_passphrase']

                # read 'Kucoin' element from config.json
                fh = open('config.json', 'r', encoding='utf8')
                config_json = ast.literal_eval(fh.read())
                config_json['kucoin'] = kucoin_config
                fh.close()

                # write new 'Kucoin' element
                fh = open('config.json', 'w')
                fh.write(json.dumps(config_json, indent=4))
                fh.close()
            else:
                print ('migration failed (io error)', "\n")

        api_key_file = None
        if 'api_key_file' in args and args['api_key_file'] is not None:
            api_key_file = args['api_key_file']
        elif 'api_key_file' in kucoin_config:
            api_key_file = kucoin_config['api_key_file']

        if api_key_file is not None:
            try :
                with open( api_key_file, 'r') as f :
                    key = f.readline().strip()
                    secret = f.readline().strip()
                    password = f.readline().strip()
                kucoin_config['api_key'] = key
                kucoin_config['api_secret'] = secret
                kucoin_config['api_passphrase'] = password
            except :
                raise RuntimeError(f"Unable to read {api_key_file}")

        if 'api_key' in kucoin_config and 'api_secret' in kucoin_config and \
                'api_passphrase' in kucoin_config and 'api_url' in kucoin_config:
            # validates the api key is syntactically correct
            p = re.compile(r"^[A-z0-9]{24,24}$")
            if not p.match(kucoin_config['api_key']):
                raise TypeError('Kucoin API key is invalid')

            app.api_key = kucoin_config['api_key']

            # validates the api secret is syntactically correct
            p = re.compile(r"^[A-z0-9-]{36,36}$")
            if not p.match(kucoin_config['api_secret']):
                raise TypeError('Kucoin API secret is invalid')

            app.api_secret = kucoin_config['api_secret']

            # validates the api passphrase is syntactically correct
            p = re.compile(r"^[A-z0-9#$%=@!{},`~&*()<>?.:;_|^/+\[\]]{8,32}$")
            if not p.match(kucoin_config['api_passphrase']):
                raise TypeError('Kucoin API passphrase is invalid')

            app.api_passphrase = kucoin_config['api_passphrase']

            valid_urls = [
                'https://api.kucoin.com/',
                'https://api.kucoin.com',
                'https://openapi-sandbox.kucoin.com/',
                'https://openapi-sandbox.kucoin.com',
            ]

            # validate Kucoin API
            if kucoin_config['api_url'] not in valid_urls:
                raise ValueError('Kucoin API URL is invalid')

            app.api_url = kucoin_config['api_url']
            app.base_currency = 'BTC'
            app.quote_currency = 'GBP'
    else:
        kucoin_config = {}

    config = merge_config_and_args(kucoin_config, args)

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
        if isinstance(config['granularity'], str) and config['granularity'].isnumeric() is True:
            app.granularity = Granularity.convert_to_enum(int(config['granularity']))
        elif isinstance(config['granularity'], int):
            app.granularity = Granularity.convert_to_enum(config['granularity'])
