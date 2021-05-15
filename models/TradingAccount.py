"""Live or test trading account"""

import re
import requests

import numpy as np
import pandas as pd
from binance.client import Client

from models.exchange.binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import AuthAPI as CBAuthAPI


class TradingAccount():
    def __init__(self, app=None):
        """Trading account object model

        Parameters
        ----------
        app : object
            PyCryptoBot object
        """

        # config needs to be a dictionary, empty or otherwise
        if app is None:
            raise TypeError('App is not a PyCryptoBot object.')

        if app.getExchange() == 'binance':
            self.client = Client(app.getAPIKey(), app.getAPISecret(), { 'verify': False, 'timeout': 20 })

        # if trading account is for testing it will be instantiated with a balance of 1000
        self.balance = pd.DataFrame([
            [ 'QUOTE', 1000, 0, 1000 ],
            [ 'BASE', 0, 0, 0 ]], 
            columns=['currency','balance','hold','available'])
        
        self.app = app

        if app.isLive() == 1:
            self.mode = 'live'
        else:
            self.mode = 'test'

        self.orders = pd.DataFrame()

    def __convertStatus(self, val):
        if val == 'filled':
            return 'done'
        else:
            return val

    def _checkMarketSyntax(self, market):
        """Check that the market is syntactically correct

        Parameters
        ----------
        market : str
            market to check
        """
        if self.app.getExchange() == 'coinbasepro' and market != '':
            p = re.compile(r"^[1-9A-Z]{2,5}\-[1-9A-Z]{2,5}$")
            if not p.match(market):
                raise TypeError('Coinbase Pro market is invalid.')
        elif self.app.getExchange() == 'binance':
            p = re.compile(r"^[A-Z]{6,12}$")
            if not p.match(market):
                raise TypeError('Binance market is invalid.')

    def getOrders(self, market='', action='', status='all'):
        """Retrieves orders either live or simulation

        Parameters
        ----------
        market : str, optional
            Filters orders by market
        action : str, optional
            Filters orders by action
        status : str
            Filters orders by status, defaults to 'all'
        """

        # validate market is syntactically correct
        self._checkMarketSyntax(market)

        if action != '':
            # validate action is either a buy or sell
            if not action in ['buy', 'sell']:
                raise ValueError('Invalid order action.')

        # validate status is open, pending, done, active or all
        if not status in ['open', 'pending', 'done', 'active', 'all', 'filled']:
            raise ValueError('Invalid order status.')

        if self.app.getExchange() == 'binance':
            if self.mode == 'live':
                # if config is provided and live connect to Binance account portfolio
                model = BAuthAPI(self.app.getAPIKey(), self.app.getAPISecret(), self.app.getAPIURL())
                # retrieve orders from live Binance account portfolio
                self.orders = model.getOrders(market, action, status)
                return self.orders
            else:
                # return dummy orders
                if market == '':
                    return self.orders
                else:
                    return self.orders[self.orders['market'] == market]             
        if self.app.getExchange() == 'coinbasepro':
            if self.mode == 'live':
                # if config is provided and live connect to Coinbase Pro account portfolio
                model = CBAuthAPI(self.app.getAPIKey(), self.app.getAPISecret(), self.app.getAPIPassphrase(), self.app.getAPIURL())
                # retrieve orders from live Coinbase Pro account portfolio
                self.orders = model.getOrders(market, action, status)
                return self.orders
            else:
                # return dummy orders
                if market == '':
                    return self.orders
                else:
                    return self.orders[self.orders['market'] == market]

    def getBalance(self, currency=''):
        """Retrieves balance either live or simulation

        Parameters
        ----------
        currency: str, optional
            Filters orders by currency
        """

        if self.app.getExchange() == 'binance':
            if self.mode == 'live':
                model = BAuthAPI(self.app.getAPIKey(), self.app.getAPISecret())
                df = model.getAccount()
                if isinstance(df, pd.DataFrame):
                    if currency == '':
                        # retrieve all balances
                        return df
                    else:
                        # retrieve balance of specified currency
                        df_filtered = df[df['currency'] == currency]['available']
                        if len(df_filtered) == 0:
                            # return nil balance if no positive balance was found
                            return 0.0
                        else:
                            # return balance of specified currency (if positive)
                            if currency in ['EUR', 'GBP', 'USD']:
                                return float(self.app.truncate(float(df[df['currency'] == currency]['available'].values[0]), 2))
                            else:
                                return float(self.app.truncate(float(df[df['currency'] == currency]['available'].values[0]), 4))
                else:
                    return 0.0
            else:
                # return dummy balances
                if currency == '':
                    # retrieve all balances
                    return self.balance
                else:
                    if self.app.getExchange() == 'binance':
                        self.balance = self.balance.replace('QUOTE', currency)
                    else:    
                        # replace QUOTE and BASE placeholders
                        if currency in ['EUR','GBP','USD']:
                            self.balance = self.balance.replace('QUOTE', currency)
                        else:
                            self.balance = self.balance.replace('BASE', currency)

                    if self.balance.currency[self.balance.currency.isin([currency])].empty:
                        self.balance.loc[len(self.balance)] = [currency, 0, 0, 0]

                    # retrieve balance of specified currency
                    df = self.balance
                    df_filtered = df[df['currency'] == currency]['available']

                    if len(df_filtered) == 0:
                        # return nil balance if no positive balance was found
                        return 0.0
                    else:
                        # return balance of specified currency (if positive)
                        if currency in ['EUR', 'GBP', 'USD']:
                            return float(self.app.truncate(float(df[df['currency'] == currency]['available'].values[0]), 2))
                        else:
                            return float(self.app.truncate(float(df[df['currency'] == currency]['available'].values[0]), 4))

        else:
            if self.mode == 'live':
                # if config is provided and live connect to Coinbase Pro account portfolio
                model = CBAuthAPI(self.app.getAPIKey(), self.app.getAPISecret(), self.app.getAPIPassphrase(), self.app.getAPIURL())
                if currency == '':
                    # retrieve all balances
                    return model.getAccounts()[['currency', 'balance', 'hold', 'available']]
                else:
                    df = model.getAccounts()
                    # retrieve balance of specified currency
                    df_filtered = df[df['currency'] == currency]['available']
                    if len(df_filtered) == 0:
                        # return nil balance if no positive balance was found
                        return 0.0
                    else:
                        # return balance of specified currency (if positive)
                        if currency in ['EUR','GBP','USD']:
                            return float(self.app.truncate(float(df[df['currency'] == currency]['available'].values[0]), 2))
                        else:
                            return float(self.app.truncate(float(df[df['currency'] == currency]['available'].values[0]), 4))
                            
            else:
                # return dummy balances

                if currency == '':
                    # retrieve all balances
                    return self.balance
                else:
                    # replace QUOTE and BASE placeholders
                    if currency in ['EUR','GBP','USD']:
                        self.balance = self.balance.replace('QUOTE', currency)
                    elif currency in ['BCH','BTC','ETH','LTC','XLM']:
                        self.balance = self.balance.replace('BASE', currency)

                    if self.balance.currency[self.balance.currency.isin([currency])].empty == True:
                        self.balance.loc[len(self.balance)] = [currency,0,0,0]

                    # retrieve balance of specified currency
                    df = self.balance
                    df_filtered = df[df['currency'] == currency]['available']

                    if len(df_filtered) == 0:
                        # return nil balance if no positive balance was found
                        return 0.0
                    else:
                        # return balance of specified currency (if positive)
                        if currency in ['EUR','GBP','USD']:
                            return float(self.app.truncate(float(df[df['currency'] == currency]['available'].values[0]), 2))
                        else:
                            return float(self.app.truncate(float(df[df['currency'] == currency]['available'].values[0]), 4))

    def saveTrackerCSV(self, market='', save_file='tracker.csv'):
        """Saves order tracker to CSV

        Parameters
        ----------
        market : str, optional
            Filters orders by market
        save_file : str
            Output CSV file
        """

        # validate market is syntactically correct
        self._checkMarketSyntax(market)

        if self.mode == 'live':
            if self.app.getExchange() == 'coinbasepro':
                # retrieve orders from live Coinbase Pro account portfolio
                df = self.getOrders(market, '', 'done')
            elif self.app.getExchange() == 'binance':
                # retrieve orders from live Binance account portfolio
                df = self.getOrders(market, '', 'done')
            else:
                df = pd.DataFrame()
        else:
            # return dummy orders
            if market == '':
                df = self.orders
            else:
                if 'market' in self.orders:
                    df = self.orders[self.orders['market'] == market]
                else:
                    df = pd.DataFrame()

        if list(df.keys()) != [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'fees', 'price', 'status' ]:
            # no data, return early
            return False

        df_tracker = pd.DataFrame()

        last_action = ''
        for market in df['market'].sort_values().unique():
            df_market = df[df['market'] == market]

            df_buy = pd.DataFrame()
            df_sell = pd.DataFrame()

            pair = 0
            # pylint: disable=unused-variable
            for index, row in df_market.iterrows():
                if row['action'] == 'buy':
                    pair = 1

                if pair == 1 and (row['action'] != last_action):
                    if row['action'] == 'buy':
                        df_buy = row
                    elif row['action'] == 'sell':
                        df_sell = row
                            
                if row['action'] == 'sell' and len(df_buy) != 0:
                    df_pair = pd.DataFrame([
                        [
                            df_sell['status'], 
                            df_buy['market'], 
                            df_buy['created_at'], 
                            df_buy['type'], 
                            df_buy['size'],
                            df_buy['value'],
                            df_buy['fees'], 
                            df_buy['price'],
                            df_sell['created_at'],
                            df_sell['type'], 
                            df_sell['size'], 
                            df_sell['value'],
                            df_sell['fees'], 
                            df_sell['price']                    
                        ]], columns=[ 'status', 'market', 
                            'buy_at', 'buy_type', 'buy_size', 'buy_value', 'buy_fees', 'buy_price',
                            'sell_at', 'sell_type', 'sell_size', 'sell_value', 'sell_fees', 'sell_price' 
                        ])
                    df_tracker = df_tracker.append(df_pair, ignore_index=True)
                    pair = 0
                
                last_action = row['action']

        if list(df_tracker.keys()) != [ 'status', 'market', 
                            'buy_at', 'buy_type', 'buy_size', 'buy_value', 'buy_fees', 'buy_price',
                            'sell_at', 'sell_type', 'sell_size', 'sell_value', 'sell_fees', 'sell_price' ]:
            # no data, return early
            return False

        df_tracker['profit'] = np.subtract(np.subtract(df_tracker['sell_value'], df_tracker['buy_value']), np.add(df_tracker['buy_fees'], df_tracker['sell_fees']))
        df_tracker['margin'] = np.multiply(np.true_divide(df_tracker['profit'], df_tracker['buy_value']), 100)
        df_sincebot = df_tracker[df_tracker['buy_at'] > '2021-02-1']

        try:
            df_sincebot.to_csv(save_file, index=False)
        except OSError:
            raise SystemExit('Unable to save: ', save_file) 

    def buy(self, cryptoMarket, fiatMarket, fiatAmount=0, manualPrice=0.00000000):
        """Places a buy order either live or simulation

        Parameters
        ----------
        cryptoMarket: str
            Crypto market you wish to purchase
        fiatMarket, str
            QUOTE market funding the purchase
        fiatAmount, float
            QUOTE amount of crypto currency to purchase
        manualPrice, float
            Used for simulations specifying the live price to purchase
        """

        # fiat funding amount must be an integer or float
        if not isinstance(fiatAmount, float) and not isinstance(fiatAmount, int):
            raise TypeError('QUOTE amount not numeric.')

        # fiat funding amount must be positive
        if fiatAmount <= 0:
            raise Exception('Invalid QUOTE amount.')

        if self.app.getExchange() == 'binance':
             # validate crypto market is syntactically correct
            p = re.compile(r"^[A-Z]{3,8}$")
            if not p.match(cryptoMarket):
                raise TypeError('Binance crypto market is invalid.')

             # validate fiat market is syntactically correct
            p = re.compile(r"^[A-Z]{3,8}$")
            if not p.match(fiatMarket):
                raise TypeError('Binance fiat market is invalid.')
        else:
            # crypto market should be either BCH, BTC, ETH, LTC or XLM
            if cryptoMarket not in ['BCH', 'BTC', 'ETH', 'LTC', 'XLM']:
                raise Exception('Invalid crypto market: BCH, BTC, ETH, LTC, ETH, or XLM')

            # fiat market should be either EUR, GBP, or USD
            if fiatMarket not in ['EUR', 'GBP', 'USD']:
                raise Exception('Invalid QUOTE market: EUR, GBP, USD')

        # reconstruct the exchange market using crypto and fiat inputs
        if self.app.getExchange() == 'binance':
            market = cryptoMarket + fiatMarket
        else:
            market = cryptoMarket + '-' + fiatMarket

        if self.app.getExchange() == 'binance':
            if self.mode == 'live':
                # execute a live market buy
                resp = self.client.order_market_buy(symbol=market, quantity=fiatAmount)

                # TODO: not finished
                print(resp)
            else:
                # fiat amount should exceed balance
                if fiatAmount > self.getBalance(fiatMarket):
                    raise Exception('Insufficient funds.')

                # manual price must be an integer or float
                if not isinstance(manualPrice, float) and not isinstance(manualPrice, int):
                    raise TypeError('Optional manual price not numeric.')

                price = manualPrice
                # if manualPrice is non-positive retrieve the current live price
                if manualPrice <= 0:
                    if self.app.getExchange() == 'binance':
                        api = BPublicAPI()
                        price = api.getTicker(market)[1]
                    else:
                        resp = requests.get('https://api-public.sandbox.pro.coinbase.com/products/' + market + '/ticker')
                        if resp.status_code != 200:
                            raise Exception('GET /products/' + market +
                                            '/ticker {}'.format(resp.status_code))
                        resp.raise_for_status()
                        json = resp.json()
                        price = float(json['price'])

                # calculate purchase fees
                fee = fiatAmount * 0.005
                fiatAmountMinusFee = fiatAmount - fee
                total = float(fiatAmountMinusFee / float(price))

                # append dummy order into orders dataframe
                ts = pd.Timestamp.now()
                price = (fiatAmountMinusFee * 100) / (total * 100)
                order = pd.DataFrame([['', market, 'buy', 'market', float('{:.8f}'.format(total)), fiatAmountMinusFee, 'done', '{:.8f}'.format(float(price))]], columns=[
                                    'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price'], index=[ts])
                order['created_at'] = order.index
                self.orders = pd.concat([self.orders, pd.DataFrame(order)], ignore_index=False)

                # update the dummy fiat balance
                self.balance.loc[self.balance['currency'] == fiatMarket, 'balance'] = self.getBalance(fiatMarket) - fiatAmount
                self.balance.loc[self.balance['currency'] == fiatMarket, 'available'] = self.getBalance(fiatMarket) - fiatAmount

                # update the dummy crypto balance
                self.balance.loc[self.balance['currency'] == cryptoMarket, 'balance'] = self.getBalance(cryptoMarket) + (fiatAmountMinusFee / price)
                self.balance.loc[self.balance['currency'] == cryptoMarket, 'available'] = self.getBalance(cryptoMarket) + (fiatAmountMinusFee / price)

        else:
            if self.mode == 'live':
                # connect to coinbase pro api (authenticated)
                model = CBAuthAPI(self.app.getAPIKey(), self.app.getAPISecret(), self.app.getAPIPassphrase(), self.app.getAPIURL())

                # execute a live market buy
                if fiatAmount > 0:
                    resp = model.marketBuy(market, fiatAmount)
                else:
                    resp = model.marketBuy(market, float(self.getBalance(fiatMarket)))
                
                # TODO: not finished
                print(resp)
            else:
                # fiat amount should exceed balance
                if fiatAmount > self.getBalance(fiatMarket):
                    raise Exception('Insufficient funds.')

                # manual price must be an integer or float
                if not isinstance(manualPrice, float) and not isinstance(manualPrice, int):
                    raise TypeError('Optional manual price not numeric.')

                price = manualPrice
                # if manualPrice is non-positive retrieve the current live price
                if manualPrice <= 0:
                    resp = requests.get('https://api-public.sandbox.pro.coinbase.com/products/' + market + '/ticker')
                    if resp.status_code != 200:
                        raise Exception('GET /products/' + market +
                                        '/ticker {}'.format(resp.status_code))
                    resp.raise_for_status()
                    json = resp.json()
                    price = float(json['price'])

                # calculate purchase fees
                fee = fiatAmount * 0.005
                fiatAmountMinusFee = fiatAmount - fee
                total = float(fiatAmountMinusFee / price)

                # append dummy order into orders dataframe
                ts = pd.Timestamp.now()
                price = (fiatAmountMinusFee * 100) / (total * 100)
                order = pd.DataFrame([['', market, 'buy', 'market', float('{:.8f}'.format(total)), fiatAmountMinusFee, 'done', price]], columns=[
                                    'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price'], index=[ts])
                order['created_at'] = order.index
                self.orders = pd.concat([self.orders, pd.DataFrame(order)], ignore_index=False)

                # update the dummy fiat balance
                self.balance.loc[self.balance['currency'] == fiatMarket, 'balance'] = self.getBalance(fiatMarket) - fiatAmount
                self.balance.loc[self.balance['currency'] == fiatMarket, 'available'] = self.getBalance(fiatMarket) - fiatAmount

                # update the dummy crypto balance
                self.balance.loc[self.balance['currency'] == cryptoMarket, 'balance'] = self.getBalance(cryptoMarket) + (fiatAmountMinusFee / price)
                self.balance.loc[self.balance['currency'] == cryptoMarket, 'available'] = self.getBalance(cryptoMarket) + (fiatAmountMinusFee / price)

    def sell(self, cryptoMarket, fiatMarket, cryptoAmount, manualPrice=0.00000000):
        """Places a sell order either live or simulation

        Parameters
        ----------
        cryptoMarket: str
            Crypto market you wish to purchase
        fiatMarket, str
            QUOTE market funding the purchase
        fiatAmount, float
            QUOTE amount of crypto currency to purchase
        manualPrice, float
            Used for simulations specifying the live price to purchase
        """
        if self.app.getExchange() == 'binance':
             # validate crypto market is syntactically correct
            p = re.compile(r"^[A-Z]{3,8}$")
            if not p.match(cryptoMarket):
                raise TypeError('Binance crypto market is invalid.')

             # validate fiat market is syntactically correct
            p = re.compile(r"^[A-Z]{3,8}$")
            if not p.match(fiatMarket):
                raise TypeError('Binance fiat market is invalid.')
        else:
            # crypto market should be either BCH, BTC, ETH, LTC or XLM
            if cryptoMarket not in ['BCH', 'BTC', 'ETH', 'LTC', 'XLM']:
                raise Exception('Invalid crypto market: BCH, BTC, ETH, LTC, ETH, or XLM')

            # fiat market should be either EUR, GBP, or USD
            if fiatMarket not in ['EUR', 'GBP', 'USD']:
                raise Exception('Invalid QUOTE market: EUR, GBP, USD')

        # reconstruct the exchange market using crypto and fiat inputs
        if self.app.getExchange() == 'binance':
            market = cryptoMarket + fiatMarket
        else:
            market = cryptoMarket + '-' + fiatMarket

        # crypto amount must be an integer or float
        if not isinstance(cryptoAmount, float) and not isinstance(cryptoAmount, int):
            raise TypeError('Crypto amount not numeric.')

        # crypto amount must be positive
        if cryptoAmount <= 0:
            raise Exception('Invalid crypto amount.')

        if self.app.getExchange() == 'binance':
            if self.mode == 'live':
                # execute a live market buy
                resp = self.client.order_market_sell(symbol=market, quantity=cryptoAmount)

                # TODO: not finished
                print(resp)
            else:
                # crypto amount should exceed balance
                if cryptoAmount > self.getBalance(cryptoMarket):
                    raise Exception('Insufficient funds.')

                # manual price must be an integer or float
                if not isinstance(manualPrice, float) and not isinstance(manualPrice, int):
                    raise TypeError('Optional manual price not numeric.')

                # calculate purchase fees
                fee = cryptoAmount * 0.005
                cryptoAmountMinusFee = cryptoAmount - fee

                price = manualPrice
                # if manualPrice is non-positive retrieve the current live price
                if manualPrice <= 0:
                    resp = requests.get('https://api-public.sandbox.pro.coinbase.com/products/' + market + '/ticker')
                    if resp.status_code != 200:
                        raise Exception('GET /products/' + market +
                                        '/ticker {}'.format(resp.status_code))
                    resp.raise_for_status()
                    json = resp.json()
                    price = float(json['price'])

                total = price * cryptoAmountMinusFee

                # append dummy order into orders dataframe
                ts = pd.Timestamp.now()
                price = ((price * cryptoAmount) * 100) / (cryptoAmount * 100)
                order = pd.DataFrame([['', market, 'sell', 'market', cryptoAmountMinusFee, float('{:.8f}'.format(
                    total)), 'done', '{:.8f}'.format(float(price))]], columns=['created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price'], index=[ts])
                order['created_at'] = order.index
                self.orders = pd.concat([self.orders, pd.DataFrame(order)], ignore_index=False)

                # update the dummy fiat balance
                self.balance.loc[self.balance['currency'] == fiatMarket, 'balance'] = self.getBalance(fiatMarket) + total
                self.balance.loc[self.balance['currency'] == fiatMarket, 'available'] = self.getBalance(fiatMarket) + total

                # update the dummy crypto balance
                self.balance.loc[self.balance['currency'] == cryptoMarket, 'balance'] = self.getBalance(cryptoMarket) - cryptoAmount
                self.balance.loc[self.balance['currency'] == cryptoMarket, 'available'] = self.getBalance(cryptoMarket) - cryptoAmount
        
        else:
            if self.mode == 'live':
                # connect to Coinbase Pro API live
                model = CBAuthAPI(self.app.getAPIKey(), self.app.getAPISecret(), self.app.getAPIPassphrase(), self.app.getAPIURL())

                # execute a live market sell
                resp = model.marketSell(market, float(self.getBalance(cryptoMarket)))
                
                # TODO: not finished
                print(resp)
            else:
                # crypto amount should exceed balance
                if cryptoAmount > self.getBalance(cryptoMarket):
                    raise Exception('Insufficient funds.')

                # manual price must be an integer or float
                if not isinstance(manualPrice, float) and not isinstance(manualPrice, int):
                    raise TypeError('Optional manual price not numeric.')

                # calculate purchase fees
                fee = cryptoAmount * 0.005
                cryptoAmountMinusFee = cryptoAmount - fee

                price = manualPrice
                if manualPrice <= 0:
                    # if manualPrice is non-positive retrieve the current live price
                    resp = requests.get('https://api-public.sandbox.pro.coinbase.com/products/' + market + '/ticker')
                    if resp.status_code != 200:
                        raise Exception('GET /products/' + market + '/ticker {}'.format(resp.status_code))
                    resp.raise_for_status()
                    json = resp.json()
                    price = float(json['price'])

                total = price * cryptoAmountMinusFee

                # append dummy order into orders dataframe
                ts = pd.Timestamp.now()
                price = ((price * cryptoAmount) * 100) / (cryptoAmount * 100)
                order = pd.DataFrame([[market, 'sell', 'market', cryptoAmountMinusFee, float('{:.8f}'.format(
                    total)), 'done', price]], columns=['market', 'action', 'type', 'size', 'value', 'status', 'price'], index=[ts])
                order['created_at'] = order.index
                self.orders = pd.concat([self.orders, pd.DataFrame(order)], ignore_index=False)

                # update the dummy fiat balance
                self.balance.loc[self.balance['currency'] == fiatMarket, 'balance'] = self.getBalance(fiatMarket) + total
                self.balance.loc[self.balance['currency'] == fiatMarket, 'available'] = self.getBalance(fiatMarket) + total

                # update the dummy crypto balance
                self.balance.loc[self.balance['currency'] == cryptoMarket, 'balance'] = self.getBalance(cryptoMarket) - cryptoAmount
                self.balance.loc[self.balance['currency'] == cryptoMarket, 'available'] = self.getBalance(cryptoMarket) - cryptoAmount