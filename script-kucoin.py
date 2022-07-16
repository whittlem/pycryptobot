from datetime import datetime
from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount
from models.AppState import AppState
from models.exchange.kucoin import AuthAPI as AuthAPI, PublicAPI as PublicAPI

"""
app = PyCryptoBot(exchange='kucoin')

api = PublicAPI('https://api.kucoin.com')

ts = api.get_time()
print("get_time: " + str(ts))

ticker = api.get_ticker('BTC-USDT')
print("get_ticker: ")
print(ticker)

df = api.get_historical_data('ETH-USDT', '1hour', '', '')
print("get_historical_data: fast")
print(df)
df = api.get_historical_data('ETH-USDT', '1hour', '2021-08-03T00:00:00', '2021-08-17T00:00:00')
print("get_historical_data: fast-sample")
print(df)

"""

"""
api = AuthAPI(api_key, api_secret, api_passphrase, url)

df = api.getAccounts()
print("getAccounts:")
print(df)

df = api.getAccount('6113cf2c4270260006395aad')
print(df)


df = api.getFees()
print(df)


df = api.get_maker_fee()
print(df)


df = api.get_taker_fee()
print(df)

df = api.get_orders('BTC-USDT', '', 'done')
print(df)

df = api.markets()
print (df)


fee = api.getTradeFee('BTC-USDT')
print (fee)


df = api.get_orders('BTC-USDT')
print(df)

resp = api.marketSell('BTC-USDT', 0.0002)
print (resp)


resp = api.marketBuy('BTC-USDT', 100)
print (resp)
resp = api.marketBuy('XRP-USDT', 100)
print (resp)

account = TradingAccount(app)
balance = self.account.get_balance('USDT')
print (balance)


app = PyCryptoBot(exchange='kucoin')
account = TradingAccount(app)
state = AppState(app, account)
state.minimum_order_base()
state.minimum_order_quote()

"""