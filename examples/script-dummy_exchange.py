import sys

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.TradingAccount import TradingAccount  # noqa: E402

app = PyCryptoBot(exchange='dummy')

account = TradingAccount(app)
# print (account.get_balance())

# account.deposit_base_currency(0.5)
# print (account.get_balance())

account.deposit_quote_currency(1000)
print(account.get_balance(), "\n")

# account.withdraw_base_currency(0.5)
# print (account.get_balance())

# account.withdraw_quote_currency(500)
# print (account.get_balance())

account.market_buy(app.market, 100, 100, 20000)
print(account.get_balance(), "\n")

account.market_sell(app.market, account.get_balance(app.base_currency), 100, 20000)
print(account.get_balance(), "\n")

print(account.get_orders())
