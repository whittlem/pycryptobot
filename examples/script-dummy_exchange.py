from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount

app = PyCryptoBot(exchange='dummy')

account = TradingAccount(app)
#print (self.account.get_balance())

#account.depositBaseCurrency(0.5)
#print (self.account.get_balance())

account.depositQuoteCurrency(1000)
print (self.account.get_balance(), "\n")

#account.withdrawBaseCurrency(0.5)
#print (self.account.get_balance())

#account.withdrawQuoteCurrency(500)
#print (self.account.get_balance())

account.marketBuy(app.market, 100, 100, 20000)
print (self.account.get_balance(), "\n")

account.marketSell(app.market, self.account.get_balance(app.base_currency), 100, 20000)
print (self.account.get_balance(), "\n")

print (self.account.get_orders())