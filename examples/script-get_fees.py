from models.PyCryptoBot import PyCryptoBot
from models.exchange.binance import AuthAPI as BAuthAPI
from models.exchange.coinbase_pro import AuthAPI as CAuthAPI

# Coinbase Pro fees
app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.api_key, self.api_secret, self.api_passphrase, self.api_url)
#print (api.get_taker_fee())
#print (api.get_taker_fee('BTC-GBP'))
#print (api.get_maker_fee())
#print (api.get_maker_fee('BTC-GBP'))
#print (api.getFees('BTCGBP'))
#print (api.getFees())
print (app.get_maker_fee())
print (app.get_taker_fee())

# Binance fees
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.api_key, self.api_secret, self.api_url)
#print (api.get_taker_fee())
#print (api.get_taker_fee('BTCGBP'))
#print (api.get_maker_fee())
#print (api.get_maker_fee('BTCGBP'))
#print (api.getFees('BTCGBP'))
#print (api.getFees())
print (app.get_maker_fee())
print (app.get_taker_fee())