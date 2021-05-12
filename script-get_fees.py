from models.PyCryptoBot import PyCryptoBot
from models.Binance import AuthAPI as BAuthAPI
from models.CoinbasePro import AuthAPI as CAuthAPI

# Coinbase Pro fees
app = PyCryptoBot(exchange='coinbasepro')
api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase(), app.getAPIURL())
#print (api.getTakerFee())
#print (api.getTakerFee('BTC-GBP'))
#print (api.getMakerFee())
#print (api.getMakerFee('BTC-GBP'))
#print (api.getFees('BTCGBP'))
#print (api.getFees())
print (app.getMakerFee())
print (app.getTakerFee())

# Binance fees
app = PyCryptoBot(exchange='binance')
api = BAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIURL())
#print (api.getTakerFee())
#print (api.getTakerFee('BTCGBP'))
#print (api.getMakerFee())
#print (api.getMakerFee('BTCGBP'))
#print (api.getFees('BTCGBP'))
#print (api.getFees())
print (app.getMakerFee())
print (app.getTakerFee())