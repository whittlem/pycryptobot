from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount
from models.AppState import AppState

app = PyCryptoBot()
account = TradingAccount(app)
state = AppState(app, account)

print (account.getBalance(app.getBaseCurrency()), account.getBalance(app.getQuoteCurrency()))

print (state.last_action)
state.initLastAction(app, account, state)
print (state.last_action)