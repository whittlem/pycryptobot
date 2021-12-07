import asyncio
import os
import re
from itertools import product
from typing import Iterable
from jinja2 import Template
from models.PyCryptoBot import PyCryptoBot
from models.exchange.binance import PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import PublicAPI as CPublicAPI
from models.exchange.kucoin import PublicAPI as KPublicAPI
from models.exchange.ExchangesEnum import Exchange as CryptoExchange
from numpy import arange, array, around
from pathlib import Path


# constant config values
buymaxsize = 1000
live = 0
sellatloss = 0
sellatresistance = 0
disablebullonly = 1
disablelog = 1
websocket = 1
autorestart = 1
disablecleanfilesonexit = 1
enableinsufficientfundslogging = 1

config_iterables = {'nosellminpcnt': [],
             'nosellmaxpcnt': [],
             'trailingstoploss': [],
             'trailingstoplosstrigger': []}

config_binaries = {'disablebuyelderray': [0,1],
            'disablebuyema': [0,1],
            'disablebuyobv': [0,1],
            'disablefailsafefibonacci': [0,1],
            'disableprofitbankreversal': [0,1]}


def bootstrap(exchange):
    if exchange == CryptoExchange.BINANCE.value:
        app = PyCryptoBot(exchange=exchange)
        app.public_api = BPublicAPI()
    elif exchange == CryptoExchange.COINBASEPRO.value:
        app = PyCryptoBot(exchange=exchange)
        app.public_api = CPublicAPI()
    elif exchange == CryptoExchange.KUCOIN.value:
        app = PyCryptoBot(exchange=exchange)
        app.public_api = KPublicAPI()
    else:
        raise ValueError('Not supported!')

    return app

def populate_markets(app, quote_currency):
    market_pairs = []
    quote_currency = quote_currency.upper()
    currency_match = re.compile(f"^(\w+).({quote_currency}$)")
    resp = app.public_api.getMarkets24HrStats()
    if app.exchange == CryptoExchange.BINANCE:
        for row in resp:
            market = row['symbol']
            match_result = currency_match.search(market)
            if match_result:
                market_pairs.append((match_result.groups()[0],
                                    match_result.groups()[1]))
    elif app.exchange == CryptoExchange.COINBASEPRO:
        for market in resp:
            market = str(market)
            match_result = currency_match.search(market)
            if match_result:
                market_pairs.append((match_result.groups()[0],
                                    match_result.groups()[1]))
    elif app.exchange == CryptoExchange.KUCOIN:
        results = resp["data"]["ticker"]
        for result in results:
            market = result['symbol']
            match_result = currency_match.search(market)
            if match_result:
                market_pairs.append((match_result.groups()[0],
                                    match_result.groups()[1]))

    return market_pairs

async def write_config(**kwargs):
    templatepath = Path(f"{kwargs['template']}")
    with templatepath.open('r') as t:
        template = Template(t.read())
        output_from_parsed_template = template.render(**kwargs)
    
    filepath = \
        Path(
            f"{kwargs['destination']}/{kwargs['base_currency']}-{kwargs['quote_currency']}/" + \
            f"/noema{kwargs['disablebuyema']}-noelder{kwargs['disablebuyelderray']}-nofib{kwargs['disablefailsafefibonacci']}-nobank{kwargs['disableprofitbankreversal']}-noobv{kwargs['disablebuyobv']}/" + \
                f"tslt{kwargs['tslt']}-tsl{kwargs['tsl']}-nsmax{kwargs['nsmax']}-nsmin{kwargs['nsmin']}.json")
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with filepath.open("w", encoding ="utf-8") as f:
        f.write(output_from_parsed_template)

    return True

async def gen_binary_config_perms(binary_configs):
    list_of_dicts = [dict(zip(binary_configs, v)) for v in product(*binary_configs.values())]

    return list_of_dicts

async def get_iterables_permutations(possible_iterable_values_dict):
    perms = [dict(zip(possible_iterable_values_dict, b)) for b in product(*possible_iterable_values_dict.values())]
    
    return perms

async def main(app, **kwargs):
    tsl = []
    tslt = []
    nsmin = []
    nsmax = []
    market_pairs = []
    if kwargs['base_currencies']:
        market_pairs = kwargs['base_currencies']
    else:
        for quote in kwargs['quote_currencies']:
            market_pairs.extend(populate_markets(app, quote))
    for market in market_pairs:
        binary_permutations  = await gen_binary_config_perms(kwargs['config_binaries'])
        for binary_combo in binary_permutations:
            for iter_key, iter_value in kwargs['config_iterables'].items():
                iterable_permutations = arange(float(iter_value[0]), float(iter_value[1]), float(kwargs['step']))
                if iter_key == 'trailingstoploss':
                    tsl = [around(perm, 3) for perm in iterable_permutations]
                if iter_key == 'trailingstoplosstrigger':
                    tslt = [around(perm, 3) for perm in iterable_permutations]
                if iter_key == 'nosellminpcnt':
                    nsmin = [around(perm, 3) for perm in iterable_permutations]
                if iter_key == 'nosellmaxpcnt':
                    nsmax = [around(perm, 3) for perm in iterable_permutations]
            all_possibilities = {'tsl': tsl, 'tslt': tslt, 'nsmin': nsmin, 'nsmax': nsmax}
            all_possible_permutations = await get_iterables_permutations(all_possibilities) 
            for possible_config in all_possible_permutations:
                await write_config(exchange=kwargs['exchange'], base_currency=market[0], quote_currency=market[1], template=kwargs['template'],
                                   destination=kwargs['destination'], **binary_combo, **possible_config)
    return True


if __name__ == '__main__':
    import json
    from argparse import ArgumentParser


    parser = ArgumentParser(add_help=True)
    parser.add_argument('-x', '--exchange', action='store', required=True,
                        help='[coinbasepro|kucoin|binance]')
    parser.add_argument('-d', '--destination', action='store',
                        help='destination path for rendered configs')
    parser.add_argument('-t', '--template', action='store', default='config.json.j2',
                        help='path to config template')
    parser.add_argument('-q', '--quote-currencies', action='store', nargs='+',
                        default=['USDT', 'USD'], required=True,
                        help='space separated list of quote currencies')
    parser.add_argument('-r', '--ranges', action='store', required=True,
                        help='\'{"trailingstoploss": [-3,3], "trailingstoplosstrigger": [-3,3]}\'')
    parser.add_argument('-s', '--step', action='store',
                        help='number of decimal places to account for in range permutations')
    parser.add_argument('-b', '--base_currencies', action='store', nargs='+',
                        help='space separated list of base currencies')
    args = parser.parse_args()
    
    for k,v in args.__dict__.items():
        if k in config_binaries:
            config_binaries[k] = v

    ranges = json.loads(args.ranges)
    for k,v in ranges.items():
        if k in config_iterables:
            config_iterables[k] = v

    app = bootstrap(args.exchange)    

    asyncio.run(main(app, exchange=args.exchange,
                    base_currencies=args.base_currencies,
                    quote_currencies=args.quote_currencies,
                    config_iterables=config_iterables,
                    config_binaries=config_binaries,
                    step=args.step, template=args.template,
                    destination=args.destination))
