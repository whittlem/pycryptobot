from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount
from models.AppState import AppState
from models.exchange.binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import AuthAPI as CAuthAPI, PublicAPI as CPublicAPI

"""
app = PyCryptoBot(exchange='binance')

api = BPublicAPI()
resp = api.authAPI('GET', '/api/v3/klines' , { 'symbol': 'BTCGBP', 'interval': '1h', 'limit': 300 })
print(resp)

api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
resp = api.authAPI('GET', '/api/v3/account')
print(resp)

api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
resp = api.authAPI('GET', '/api/v3/klines' , { 'symbol': 'BTCGBP', 'interval': '1h', 'limit': 300 })
print(resp)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getAccounts()
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase())
df = api.getAccounts()
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getAccount(416)
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase())
df = api.getAccount('b54a0159-7a5c-4961-9db6-c31cafd663c7')
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getFees()
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase())
df = api.getFees()
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getMakerFee()
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase())
df = api.getMakerFee()
print(df)

app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getTakerFee()
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase())
df = api.getTakerFee()
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getUSDVolume()
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase())
df = api.getUSDVolume()
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getOrders(order_history=['BTGBTC', 'DOGEBTC', 'BTCGBP', 'DOGEGBP', 'SHIBUSDT'])
#df = api.getOrders()
print(df)

#app = PyCryptoBot(exchange='coinbasepro')
#api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase())
#df = api.getOrders('BTC-GBP')
#print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getMarkets()
print (df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
ts = api.getTime()
print(ts)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase())
ts = api.getTime()
print(ts)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BPublicAPI()
ticker = api.getTicker('BTCGBP')
print(ticker)

app = PyCryptoBot(exchange='coinbasepro')
api = CPublicAPI()
ticker = api.getTicker('BTC-GBP')
print(ticker)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BPublicAPI()
df = api.getHistoricalData('BTCGBP', '1h')
#df = api.getHistoricalData('BTCGBP', '1h', '2020-06-19T10:00:00', '2020-06-19T14:00:00')
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CPublicAPI()
df = api.getHistoricalData('BTC-GBP', 3600)
#df = api.getHistoricalData('BTC-GBP', 3600, '2020-06-19T10:00:00', '2020-06-19T14:00:00')
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getMarketInfoFilters('BTCGBP')
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
fee = api.getTradeFee('BTCGBP')
print (fee)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getOrders('SHIBUSDT')
print(df)

app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
resp = api.marketSell('SHIBUSDT', 2485964.0, test=True)
#resp = api.marketSell('SHIBUSDT', 2485964.0)
print (resp)

app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getOrders('SHIBUSDT')
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getOrders('MATICUSDT')
print(df)

app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
resp = api.marketBuy('MATICUSDT', 15.58064897, test=True)
#resp = api.marketBuy('MATICUSDT', 15.58064897)
print (resp)

app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getOrders('MATICUSDT')
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
account = TradingAccount(app)
balance = account.getBalance('SHIBUSDT')
print (balance)
"""

app = PyCryptoBot(exchange='binance')
account = TradingAccount(app)
state = AppState(app, account)
#state.minimumOrderBase()
state.minimumOrderQuote()