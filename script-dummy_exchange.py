from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount

app = PyCryptoBot(exchange='dummy')

account = TradingAccount(app)
#print (account.getBalance())

#account.depositBaseCurrency(0.5)
#print (account.getBalance())

account.depositQuoteCurrency(1000)
print (account.getBalance(), "\n")

#account.withdrawBaseCurrency(0.5)
#print (account.getBalance())

#account.withdrawQuoteCurrency(500)
#print (account.getBalance())

account.marketBuy(app.market, 100, 100, 20000)
print (account.getBalance(), "\n")

account.marketSell(app.market, account.getBalance(app.base_currency), 100, 20000)
print (account.getBalance(), "\n")

print (account.getOrders())