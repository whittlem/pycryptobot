import json, requests
from datetime import datetime

class TradingAccount():
    def __init__(self, user='anonymous'):
        self.balance = 0
        self.user = user
        self.activity = []
        #self.activity.append([datetime.now().strftime(
        #    "%Y-%m-%d %H:%M:%S"), 0, 'open', 0, 0])

    def getActivity(self):
        return self.activity

    def getBalanceFIAT(self):
        return self.balance

    def getUser(self):
        return self.user

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

        self.balance = self.balance - fiatAmount
        self.activity.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.balance, 'buy', float('{:.8f}'.format(total)), price])

        #print ('Fee =', '{:.2f}'.format(fee), fiatMarket)
        #print ('Total =', '{:.8f}'.format(total), cryptoMarket)       

    def depositFIAT(self, amount):
        if not isinstance(amount, float) and not isinstance(amount, int):
            raise TypeError('Deposit amount not numeric.')

        if amount <= 0:
            raise Exception('Insufficient deposit.')

        self.balance = self.balance + amount
        #self.activity.append([datetime.now().strftime(
        #    "%Y-%m-%d %H:%M:%S"), amount, 'deposit'])

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
        
        self.balance = self.balance + total
        self.activity.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.balance, 'sell', float('{:.8f}'.format(total)), price])

        #print ('Fee =', '{:.2f}'.format(fee * float(json['price'])), fiatMarket)
        #print ('Total =', '{:.8f}'.format(total), fiatMarket) 

    def withdraw(self, amount):
        if not isinstance(amount, float) and not isinstance(amount, int):
            raise TypeError('Withdraw amount not numeric.')

        if amount <= 0:
            raise Exception('Insufficient withdraw.')

        if amount > self.balance:
            raise Exception('Insufficient funds.')

        self.balance = self.balance - amount
        self.activity.append([datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"), -amount, 'withdraw'])
