import ast
import json
import os.path
import re

from .default_parser import isCurrencyValid, defaultConfigParse, merge_config_and_args
from models.exchange.Granularity import Granularity


def isMarketValid(market) -> bool:
    p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
    return p.match(market) is not None

def parseMarket(market):
    if not isMarketValid(market):
        raise ValueError(f'Coinbase Pro market invalid: {market}')

    base_currency, quote_currency = market.split('-', 2)
    return market, base_currency, quote_currency

def parser(app, coinbase_config, args={}):
    #print('CoinbasePro Configuration parse')

    if not app:
        raise Exception('No app is passed')

    if isinstance(coinbase_config, dict):
        if 'api_key' in coinbase_config or 'api_secret' in coinbase_config or 'api_passphrase' in coinbase_config:
            print(f'>>> migrating api keys to coinbasepro.key <<<\n')

            # create 'coinbasepro.key'
            fh = open('coinbasepro.key', 'w')
            fh.write(f"{coinbase_config['api_key']}\n{coinbase_config['api_secret']}\n{coinbase_config['api_passphrase']}")
            fh.close()

            if os.path.isfile('config.json') and os.path.isfile('coinbasepro.key'):
                coinbase_config['api_key_file'] = coinbase_config.pop('api_key')
                coinbase_config['api_key_file'] = 'coinbasepro.key'
                del coinbase_config['api_secret']
                del coinbase_config['api_passphrase']

                # read 'coinbasepro' element from config.json
                fh = open('config.json', 'r')
                config_json = ast.literal_eval(fh.read())
                config_json['coinbasepro'] = coinbase_config
                fh.close()

                # write new 'coinbasepro' element
                fh = open('config.json', 'w')
                fh.write(json.dumps(config_json, indent=4))
                fh.close()

        api_key_file = None
        if 'api_key_file' in args and args['api_key_file'] is not None:
            api_key_file = args['api_key_file']
        elif 'api_key_file' in coinbase_config:
            api_key_file = coinbase_config['api_key_file']

        if api_key_file is not None:
            try :
                with open( api_key_file, 'r') as f :
                    key = f.readline().strip()
                    secret = f.readline().strip()
                    password = f.readline().strip()
                coinbase_config['api_key'] = key
                coinbase_config['api_secret'] = secret
                coinbase_config['api_passphrase'] = password
            except :
                raise RuntimeError(f"Unable to read {api_key_file}")

        if 'api_key' in coinbase_config and 'api_secret' in coinbase_config and \
                'api_passphrase' in coinbase_config and 'api_url' in coinbase_config:

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
            p = re.compile(r"^[A-z0-9#$%=@!{},`~&*()<>?.:;_|^/+\[\]]{8,32}$")
            if not p.match(coinbase_config['api_passphrase']):
                raise TypeError('Coinbase Pro API passphrase is invalid')

            app.api_passphrase = coinbase_config['api_passphrase']

            valid_urls = [
                'https://api.pro.coinbase.com/',
                'https://api.pro.coinbase.com',
                'https://public.sandbox.pro.coinbase.com',
                'https://public.sandbox.pro.coinbase.com/'
            ]

            # validate Coinbase Pro API
            if coinbase_config['api_url'] not in valid_urls:
                raise ValueError('Coinbase Pro API URL is invalid')

            app.api_url = coinbase_config['api_url']
    else:
        coinbase_config = {}

    config = merge_config_and_args(coinbase_config, args)

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

