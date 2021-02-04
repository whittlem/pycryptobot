from models.CoinbasePro import PublicAPI

model = PublicAPI()
resp = model.authAPI('GET','products/BTC-GBP/candles?granularity=3600')
print (resp)