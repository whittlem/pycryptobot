import json
from models.CoinbaseProAPI import CoinbaseProAPI

with open('config.json') as config_file:
    config = json.load(config_file)

model = CoinbaseProAPI(config['api_key'], config['api_secret'], config['api_pass'], config['api_url'])
data = model.getAccounts()
data = model.getAccount('b0d0824f-01d4-42a3-bff8-365ea451907c')
print (data[['currency','balance']])