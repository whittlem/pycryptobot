import json
from models.TradingAccount import TradingAccount

with open('config.json') as config_file:
    config = json.load(config_file)

account = TradingAccount(config)
print (account.getBalance())
print (account.getBalance('BTC'))
#print (account.getOrders('BTC-GBP', '', 'done'))