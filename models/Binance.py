import math, re
import pandas as pd
from datetime import datetime, timedelta
from binance.client import Client

class PublicAPI():
    def __init__(self):
        self.client = Client()

    def __truncate(self, f, n):
        return math.floor(f * 10 ** n) / 10 ** n

    def getHistoricalData(self, market='BTCGBP', granularity=86400, iso8601start='', iso8601end=''):
        # validates the market is syntactically correct
        p = re.compile(r"^[A-Z]{6,12}$")
        if not p.match(market):
            raise TypeError('Coinbase Pro market required.')

        # validates granularity is an integer
        if not isinstance(granularity, int):
            raise TypeError('Granularity integer required.')

        # validates the granularity is supported by Coinbase Pro
        if not granularity in [60, 300, 900, 3600, 21600, 86400]:
            raise TypeError('Granularity options: 60, 300, 900, 3600, 21600, 86400.')

        # text granularity (binance format)
        if granularity == 60:
            text_granularity = '1m'
        elif granularity == 300:
            text_granularity = '5m'
        elif granularity == 900:
            text_granularity = '15m'
        elif granularity == 3600:
            text_granularity = '1h'
        elif granularity == 21600:
            text_granularity = '6h'
        elif granularity == 86400:
            text_granularity = '1d'

        # validates the ISO 8601 start date is a string (if provided)
        if not isinstance(iso8601start, str):
            raise TypeError('ISO8601 start integer as string required.')

        # validates the ISO 8601 end date is a string (if provided)
        if not isinstance(iso8601end, str):
            raise TypeError('ISO8601 end integer as string required.')

        # if only a start date is provided
        if iso8601start != '' and iso8601end == '':
            multiplier = 1
            if(granularity == 60):
                multiplier = 1
            elif(granularity == 300):
                multiplier = 5
            elif(granularity == 900):
                multiplier = 10
            elif(granularity == 3600):
                multiplier = 60
            elif(granularity == 21600):
                multiplier = 360
            elif(granularity == 86400):
                multiplier = 1440

            # calculate the end date using the granularity
            iso8601end = str((datetime.strptime(iso8601start, '%Y-%m-%dT%H:%M:%S.%f') + timedelta(minutes=granularity * multiplier)).isoformat())

        resp = self.client.get_historical_klines(market, text_granularity, '301 hours ago UTC')
            
        # convert the API response into a Pandas DataFrame
        df = pd.DataFrame(resp, columns=[ 'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'traker_buy_quote_asset_volume', 'ignore' ])
        df['market'] = market
        df['granularity'] = 3600

        # binance epoch is too long
        df['close_time'] = df['close_time'] + 1
        df['close_time'] = df['close_time'].astype(str)
        df['close_time'] = df['close_time'].str.replace(r'\d{3}$', '')   

        if(granularity == 60):
            freq = 'T'
        elif(granularity == 300):
            freq = '5T'
        elif(granularity == 900):
            freq = '15T'
        elif(granularity == 3600):
            freq = 'H'
        elif(granularity == 21600):
            freq = '6H'
        else:
            freq = 'D'

        # convert the DataFrame into a time series with the date as the index/key
        try:
            tsidx = pd.DatetimeIndex(pd.to_datetime(df['close_time'], unit='s'), dtype='datetime64[ns]', freq=freq)
            df.set_index(tsidx, inplace=True)
            df = df.drop(columns=['close_time'])
            df.index.names = ['ts']
            df['date'] = tsidx
        except ValueError:
            tsidx = pd.DatetimeIndex(pd.to_datetime(df['close_time'], unit='s'), dtype='datetime64[ns]')
            df.set_index(tsidx, inplace=True)
            df = df.drop(columns=['close_time'])
            df.index.names = ['ts']           
            df['date'] = tsidx

        # re-order columns
        df = df[[ 'date', 'market', 'granularity', 'low', 'high', 'open', 'close', 'volume' ]]

        # correct column types
        df['low'] = df['low'].astype(float)
        df['high'] = df['high'].astype(float)   
        df['open'] = df['open'].astype(float)   
        df['close'] = df['close'].astype(float)   
        df['volume'] = df['volume'].astype(float)      

        return df

    def getTicker(self, market='BTC-GBP'):
        # validates the market is syntactically correct
        p = re.compile(r"^[A-Z]{6,12}$")
        if not p.match(market):
            raise TypeError('Binance market required.')

        resp = self.client.get_symbol_ticker(symbol=market)

        if 'price' in resp:
            return float(resp['price'])

        return 0.0