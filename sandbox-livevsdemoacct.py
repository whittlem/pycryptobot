"""Trading Account object model examples"""

import json
from models.TradingAccount import TradingAccount

with open('config.json') as config_file:
    config = json.load(config_file)

# live trading account - your account data!

'''
account = TradingAccount(config)
print (account.getBalance('GBP'))
print (account.getOrders('BTC-GBP'))
'''

# test trading account - dummy data

account = TradingAccount()
print (account.getBalance('GBP'))
print (account.getBalance('BTC'))
account = TradingAccount()
account.buy('BTC','GBP',250,30000)
print (account.getBalance())
account.sell('BTC','GBP',0.0082,35000)
print (account.getBalance())
account.buy('ETH','GBP',250,30000)
print (account.getBalance())
account.sell('ETH','GBP',0.0082,35000)
print (account.getOrders())
print (account.getOrders('BTC-GBP'))
print (account.getOrders('ETH-GBP'))