import json
import pandas as pd
import numpy as np
from models.CoinbasePro import AuthAPI

with open('config.json') as config_file:
    config = json.load(config_file)

model = AuthAPI(config['api_key'], config['api_secret'], config['api_pass'], config['api_url'])

df = model.getOrders()

df_tracker = pd.DataFrame()

last_action = ''
for market in df['market'].sort_values().unique():
    df_market = df[df['market'] == market]

    df_buy = pd.DataFrame()
    df_sell = pd.DataFrame()

    pair = 0
    for index, row in df_market.iterrows():
        if row['action'] == 'buy':
            pair = 1

        if pair == 1 and (row['action'] != last_action):
            if row['action'] == 'buy':
                df_buy = row
            elif row['action'] == 'sell':
                df_sell = row
                       
        if row['action'] == 'sell' and len(df_buy) != 0:
            df_pair = pd.DataFrame([
                [
                    df_sell['status'], 
                    df_buy['market'], 
                    df_buy['created_at'], 
                    df_buy['type'], 
                    df_buy['size'],
                    df_buy['value'], 
                    df_buy['price'],
                    df_sell['created_at'],
                    df_sell['type'], 
                    df_sell['size'], 
                    df_sell['value'], 
                    df_sell['price']                    
                ]], columns=[ 'status', 'market', 
                    'buy_at', 'buy_type', 'buy_size', 'buy_value', 'buy_price',
                    'sell_at', 'sell_type', 'sell_size', 'sell_value', 'sell_price' 
                ])
            df_tracker = df_tracker.append(df_pair, ignore_index=True)
            pair = 0
        
        last_action = row['action']

df_tracker['profit'] = np.subtract(df_tracker['sell_value'], df_tracker['buy_value'])
df_tracker['margin'] = np.multiply(np.true_divide(df_tracker['profit'], df_tracker['sell_value']), 100)
df_sincebot = df_tracker[df_tracker['buy_at'] > '2021-02-1']

df_sincebot.to_csv('tracker.csv', index=False)