"""Application state class"""

import sys
from numpy import array as np_array, min as np_min, ptp as np_ptp
from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount
from models.exchange.binance import AuthAPI as BAuthAPI
from models.exchange.coinbase_pro import AuthAPI as CAuthAPI

def binanceMinimumOrderBase(app:PyCryptoBot, account:TradingAccount):
    app = PyCryptoBot(exchange='binance')
    api = BAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIURL())
    info = api.client.get_symbol_info(symbol='BTCGBP')

    base_min = 0
    if 'filters' in info:
        for filter_type in info['filters']:
            if 'LOT_SIZE' == filter_type['filterType']:
                base_min = float(filter_type['minQty'])

    base = float(account.getBalance(app.getBaseCurrency()))

    if base < base_min:
        sys.tracebacklimit = 0
        raise Exception(f'Insufficient Base Funds! (Actual: {base}, Minimum: {base_min})')    

def binanceMinimumOrderQuote(app:PyCryptoBot, account:TradingAccount):
    app = PyCryptoBot(exchange='binance')
    api = BAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIURL())
    info = api.client.get_symbol_info(symbol='BTCGBP')

    quote_min = 0
    if 'filters' in info:
        for filter_type in info['filters']:
            if 'MIN_NOTIONAL' == filter_type['filterType']:
                quote_min = float(filter_type['minNotional'])

    quote = float(account.getBalance(app.getQuoteCurrency()))

    if quote < quote_min:
        sys.tracebacklimit = 0
        raise Exception(f'Insufficient Quote Funds! (Actual: {quote}, Minimum: {quote_min})')    

def coinbaseproMinimumOrderBase(app:PyCryptoBot, account:TradingAccount):
    api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase(), app.getAPIURL())
    product = api.authAPI('GET', f'products/{app.getMarket()}')
    if len(product) == 0:
        sys.tracebacklimit = 0
        raise Exception(f'Market not found! ({app.getMarket()})')

    base = float(account.getBalance(app.getBaseCurrency()))
    base_min = float(product['base_min_size'])

    if base < base_min:
        sys.tracebacklimit = 0
        raise Exception(f'Insufficient Base Funds! (Actual: {base}, Minimum: {base_min})')    

def coinbaseproMinimumOrderQuote(app:PyCryptoBot, account:TradingAccount):
    api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase(), app.getAPIURL())
    product = api.authAPI('GET', f'products/{app.getMarket()}')
    if len(product) == 0:
        sys.tracebacklimit = 0
        raise Exception(f'Market not found! ({app.getMarket()})')

    ticker = api.authAPI('GET', f'products/{app.getMarket()}/ticker')
    price = float(ticker['price'])

    quote = float(account.getBalance(app.getQuoteCurrency()))
    base_min = float(product['base_min_size'])

    if (quote / price) < base_min:
        sys.tracebacklimit = 0
        raise Exception(f'Insufficient Quote Funds! (Actual: {"{:.8f}".format((quote / price))}, Minimum: {base_min})')

class AppState():
    def __init__(self):
        self.action = 'WAIT'
        self.buy_count = 0
        self.buy_state = ''
        self.buy_sum = 0
        self.eri_text = ''
        self.fib_high = 0
        self.fib_low = 0
        self.iterations = 0
        self.last_action = ''
        self.last_buy_size = 0
        self.last_buy_price = 0
        self.last_buy_filled = 0
        self.last_buy_fee = 0
        self.last_buy_high = 0 
        self.last_df_index = ''
        self.sell_count = 0
        self.sell_sum = 0
        self.first_buy_size = 0

    @classmethod
    def updateLastAction(self, app:PyCryptoBot, account:TradingAccount, state):
        orders = account.getOrders(app.getMarket(), '', 'done')
        if len(orders) > 0:
            last_order = orders[-1:]

            # if orders exist and last order is a buy
            if str(last_order.action.values[0]) == 'buy':
                state.last_buy_size = float(last_order[last_order.action == 'buy']['size'])
                state.last_buy_filled = float(last_order[last_order.action == 'buy']['filled'])
                state.last_buy_price = float(last_order[last_order.action == 'buy']['price'])
                state.last_buy_fee = float(last_order[last_order.action == 'buy']['fees'])
                state.last_action = 'BUY'
                return
            else:
                state.last_action = 'SELL'
                state.last_buy_price = 0.0

                if app.getExchange() == 'coinbasepro':
                    coinbaseproMinimumOrderBase(app, account)
                elif app.getExchange() == 'binance':
                    binanceMinimumOrderBase(app, account)

                return
        else:
            base = float(account.getBalance(app.getBaseCurrency()))
            quote = float(account.getBalance(app.getQuoteCurrency()))

            # nil base or quote funds
            if base == 0.0 and quote == 0.0:
                sys.tracebacklimit = 0
                raise Exception(f'Insufficient Funds! ({app.getBaseCurrency()}={str(base)}, {app.getQuoteCurrency()}={str(base)})') 

            # determine last action by comparing normalised [0,1] base and quote balances 
            order_pairs = np_array([ base, quote ])
            order_pairs_normalised = (order_pairs - np_min(order_pairs)) / np_ptp(order_pairs)

            if order_pairs_normalised[0] < order_pairs_normalised[1]:
                state.last_action = 'BUY'
                if app.getExchange() == 'coinbasepro':
                    coinbaseproMinimumOrderQuote(app, account)
                elif app.getExchange() == 'binance':
                    binanceMinimumOrderQuote(app, account)

            elif order_pairs_normalised[0] > order_pairs_normalised[1]:
                state.last_action = 'SELL'
                if app.getExchange() == 'coinbasepro':
                    coinbaseproMinimumOrderBase(app, account)
                elif app.getExchange() == 'binance':
                    binanceMinimumOrderBase(app, account)

            else:
                state.last_action = 'WAIT'

            return