import sys
from datetime import datetime

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.exchange.Granularity import Granularity  # noqa: E402
from models.TradingAccount import TradingAccount  # noqa: E402
from models.AppState import AppState  # noqa: E402
from models.exchange.kucoin import AuthAPI, PublicAPI  # noqa: E402

# ts = api.get_time()
# print("get_time: " + str(ts))

# ticker = api.get_ticker("BTC-USDT")
# print("get_ticker: ")
# print(ticker)

# TODO: fix this
# df = api.get_historical_data("ETH-USDT", "15min", None, "", "")

# app = PyCryptoBot(exchange="kucoin")
# api = PublicAPI("https://api.kucoin.com", app=app)
# df = api.get_historical_data("MATIC-USDT", Granularity.FIFTEEN_MINUTES, None, "2023-01-13T19:00:00", "2023-01-15T21:00:00")
# print("get_historical_data: fast")
# print(df)

# df = api.get_historical_data('ETH-USDT', '1hour', '2021-08-03T00:00:00', '2021-08-17T00:00:00')
# print("get_historical_data: fast-sample")
# print(df)

# app = PyCryptoBot(exchange="kucoin")
# api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
# df = api.get_accounts()
# print(df)

# df = api.get_account('6113cf2c4270260006395aad')
# print(df)

# app = PyCryptoBot(exchange="kucoin")
# api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
# df = api.get_fees()
# print(df)

# app = PyCryptoBot(exchange="kucoin")
# api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
# df = api.get_maker_fee()
# print(df)

# app = PyCryptoBot(exchange="kucoin")
# api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
# df = api.get_taker_fee()
# print(df)

# df = api.get_orders("MATIC-USDT", "", "done")
# print(df)
# df = api.markets()
# print (df)

# fee = api.get_trade_fee('BTC-USDT')
# print (fee)

# app = PyCryptoBot(exchange="kucoin")
# api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
# df = api.get_orders()
# df = api.get_orders("MATIC-USDT", "", "done")
# print(df)

# resp = api.market_sell('BTC-USDT', 0.0002)
# print (resp)

# app = PyCryptoBot(exchange="kucoin")
# api = AuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
# resp = api.market_buy("MATIC-USDT", 17.81358435 - (17.81358435 * 0.001))
# print (resp)

# resp = api.market_buy('XRP-USDT', 100)
# print (resp)

# account = TradingAccount(app)
# balance = self.account.get_balance('USDT')
# print (balance)

# app = PyCryptoBot(exchange='kucoin')
# account = TradingAccount(app)
# state = AppState(app, account)
# state.minimum_order_base()
# state.minimum_order_quote()
