import sys

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.exchange.binance import AuthAPI as BAuthAPI  # noqa: E402
from models.exchange.coinbase import AuthAPI as CBAuthAPI  # noqa: E402
from models.exchange.coinbase_pro import AuthAPI as CAuthAPI  # noqa: E402

# Coinbase fees
app = PyCryptoBot(exchange="coinbase")
api = CBAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
# print (api.get_taker_fee())
# print (api.get_taker_fee('BTC-GBP'))
# print (api.get_maker_fee())
# print (api.get_maker_fee('BTC-GBP'))
# print (api.get_fees('BTCGBP'))
# print (api.get_fees())
print(api.get_maker_fee())
print(api.get_taker_fee())
print(app.get_maker_fee())
print(app.get_taker_fee())

"""
# Coinbase Pro fees
app = PyCryptoBot(exchange="coinbasepro")
api = CAuthAPI(app.api_key, app.api_secret, app.api_passphrase, app.api_url, app=app)
# print (api.get_taker_fee())
# print (api.get_taker_fee('BTC-GBP'))
# print (api.get_maker_fee())
# print (api.get_maker_fee('BTC-GBP'))
# print (api.get_fees('BTCGBP'))
# print (api.get_fees())
print(api.get_maker_fee())
print(api.get_taker_fee())
print(app.get_maker_fee())
print(app.get_taker_fee())
"""

"""
# Binance fees
app = PyCryptoBot(exchange="binance")
api = BAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)
# print (api.get_taker_fee())
# print (api.get_taker_fee('BTCGBP'))
# print (api.get_maker_fee())
# print (api.get_maker_fee('BTCGBP'))
# print (api.get_fees('BTCGBP'))
# print (api.get_fees())
print(api.get_maker_fee())
print(api.get_taker_fee())
print(app.get_maker_fee())
print(app.get_taker_fee())
"""
