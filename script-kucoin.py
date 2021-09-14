from datetime import datetime
from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount
from models.AppState import AppState
from models.exchange.kucoin import AuthAPI as AuthAPI, PublicAPI as PublicAPI

api_key = "6113d087bc85c200065a7667"
api_secret = "ff76c450-757a-4ff9-8105-524b9d7a965d"
api_passphrase = "Pa55word01!"
url = 'https://openapi-sandbox.kucoin.com'

app = PyCryptoBot(exchange='kucoin')

api = PublicAPI('https://api.kucoin.com')

#ts = api.getTime()
#print("getTime: " + str(ts))

#ticker = api.getTicker('BTC-USDT')
#print("getTicker: ")
#print(ticker)

#df = api.getHistoricalData('ETH-USDT', '1hour', '', '')
#print("getHistoricalData: fast")
#print(df)
#df = api.getHistoricalData('ETH-USDT', '1hour', '2021-08-03T00:00:00', '2021-08-17T00:00:00')
#print("getHistoricalData: fast-sample")
#print(df)


api = AuthAPI(api_key, api_secret, api_passphrase, url)

#df = api.getAccounts()
#print("getAccounts:")
#print(df)

#df = api.getAccount('6113cf2c4270260006395aad')
#print(df)


#df = api.getFees()
#print(df)


#df = api.getMakerFee()
#print(df)


#df = api.getTakerFee()
#print(df)

#df = api.getOrders('BTC-USDT', '', 'done')
#print(df)

#df = api.getMarkets()
#print (df)


#fee = api.getTradeFee('BTC-USDT')
#print (fee)


#df = api.getOrders('BTC-USDT')
#print(df)

resp = api.marketSell('BTC-USDT', 0.0002)
print (resp)


#resp = api.marketBuy('BTC-USDT', 100)
#print (resp)
#resp = api.marketBuy('XRP-USDT', 100)
#print (resp)

#account = TradingAccount(app)
#balance = account.getBalance('USDT')
#print (balance)


app = PyCryptoBot(exchange='kucoin')
account = TradingAccount(app)
state = AppState(app, account)
state.minimumOrderBase()
state.minimumOrderQuote()
