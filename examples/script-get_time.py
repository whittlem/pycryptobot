from models.PyCryptoBot import PyCryptoBot
from models.exchange.binance import PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import PublicAPI as CBPublicAPI

# Coinbase Pro time
api = CBPublicAPI()
ts = api.get_time()
print (ts)

app = PyCryptoBot(exchange='coinbasepro')
ts = api.get_time()
print (ts)

# Binance Live time
api = BPublicAPI()
ts = api.get_time()
print (ts)

app = PyCryptoBot(exchange='binance')
ts = api.get_time()
print (ts)