import pandas as pd
import json, re, requests
from datetime import datetime
from models.CoinbaseProAPI import CoinbaseProAPI

class TradingAccount():
    def __init__(self, config={}):
        if not isinstance(config, dict):
            raise TypeError('Config provided is not a dictionary.')

        if len(config) >= 4 and 'api_url' in config and 'api_key' in config and 'api_secret' in config and 'api_pass' in config:
            valid_urls = [
                'https://api.pro.coinbase.com',
                'https://public.sandbox.pro.coinbase.com',
                'https://api-public.sandbox.pro.coinbase.com'
            ]

            if config['api_url'] not in valid_urls:
                raise ValueError('Coinbase Pro API URL is invalid')

            if config['api_url'][-1] != '/':
                config['api_url'] = config['api_url'] + '/' 

            p = re.compile(r"^[a-f0-9]{32,32}$")
            if not p.match(config['api_key']):
                raise TypeError('Coinbase Pro API key is invalid')
    
            p = re.compile(r"^[A-z0-9+\/]+==$")
            if not p.match(config['api_secret']):
                raise TypeError('Coinbase Pro API secret is invalid')

            p = re.compile(r"^[a-z0-9]{11,11}$")
            if not p.match(config['api_pass']):
                raise TypeError('Coinbase Pro API passphase is invalid')      

            print ('Trading account mode: live (using YOUR account data - use at own risk!)')
            self.mode = 'live'

            self.api_url = config['api_url']
            self.api_key = config['api_key']
            self.api_secret = config['api_secret']
            self.api_pass = config['api_pass']           
        else:
            print ('Trading account mode: test (using dummy data)')
            self.mode = 'test'

        self.balance = 1000
        self.orders = pd.DataFrame()

    def getOrders(self, market='', action='', status='all'):
        if market != '':
            p = re.compile(r"^[A-Z]{3,4}\-[A-Z]{3,4}$")
            if not p.match(market):
                raise TypeError('Coinbase Pro market is invalid.')

        if action != '':
            if not action in ['buy', 'sell']:
                raise ValueError('Invalid order action.')

        if not status in ['open', 'pending', 'done', 'active', 'all']:
            raise ValueError('Invalid order status.')

        if self.mode == 'live':
            model = CoinbaseProAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)
            self.orders = model.getOrders(market, action, status)
            return self.orders
        else:
            return self.orders

    def getBalance(self, currency=''):
        if self.mode == 'live':
            model = CoinbaseProAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)
            if currency == '':
                return model.getAccounts()[['currency','balance','hold','available']]
            else:
                df = model.getAccounts()
                df_filtered = df[df['currency'] == currency]['available']
                if len(df_filtered) == 0:
                    return 0.0
                else:
                    return df[df['currency'] == currency]['available'].values[0]
        else:
            return self.balance

    def buy(self, cryptoMarket, fiatMarket, fiatAmount, manualPrice=0.00000000):
        if not isinstance(fiatAmount, float) and not isinstance(fiatAmount, int):
            raise TypeError('FIAT amount not numeric.')

        if fiatAmount <= 0:
            raise Exception('Invalid FIAT amount.')

        if fiatAmount > self.balance:
            raise Exception('Insufficient funds.')

        if cryptoMarket not in ['BCH','BTC','ETH','LTC']:
            raise Exception('Invalid crypto market: BCH, BTC, ETH, LTC or ETH')

        if fiatMarket not in ['EUR','GBP','USD']:
            raise Exception('Invalid FIAT market: EUR, GBP, USD')

        if not isinstance(manualPrice, float) and not isinstance(manualPrice, int):
            raise TypeError('Optional manual price not numeric.')

        market = cryptoMarket + '-' + fiatMarket

        price = manualPrice
        if manualPrice <= 0:
            resp = requests.get('https://api-public.sandbox.pro.coinbase.com/products/BTC-GBP/ticker')
            if resp.status_code != 200:
                raise Exception('GET /products/' + market + '/ticker {}'.format(resp.status_code))
            resp.raise_for_status()
            json = resp.json()
            price = float(json['price'])

        fee = fiatAmount * 0.005
        fiatAmountMinusFee = fiatAmount - fee
        total = float(fiatAmountMinusFee / price)

        ts = pd.Timestamp.now()
        price = (fiatAmountMinusFee * 100) / (total * 100)
        order = pd.DataFrame([[market,'buy','market',float('{:.8f}'.format(total)),fiatAmountMinusFee,'done',price]], columns=['market','action','type','size','value','status','price'], index=[ts])
        self.orders = pd.concat([self.orders, pd.DataFrame(order)], ignore_index=False)
        self.balance = self.balance - fiatAmount

    def sell(self, cryptoMarket, fiatMarket, cryptoAmount, manualPrice=0.00000000):
        if cryptoMarket not in ['BCH','BTC','ETH','LTC']:
            raise Exception('Invalid crypto market: BCH, BTC, ETH, LTC or ETH')

        if fiatMarket not in ['EUR','GBP','USD']:
            raise Exception('Invalid FIAT market: EUR, GBP, USD')

        market = cryptoMarket + '-' + fiatMarket

        if not isinstance(cryptoAmount, float) and not isinstance(cryptoAmount, int):
            raise TypeError('Crypto amount not numeric.')

        if cryptoAmount <= 0:
            raise Exception('Invalid crypto amount.')

        if not isinstance(manualPrice, float) and not isinstance(manualPrice, int):
            raise TypeError('Optional manual price not numeric.')

        fee = cryptoAmount * 0.005
        cryptoAmountMinusFee = cryptoAmount - fee

        price = manualPrice
        if manualPrice <= 0:
            resp = requests.get('https://api-public.sandbox.pro.coinbase.com/products/BTC-GBP/ticker')
            if resp.status_code != 200:
                raise Exception('GET /products/' + market + '/ticker {}'.format(resp.status_code))
            resp.raise_for_status()
            json = resp.json()
            price = float(json['price'])

        total = price * cryptoAmountMinusFee
        
        ts = pd.Timestamp.now()
        price = ((price * cryptoAmount) * 100) / (cryptoAmount * 100)
        order = pd.DataFrame([[market, 'sell', 'market', cryptoAmountMinusFee, float('{:.8f}'.format(total)), 'done',price]], columns=['market', 'action', 'type', 'size', 'value', 'status','price'], index=[ts])
        self.orders = pd.concat([self.orders, pd.DataFrame(order)], ignore_index=False)        
        self.balance = self.balance + total
