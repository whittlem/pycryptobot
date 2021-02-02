import json
from models.CoinbaseProAPI import CoinbaseProAPI

with open('config.json') as config_file:
    config = json.load(config_file)

model = CoinbaseProAPI(config['api_key'], config['api_secret'], config['api_pass'], config['api_url'])
resp = model.authAPIGET('orders?status=all')
print (resp)