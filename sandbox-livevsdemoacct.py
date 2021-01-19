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
account.buy('BTC','GBP',100,26000)
account.sell('BTC','GBP',0.003827,26500)
account.buy('BTC','GBP',100,30000)
account.sell('BTC','GBP',0.003317,35000)
print (account.getOrders())