"""Coinbase Pro trading account, simulated or live depending on if the config file is provided"""

import pandas as pd
import json, math, re, requests
from datetime import datetime
from models.CoinbasePro import AuthAPI

class TradingAccount():
    def __init__(self, config={}):
        """Trading account object model

        Parameters
        ----------
        config : str, optional
            A JSON string containing the API keys from config.json
        """

        # config needs to be a dictionary, empty or otherwise
        if not isinstance(config, dict):
            raise TypeError('Config provided is not a dictionary.')

        # if the config is provided then a valid api_url, api_key, api_secret and api_pass need to be provided
        if len(config) >= 4 and 'api_url' in config and 'api_key' in config and 'api_secret' in config and 'api_pass' in config:
            valid_urls = [
                'https://api.pro.coinbase.com',
                'https://public.sandbox.pro.coinbase.com',
                'https://api-public.sandbox.pro.coinbase.com'
            ]

            # validate api_url is valid
            if config['api_url'] not in valid_urls:
                raise ValueError('Coinbase Pro API URL is invalid')

            if config['api_url'][-1] != '/':
                config['api_url'] = config['api_url'] + '/'

            # validate api_key is syntactically correct
            p = re.compile(r"^[a-f0-9]{32,32}$")
            if not p.match(config['api_key']):
                raise TypeError('Coinbase Pro API key is invalid')

            # validate api_secret is syntactically correct
            p = re.compile(r"^[A-z0-9+\/]+==$")
            if not p.match(config['api_secret']):
                raise TypeError('Coinbase Pro API secret is invalid')

            # validate api_pass is syntactically correct
            p = re.compile(r"^[a-z0-9]{11,11}$")
            if not p.match(config['api_pass']):
                raise TypeError('Coinbase Pro API passphase is invalid')

            # if a config file is provided the trading account will be using live data!
            print(
                'Trading account mode: live (using YOUR account data - use at own risk!)')
            self.mode = 'live'

            self.api_url = config['api_url']
            self.api_key = config['api_key']
            self.api_secret = config['api_secret']
            self.api_pass = config['api_pass']
        else:
            # if a config file is not provided the trading account will be using dummy data!
            print('Trading account mode: test (using dummy data)')
            self.mode = 'test'

        # if trading account is for testing it will be instantiated with a balance of 1000
        self.balance = pd.DataFrame([['FIAT',1000,0,1000],['CRYPTO',0,0,0]], columns=['currency','balance','hold','available'])
        
        self.orders = pd.DataFrame()

    def truncate(self, f, n):
        return math.floor(f * 10 ** n) / 10 ** n

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

        if market != '':
            # validate market is syntactically correct
            p = re.compile(r"^[A-Z]{3,4}\-[A-Z]{3,4}$")
            if not p.match(market):
                raise TypeError('Coinbase Pro market is invalid.')

        if action != '':
            # validate action is either a buy or sell
            if not action in ['buy', 'sell']:
                raise ValueError('Invalid order action.')

        # validate status is open, pending, done, active or all
        if not status in ['open', 'pending', 'done', 'active', 'all']:
            raise ValueError('Invalid order status.')

        if self.mode == 'live':
            # if config is provided and live connect to Coinbase Pro account portfolio
            model = AuthAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)
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

        if self.mode == 'live':
            # if config is provided and live connect to Coinbase Pro account portfolio
            model = AuthAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)
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
                        return self.truncate(float(df[df['currency'] == currency]['available'].values[0]), 2)
                    else:
                        return self.truncate(float(df[df['currency'] == currency]['available'].values[0]), 4)
                        
        else:
            # return dummy balances

            if currency == '':
                # retrieve all balances
                return self.balance
            else:
                # replace FIAT and CRYPTO placeholders
                if currency in ['EUR','GBP','USD']:
                    self.balance = self.balance.replace('FIAT', currency)
                elif currency in ['BCH','BTC','ETH','LTC']:
                    self.balance = self.balance.replace('CRYPTO', currency)

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
                        return self.truncate(float(df[df['currency'] == currency]['available'].values[0]), 2)
                    else:
                        return self.truncate(float(df[df['currency'] == currency]['available'].values[0]), 4)

    def buy(self, cryptoMarket, fiatMarket, fiatAmount, manualPrice=0.00000000):
        """Places a buy order either live or simulation

        Parameters
        ----------
        cryptoMarket: str
            Crypto market you wish to purchase
        fiatMarket, str
            FIAT market funding the purchase
        fiatAmount, float
            FIAT amount of crypto currency to purchase
        manualPrice, float
            Used for simulations specifying the live price to purchase
        """

        # fiat funding amount must be an integer or float
        if not isinstance(fiatAmount, float) and not isinstance(fiatAmount, int):
            raise TypeError('FIAT amount not numeric.')

        # fiat funding amount must be positive
        if fiatAmount <= 0:
            raise Exception('Invalid FIAT amount.')

        # crypto market should be either BCH, BTC, ETH or LTC
        if cryptoMarket not in ['BCH', 'BTC', 'ETH', 'LTC']:
            raise Exception('Invalid crypto market: BCH, BTC, ETH, LTC or ETH')

        # fiat market should be either EUR, GBP, or USD
        if fiatMarket not in ['EUR', 'GBP', 'USD']:
            raise Exception('Invalid FIAT market: EUR, GBP, USD')

        # reconstruct the exchange market using crypto and fiat inputs
        market = cryptoMarket + '-' + fiatMarket

        if self.mode == 'live':
            # connect to coinbase pro api (authenticated)
            model = AuthAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)

            # execute a live market buy
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
                resp = requests.get(
                    'https://api-public.sandbox.pro.coinbase.com/products/BTC-GBP/ticker')
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
            order = pd.DataFrame([[market, 'buy', 'market', float('{:.8f}'.format(total)), fiatAmountMinusFee, 'done', price]], columns=[
                                 'market', 'action', 'type', 'size', 'value', 'status', 'price'], index=[ts])
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
            FIAT market funding the purchase
        fiatAmount, float
            FIAT amount of crypto currency to purchase
        manualPrice, float
            Used for simulations specifying the live price to purchase
        """
        # crypto market should be either BCH, BTC, ETH or LTC
        if cryptoMarket not in ['BCH', 'BTC', 'ETH', 'LTC']:
            raise Exception('Invalid crypto market: BCH, BTC, ETH, LTC or ETH')

        # fiat market should be either EUR, GBP, or USD
        if fiatMarket not in ['EUR', 'GBP', 'USD']:
            raise Exception('Invalid FIAT market: EUR, GBP, USD')

        # reconstruct the exchange market using crypto and fiat inputs
        market = cryptoMarket + '-' + fiatMarket

        # crypto amount must be an integer or float
        if not isinstance(cryptoAmount, float) and not isinstance(cryptoAmount, int):
            raise TypeError('Crypto amount not numeric.')

        # crypto amount must be positive
        if cryptoAmount <= 0:
            raise Exception('Invalid crypto amount.')

        if self.mode == 'live':
            # connect to Coinbase Pro API live
            model = AuthAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)

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
            self.orders = pd.concat([self.orders, pd.DataFrame(order)], ignore_index=False)

            # update the dummy fiat balance
            self.balance.loc[self.balance['currency'] == fiatMarket, 'balance'] = self.getBalance(fiatMarket) + total
            self.balance.loc[self.balance['currency'] == fiatMarket, 'available'] = self.getBalance(fiatMarket) + total

            # update the dummy crypto balance
            self.balance.loc[self.balance['currency'] == cryptoMarket, 'balance'] = self.getBalance(cryptoMarket) - cryptoAmount
            self.balance.loc[self.balance['currency'] == cryptoMarket, 'available'] = self.getBalance(cryptoMarket) - cryptoAmount