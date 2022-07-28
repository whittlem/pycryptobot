from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount
from models.AppState import AppState
from models.exchange.binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import AuthAPI as CAuthAPI, PublicAPI as CPublicAPI

app = PyCryptoBot(exchange='binance')

"""
api = BPublicAPI(api_url=app.api_url)
resp = api.authAPI('GET', '/api/v3/klines' , { 'symbol': 'BTCGBP', 'interval': '1h', 'limit': 300 })
print(resp)

api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
resp = api.authAPI('GET', '/api/v3/account')
print(resp)

api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
resp = api.authAPI('GET', '/api/v3/klines' , { 'symbol': 'BTCGBP', 'interval': '1h', 'limit': 300 })
print(resp)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.getAccounts()
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.api_key, self.api_secret, self.api_passphrase)
df = api.getAccounts()
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.getAccount()
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.api_key, self.api_secret, self.api_passphrase)
df = api.getAccount('b54a0159-7a5c-4961-9db6-c31cafd663c7')
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.getFees()
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.api_key, self.api_secret, self.api_passphrase)
df = api.getFees()
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.get_maker_fee()
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.api_key, self.api_secret, self.api_passphrase)
df = api.get_maker_fee()
print(df)

app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.get_taker_fee()
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.api_key, self.api_secret, self.api_passphrase)
df = api.get_taker_fee()
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.getUSDVolume()
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.api_key, self.api_secret, self.api_passphrase)
df = api.getUSDVolume()
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.get_orders(order_history=['BTGBTC', 'DOGEBTC', 'BTCGBP', 'DOGEGBP', 'SHIBUSDT'])
#df = api.get_orders('SHIBUSDT')
print(df)

#app = PyCryptoBot(exchange='coinbasepro')
#api = CAuthAPI(app.api_key, self.api_secret, self.api_passphrase)
#df = api.get_orders('BTC-GBP')
#print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.markets()
print (df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
ts = api.get_time()
print(ts)

app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.api_key, self.api_secret, self.api_passphrase)
ts = api.get_time()
print(ts)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BPublicAPI(api_url=app.api_url)
ticker = api.get_ticker('BTCGBP')
print(ticker)

app = PyCryptoBot(exchange='coinbasepro')
api = CPublicAPI()
ticker = api.get_ticker('BTC-GBP')
print(ticker)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BPublicAPI(api_url=app.api_url)
#df = api.get_historical_data('BTCGBP', '1h')
df = api.get_historical_data('BTCGBP', '1h', '2020-06-19T10:00:00', '2020-06-19T14:00:00')
print(df)

app = PyCryptoBot(exchange='coinbasepro')
api = CPublicAPI()
df = api.get_historical_data('BTC-GBP', 3600)
#df = api.get_historical_data('BTC-GBP', 3600, '2020-06-19T10:00:00', '2020-06-19T14:00:00')
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.marketInfoFilters('BTCGBP')
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
fee = api.getTradeFee('BTCGBP')
print (fee)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.get_orders('SHIBUSDT')
print(df)

app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
resp = api.marketSell('SHIBUSDT', 2485964.0, test=True)
#resp = api.marketSell('SHIBUSDT', 2485964.0)
print (resp)

app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.get_orders('SHIBUSDT')
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.get_orders('MATICUSDT')
print(df)

app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
resp = api.marketBuy('MATICUSDT', 15.58064897, test=True)
#resp = api.marketBuy('MATICUSDT', 15.58064897)
print (resp)

app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
df = api.get_orders('MATICUSDT')
print(df)
"""

"""
app = PyCryptoBot(exchange='binance')
account = TradingAccount(app)
balance = self.account.get_balance('SHIBUSDT')
print (balance)
"""

"""
app = PyCryptoBot(exchange='binance')
account = TradingAccount(app)
state = AppState(app, account)
#state.minimum_order_base()
state.minimum_order_quote()
"""