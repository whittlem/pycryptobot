import sys
import math, re
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from binance.client import Client

class AuthAPI():
    def __init__(self, api_key='', api_secret='', api_url='https://api.binance.com'):
        """Binance API object model
    
        Parameters
        ----------
        api_key : str
            Your Binance account portfolio API key
        api_secret : str
            Your Binance account portfolio API secret
        """
    
        # options
        self.debug = False
        self.die_on_api_error = False

        if len(api_url) > 1 and api_url[-1] != '/':
            api_url = api_url + '/'

        valid_urls = [
            'https://api.binance.com/',
            'https://testnet.binance.vision/api/'
        ]

        # validate Binance API
        if api_url not in valid_urls:
            raise ValueError('Binance API URL is invalid')

        # validates the api key is syntactically correct
        p = re.compile(r"^[A-z0-9]{64,64}$")
        if not p.match(api_key):
            err = 'Binance API key is invalid'
            if self.debug:
                raise TypeError(err)
            else:
                raise SystemExit(err)
 
        # validates the api secret is syntactically correct
        p = re.compile(r"^[A-z0-9]{64,64}$")
        if not p.match(api_secret):
            err = 'Binance API secret is invalid'
            if self.debug:
                raise TypeError(err)
            else:
                raise SystemExit(err)

        self.mode = 'live'
        self.api_url = api_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = Client(self.api_key, self.api_secret, { 'verify': False, 'timeout': 20 })

    def getClient(self):
        return self.client

    def marketBuy(self, market='', quote_quantity=0):
        """Executes a market buy providing a funding amount"""

        # validates the market is syntactically correct
        p = re.compile(r"^[A-Z]{6,12}$")
        if not p.match(market):
            raise ValueError('Binanace market is invalid.')

        # validates quote_quantity is either an integer or float
        if not isinstance(quote_quantity, int) and not isinstance(quote_quantity, float):
            raise TypeError('The funding amount is not numeric.')

        try:
            current_price = self.getTicker(market)

            base_quantity = np.divide(quote_quantity, current_price)
            df_filters = self.getMarketInfoFilters(market)
            step_size = float(df_filters.loc[df_filters['filterType'] == 'LOT_SIZE']['stepSize'])
            precision = int(round(-math.log(step_size, 10), 0))

            # remove fees
            base_quantity = base_quantity * 0.9995

            # execute market buy
            stepper = 10.0 ** precision
            truncated = math.trunc(stepper * base_quantity) / stepper
            print ('Order quantity after rounding and fees:', truncated)
            return self.client.order_market_buy(symbol=market, quantity=truncated)
        except Exception as err:
            ts = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            print (ts, 'Binance', 'marketBuy', str(err))
            return []       

    def marketSell(self, market='', base_quantity=0):
        """Executes a market sell providing a crypto amount"""

        # validates the market is syntactically correct
        p = re.compile(r"^[A-Z]{6,12}$")
        if not p.match(market):
            raise ValueError('Binanace market is invalid.')

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError('The crypto amount is not numeric.')

        try:
            df_filters = self.getMarketInfoFilters(market)
            step_size = float(df_filters.loc[df_filters['filterType'] == 'LOT_SIZE']['stepSize'])
            precision = int(round(-math.log(step_size, 10), 0))

            # remove fees
            base_quantity = base_quantity * 0.9995

            # execute market sell
            stepper = 10.0 ** precision
            truncated = math.trunc(stepper * base_quantity) / stepper
            print ('Order quantity after rounding and fees:', truncated)
            return self.client.order_market_sell(symbol=market, quantity=truncated)
        except Exception as err:
            ts = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            print (ts, 'Binance', 'marketSell',  str(err))
            return []

    def getMarketInfo(self, market):
        # validates the market is syntactically correct
        p = re.compile(r"^[A-Z]{6,12}$")
        if not p.match(market):
            raise TypeError('Binance market required.')

        return self.client.get_symbol_info(symbol=market)

    def getMarketInfoFilters(self, market):
        return pd.DataFrame(self.client.get_symbol_info(symbol=market)['filters'])

    def getTicker(self, market):
        # validates the market is syntactically correct
        p = re.compile(r"^[A-Z]{6,12}$")
        if not p.match(market):
            raise TypeError('Binance market required.')

        resp = self.client.get_symbol_ticker(symbol=market)

        if 'price' in resp:
            return float('{:.8f}'.format(float(resp['price'])))

        return 0.0

class PublicAPI():
    def __init__(self):
        self.client = Client()

    def __truncate(self, f, n):
        return math.floor(f * 10 ** n) / 10 ** n

    def getClient(self):
        return self.client

    def getHistoricalData(self, market='BTCGBP', granularity='1h', iso8601start='', iso8601end=''):
        # validates the market is syntactically correct
        p = re.compile(r"^[A-Z]{6,12}$")
        if not p.match(market):
            raise TypeError('Binance market required.')

        # validates granularity is a string
        if not isinstance(granularity, str):
            raise TypeError('Granularity string required.')

        # validates the granularity is supported by Binance
        if not granularity in [ '1m', '5m', '15m', '1h', '6h', '1d' ]:
            raise TypeError('Granularity options: 1m, 5m, 15m. 1h, 6h, 1d')

        # validates the ISO 8601 start date is a string (if provided)
        if not isinstance(iso8601start, str):
            raise TypeError('ISO8601 start integer as string required.')

        # validates the ISO 8601 end date is a string (if provided)
        if not isinstance(iso8601end, str):
            raise TypeError('ISO8601 end integer as string required.')

        # if only a start date is provided
        if iso8601start != '' and iso8601end == '':
            multiplier = 1
            if(granularity == '1m'):
                multiplier = 1
            elif(granularity == '5m'):
                multiplier = 5
            elif(granularity == '15m'):
                multiplier = 10
            elif(granularity == '1h'):
                multiplier = 60
            elif(granularity == '6h'):
                multiplier = 360
            elif(granularity == '1d'):
                multiplier = 1440

            # calculate the end date using the granularity
            iso8601end = str((datetime.strptime(iso8601start, '%Y-%m-%dT%H:%M:%S.%f') + timedelta(minutes=granularity * multiplier)).isoformat())

        if iso8601start != '' and iso8601end != '':
            print ('Attempting to retrieve data from ' + iso8601start)
            resp = self.client.get_historical_klines(market, granularity, iso8601start)

            if len(resp) > 300:
                resp = resp[:300]
        else:
            if granularity == '5m':
                resp = self.client.get_historical_klines(market, granularity, '2 days ago UTC')
                resp = resp[-300:]
            elif granularity == '15m':
                resp = self.client.get_historical_klines(market, granularity, '4 days ago UTC')
                resp = resp[-300:]
            elif granularity == '1h':
                resp = self.client.get_historical_klines(market, granularity, '13 days ago UTC')
                resp = resp[-300:]
            elif granularity == '6h':
                resp = self.client.get_historical_klines(market, granularity, '75 days ago UTC')
                resp = resp[-300:]
            elif granularity == '1d':
                resp = self.client.get_historical_klines(market, granularity, '251 days ago UTC')
            else:
                raise Exception('Something went wrong!')
                   
        # convert the API response into a Pandas DataFrame
        df = pd.DataFrame(resp, columns=[ 'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'traker_buy_quote_asset_volume', 'ignore' ])
        df['market'] = market
        df['granularity'] = granularity

        # binance epoch is too long
        df['open_time'] = df['open_time'] + 1
        df['open_time'] = df['open_time'].astype(str)
        df['open_time'] = df['open_time'].str.replace(r'\d{3}$', '', regex=True)   

        if(granularity == '1m'):
            freq = 'T'
        elif(granularity == '5m'):
            freq = '5T'
        elif(granularity == '15m'):
            freq = '15T'
        elif(granularity == '1h'):
            freq = 'H'
        elif(granularity == '6h'):
            freq = '6H'
        else:
            freq = 'D'

        # convert the DataFrame into a time series with the date as the index/key
        try:
            tsidx = pd.DatetimeIndex(pd.to_datetime(df['open_time'], unit='s'), dtype='datetime64[ns]', freq=freq)
            df.set_index(tsidx, inplace=True)
            df = df.drop(columns=['open_time'])
            df.index.names = ['ts']
            df['date'] = tsidx
        except ValueError:
            tsidx = pd.DatetimeIndex(pd.to_datetime(df['open_time'], unit='s'), dtype='datetime64[ns]')
            df.set_index(tsidx, inplace=True)
            df = df.drop(columns=['open_time'])
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

        # reset pandas dataframe index
        df.reset_index()

        return df

    def getTicker(self, market):
        # validates the market is syntactically correct
        p = re.compile(r"^[A-Z]{6,12}$")
        if not p.match(market):
            raise TypeError('Binance market required.')

        resp = self.client.get_symbol_ticker(symbol=market)

        if 'price' in resp:
            return float('{:.8f}'.format(float(resp['price'])))

        return 0.0