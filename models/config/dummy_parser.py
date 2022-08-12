import re

from .default_parser import is_currency_valid, default_config_parse, merge_config_and_args


def is_market_valid(market) -> bool:
    p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
    return p.match(market) is not None


def parse_market(market):
    if not is_market_valid(market):
        raise ValueError(f'Dummy market invalid: {market}')

    base_currency, quote_currency = market.split('-', 2)
    return market, base_currency, quote_currency


def parser(app, dummy_config, args={}):
    if not dummy_config:
        raise Exception('There is an error in your config dictionary')

    if not app:
        raise Exception('No app is passed')

    config = merge_config_and_args(dummy_config, args)

    default_config_parse(app, config)

    if 'base_currency' in config and config['base_currency'] is not None:
        if not is_currency_valid(config['base_currency']):
            raise TypeError('Base currency is invalid.')
        base_currency = config['base_currency']

    if 'quote_currency' in config and config['quote_currency'] is not None:
        if not is_currency_valid(config['quote_currency']):
            raise TypeError('Quote currency is invalid.')
        quote_currency = config['quote_currency']

    if 'market' in config and config['market'] is not None:
        market, base_currency, quote_currency = parse_market(config['market'])

    if base_currency != '' and quote_currency != '':
        market = base_currency + '-' + quote_currency  # noqa: F841
    else:
        raise Exception('There is an error in your config dictionary')
