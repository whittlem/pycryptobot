from models.PyCryptoBot import PyCryptoBot
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

app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
df = api.getOrders('SHIBUSDT')
print(df)

#app = PyCryptoBot(exchange='coinbasepro')
#api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase())
#df = api.getOrders('BTC-GBP')
#print(df)