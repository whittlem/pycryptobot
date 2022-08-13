import json
from models.TradingAccount import TradingAccount

with open('config.json') as config_file:
    config = json.load(config_file)

account = TradingAccount(config)
account.save_tracker_csv()
