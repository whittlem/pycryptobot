from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount

app = PyCryptoBot(exchange='dummy')

account = TradingAccount(app)
#print (self.account.get_balance())

#account.deposit_base_currency(0.5)
#print (self.account.get_balance())

account.deposit_quote_currency(1000)
print (self.account.get_balance(), "\n")

#account.withdraw_base_currency(0.5)
#print (self.account.get_balance())

#account.withdraw_quote_currency(500)
#print (self.account.get_balance())

account.market_buy(app.market, 100, 100, 20000)
print (self.account.get_balance(), "\n")

account.market_sell(app.market, self.account.get_balance(app.base_currency), 100, 20000)
print (self.account.get_balance(), "\n")

print (self.account.get_orders())