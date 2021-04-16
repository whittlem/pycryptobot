from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount

# Coinbase Pro orders
app = PyCryptoBot(exchange='coinbasepro')
app.setLive(1)
account = TradingAccount(app)
orders = account.getOrders()
print (orders)

# Binance Live orders
app = PyCryptoBot(exchange='binance')
app.setLive(1)
account = TradingAccount(app)
orders = account.getOrders('DOGEBTC')
print (orders)