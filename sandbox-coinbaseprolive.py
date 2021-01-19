"""Coinbase Pro API object model examples"""

import json
from models.CoinbaseProAPI import CoinbaseProAPI

with open('config.json') as config_file:
    config = json.load(config_file)

model = CoinbaseProAPI(config['api_key'], config['api_secret'], config['api_pass'], config['api_url'])

accounts = model.getAccounts()
print (accounts)

#account = model.getAccount('00000000-0000-0000-0000-000000000000')
#print (account)

orders1 = model.getOrders()
print (orders1)

orders2 = model.getOrders('BTC-GBP')
print (orders2)

orders3 = model.getOrders('BTC-GBP', 'buy')
print (orders3)

orders4 = model.getOrders('BTC-GBP', 'buy', 'done')
print (orders4)

#order = model.marketBuy('BTC-GBP', 100)
#print (order)

#order = model.marketSell('BTC-GBP', 0.001)
#print (order)