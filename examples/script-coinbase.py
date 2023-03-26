import sys

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.exchange.coinbase import AuthAPI as CBAuthAPI  # noqa: E402
from models.exchange.Granularity import Granularity  # noqa: E402

app = PyCryptoBot(exchange="coinbase")

model = CBAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)

# df = model.get_accounts()
# print(df)
# df = model.get_account("687c96ec-24bd-5607-9682-0f6947771112")
# print(df)

# df = model.get_products()
# print(df)

# df = model.get_fees()
# df = model.get_maker_fee()
# df = model.get_taker_fee()
# print(df)

df = model.get_historical_data("BTC-GBP", 60)
# df = model.get_historical_data("BTC-GBP", 300)
# df = model.get_historical_data("BTC-GBP", 900)
# df = model.get_historical_data("ADA-GBP", 3600)
# df = model.get_historical_data("ADA-GBP", 3600, iso8601start="2023-03-25T01:00:00", iso8601end="2023-03-25T05:00:00")
# df = model.get_historical_data("ADA-GBP", 3600, iso8601start="2023-03-25T01:00:00")
# df = model.get_historical_data("ADA-GBP", 3600, iso8601end="2023-03-25T01:00:00")
# df = model.get_historical_data("BTC-GBP", 21600)
# df = model.get_historical_data("BTC-GBP", 86400)
print(df)

# df = model.auth_api("GET", "api/v3/brokerage/orders/historical/batch")
# print(df)
