import sys

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.exchange.coinbase import AuthAPI as CBAuthAPI  # noqa: E402
from models.exchange.coinbase_pro import AuthAPI as CAuthAPI, PublicAPI as CPublicAPI  # noqa: E402
from models.exchange.Granularity import Granularity  # noqa: E402

app1 = PyCryptoBot(exchange="coinbase")
model1 = CBAuthAPI(app1.api_key, app1.api_secret, app1.api_url, app=app1)

app2 = PyCryptoBot(exchange="coinbasepro")
model2 = CAuthAPI(app2.api_key, app2.api_secret, app2.api_passphrase, app2.api_url, app=app2)
model3 = CPublicAPI(app=app2)

""" COINBASE"""
# df = model1.get_accounts()
# df = model1.get_account("687c96ec-24bd-5607-9682-000000000000")
# print(df)
""" COINBASE PRO"""
# df = model2.get_accounts()
# print(df)


""" COINBASE"""
# df = model1.get_orders()
# df = model1.get_orders("ADA-GBP")
# df = model1.get_orders("ADA-GBP", "sell")
# df = model1.get_orders("ADA-GBP", "sell", "done")
# print(df)
""" COINBASE PRO"""
# df = model2.get_orders()
# print(df)


""" COINBASE"""
# df = model1.get_products()
# print(df)
# df = model1.get_product("ADA-GBP")
# print(df)
# df = model1.auth_api("GET", "api/v3/brokerage/products/ADA-GBP")
# print(float(df[["base_min_size"]].values[0]))


""" COINBASE"""
# df = model1.get_fees()
# print(df)
# fee = model1.get_maker_fee()
# print(fee)
# fee = model1.get_taker_fee()
# print(fee)
""" COINBASE PRO"""
# df = model2.get_fees()
# print(df)
# fee = model1.get_maker_fee()
# print(fee)
# fee = model1.get_taker_fee()
# print(fee)


""" COINBASE"""
# df = model1.get_historical_data("ADA-GBP", Granularity.ONE_MINUTE)
# df = model1.get_historical_data("BTC-GBP", Granularity.FIVE_MINUTES)
# df = model1.get_historical_data("BTC-GBP", Granularity.FIFTEEN_MINUTES)
df = model1.get_historical_data("ADA-GBP", Granularity.ONE_HOUR)
# df = model1.get_historical_data("ADA-GBP", Granularity.ONE_HOUR, iso8601start="2023-03-25T01:00:00", iso8601end="2023-03-25T05:00:00")
# df = model1.get_historical_data("ADA-GBP", Granularity.ONE_HOUR, iso8601start="2023-03-25T01:00:00")
# df = model1.get_historical_data("ADA-GBP", Granularity.ONE_HOUR, iso8601end="2023-03-25T01:00:00")
# df = model1.get_historical_data("BTC-GBP", Granularity.SIX_HOURS)
# df = model1.get_historical_data("BTC-GBP", Granularity.ONE_DAY)
print(df)

""" COINBASE PRO"""
df = model3.get_historical_data("ADA-GBP", Granularity.ONE_HOUR)  # Coinbase Pro has this in the public API, Advanced Trade has this in the auth API
print(df)


""" COINBASE"""
# df = model1.get_ticker("ADA-GBP", None)  # Coinbase Pro has this in the public API, Advanced Trade has this in the auth API
# print(df)
""" COINBASE PRO"""
# df = model3.get_ticker("ADA-GBP", None)  # Coinbase Pro has this in the public API, Advanced Trade has this in the auth API
# print(df)


""" COINBASE"""
# value = model1.market_base_increment("ADA-GBP", 15)
# print(value)
""" COINBASE PRO"""
# value = model2.market_base_increment("ADA-GBP", 15)
# print(value)


""" COINBASE"""
# value = model1.market_quote_increment("ADA-GBP", 15)
# print(value)
""" COINBASE PRO"""
# value = model2.market_quote_increment("ADA-GBP", 15)
# print(value)


""" COINBASE"""
# df = model1.market_sell("ADA-GBP", 10)
# print(df)


""" COINBASE"""
# df = model1.market_buy("ADA-GBP", 10)
# print(df)
