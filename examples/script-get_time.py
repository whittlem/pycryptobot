import sys

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.exchange.binance import PublicAPI as BPublicAPI  # noqa: E402
from models.exchange.coinbase_pro import PublicAPI as CBPublicAPI  # noqa: E402

# Coinbase Pro time
api = CBPublicAPI()
ts = api.get_time()
print(ts)

app = PyCryptoBot(exchange='coinbasepro')
ts = api.get_time()
print(ts)

# Binance Live time
api = BPublicAPI()
ts = api.get_time()
print(ts)

app = PyCryptoBot(exchange='binance')
ts = api.get_time()
print(ts)
