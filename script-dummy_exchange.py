from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount

app = PyCryptoBot(exchange='dummy')

account = TradingAccount(app)
print (account.getBalance())

'''
TODO: re-implement this

account.depositQuoteCurrency(1000)
print (account.getBalance())

account.marketBuy(app.getMarket(), 100, 100, 20000)
account.marketSell(app.getMarket()', 0.004975, 100, 30000)
account.marketBuy(app.getMarket(), 100, 100, 31000)
account.marketSell(app.getMarket(), 100, 3000)
'''