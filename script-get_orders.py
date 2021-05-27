from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount

# Coinbase Pro orders
app = PyCryptoBot(exchange='coinbasepro')
app.setLive(1)
account = TradingAccount(app)
#orders = account.getOrders()
orders = account.getOrders(app.getMarket(), '', 'done')
print (orders)

# Binance Live orders
app = PyCryptoBot(exchange='binance')
app.setLive(1)
account = TradingAccount(app)
#orders = account.getOrders('DOGEBTC')
orders = account.getOrders('DOGEBTC', '', 'done')
print (orders)

# Coinbase Pro last buy
app = PyCryptoBot(exchange='coinbasepro')
app.setLive(1)
result = app.getLastBuy()
print (result)

# Binance last buy
app = PyCryptoBot(exchange='binance')
app.setLive(1)
result = app.getLastBuy()
print (result)