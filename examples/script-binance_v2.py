import sys

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.TradingAccount import TradingAccount  # noqa: E402
from models.AppState import AppState  # noqa: E402
from models.exchange.binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI  # noqa: E402
from models.exchange.coinbase_pro import AuthAPI as CAuthAPI, PublicAPI as CPublicAPI  # noqa: E402

app = PyCryptoBot(exchange="binance")

# api = BPublicAPI(api_url=app.api_url, app=app)
# resp = api.auth_api("GET", "/api/v3/klines", {"symbol": "BTCGBP", "interval": "1h", "limit": 300})
# print(resp)

api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
resp = api.auth_api("GET", "/api/v3/account")
# print(resp)

api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
resp = api.auth_api("GET", "/api/v3/klines", {"symbol": "BTCGBP", "interval": "1h", "limit": 300})
# print(resp)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
df = api.get_accounts()
# print(df)

# app = PyCryptoBot(exchange='coinbasepro')
# api = CAuthAPI(app.api_key, app.api_secret, app.api_passphrase, app=app)
# df = api.get_accounts()
# print(df)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
df = api.get_account()
# print(df)

# app = PyCryptoBot(exchange='coinbasepro')
# api = CAuthAPI(app.api_key, app.api_secret, app.api_passphrase, app=app)
# df = api.get_account('b54a0159-7a5c-4961-9db6-c31cafd663c7')
# print(df)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
df = api.get_fees()
# print(df)

# app = PyCryptoBot(exchange='coinbasepro')
# api = CAuthAPI(app.api_key, app.api_secret, app.api_passphrase, app=app)
# df = api.get_fees()
# print(df)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
df = api.get_maker_fee()
# print(df)

# app = PyCryptoBot(exchange='coinbasepro')
# api = CAuthAPI(app.api_key, app.api_secret, app.api_passphrase, app=app)
# df = api.get_maker_fee()
# print(df)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
df = api.get_taker_fee()
# print(df)

# app = PyCryptoBot(exchange='coinbasepro')
# api = CAuthAPI(app.api_key, app.api_secret, app.api_passphrase, app=app)
# df = api.get_taker_fee()
# print(df)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
df = api.get_usd_volume()
# print(df)

# app = PyCryptoBot(exchange='coinbasepro')
# api = CAuthAPI(app.api_key, app.api_secret, app.api_passphrase, app=app)
# df = api.get_usd_volume()
# print(df)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
df = api.get_orders(order_history=["BTGBTC", "DOGEBTC", "BTCGBP", "DOGEGBP", "SHIBUSDT"])
df = api.get_orders("SHIBUSDT")
# print(df)

# app = PyCryptoBot(exchange='coinbasepro')
# api = CAuthAPI(app.api_key, app.api_secret, app.api_passphrase, app=app)
# df = api.get_orders('BTC-GBP')
# print(df)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
ts = api.get_time()
# print(ts)

# app = PyCryptoBot(exchange='coinbasepro')
# api = CAuthAPI(app.api_key, app.api_secret, app.api_passphrase, app=app)
# ts = api.get_time()
# print(ts)

app = PyCryptoBot(exchange="binance")
api = BPublicAPI(api_url=app.api_url, app=app)
ticker = api.get_ticker("BTCGBP")
# print(ticker)

# app = PyCryptoBot(exchange='coinbasepro')
# api = CPublicAPI(app=app)
# ticker = api.get_ticker('BTC-GBP')
# print(ticker)

app = PyCryptoBot(exchange="binance")
api = BPublicAPI(api_url=app.api_url, app=app)
df = api.get_historical_data("BTCGBP", "1h")
df = api.get_historical_data("BTCGBP", "1h", None, "2020-06-19T10:00:00", "2020-06-19T14:00:00")
# print(df)

# app = PyCryptoBot(exchange='coinbasepro')
# api = CPublicAPI(app=app)
# df = api.get_historical_data('BTC-GBP', 3600)
# df = api.get_historical_data('BTC-GBP', 3600, '2020-06-19T10:00:00', '2020-06-19T14:00:00')
# print(df)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
df = api.get_market_info_filters("BTCGBP")
# print(df)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
fee = api.get_trade_fee("BTCGBP")
# print (fee)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
df = api.get_orders("SHIBUSDT")
# print(df)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
resp = api.market_sell("SHIBUSDT", 2485964.0, test=True)
resp = api.market_sell("SHIBUSDT", 2485964.0)
# print (resp)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
df = api.get_orders("SHIBUSDT")
# print(df)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
df = api.get_orders("MATICUSDT")
# print(df)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
# resp = api.market_buy("MATICUSDT", 15.58064897, test=True)
# resp = api.market_buy("MATICUSDT", 15.58064897)
# print (resp)

app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
df = api.get_orders("MATICUSDT")
# print(df)

app = PyCryptoBot(exchange="binance")
account = TradingAccount(app)
balance = account.get_balance("SHIBUSDT")
# print (balance)

app = PyCryptoBot(exchange="binance")
account = TradingAccount(app)
state = AppState(app, account)
state.minimum_order_base()
state.minimum_order_quote()
