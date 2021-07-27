from models.PyCryptoBot import PyCryptoBot
from models.exchange.binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI

app = PyCryptoBot(exchange='binance')

api = BPublicAPI()
resp = api.authAPI('GET', '/api/v3/klines' , { 'symbol': 'BTCGBP', 'interval': '1h', 'limit': 300 })
print(resp)

api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
resp = api.authAPI('GET', '/api/v3/account')
print(resp)

api = BAuthAPI(app.getAPIKey(), app.getAPISecret())
resp = api.authAPI('GET', '/api/v3/klines' , { 'symbol': 'BTCGBP', 'interval': '1h', 'limit': 300 })
print(resp)