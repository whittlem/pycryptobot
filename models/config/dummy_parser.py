import re

from .default_parser import isCurrencyValid, defaultConfigParse, merge_config_and_args


def isMarketValid(market) -> bool:
    p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
    return p.match(market) is not None


def parseMarket(market):
    if not isMarketValid(market):
        raise ValueError(f'Dummy market invalid: {market}')

    base_currency, quote_currency = market.split('-', 2)
    return market, base_currency, quote_currency


def parser(app, dummy_config, args={}):
    #print('Dummy Configuration parse')

    if not dummy_config:
        raise Exception('There is an error in your config dictionary')

    if not app:
        raise Exception('No app is passed')

    config = merge_config_and_args(dummy_config, args)

    defaultConfigParse(app, config)

    if 'base_currency' in config and config['base_currency'] is not None:
        if not isCurrencyValid(config['base_currency']):
            raise TypeError('Base currency is invalid.')
        self.base_currency = config['base_currency']

    if 'quote_currency' in config and config['quote_currency'] is not None:
        if not isCurrencyValid(config['quote_currency']):
            raise TypeError('Quote currency is invalid.')
        self.quote_currency = config['quote_currency']

    if 'market' in config and config['market'] is not None:
        self.market, self.base_currency, self.quote_currency = parseMarket(config['market'])

    if self.base_currency != '' and self.quote_currency != '':
        self.market = self.base_currency + '-' + self.quote_currency

    else:
        raise Exception('There is an error in your config dictionary')
