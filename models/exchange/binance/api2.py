"""Remotely control your Binance account via their API : https://binance-docs.github.io/apidocs/spot/en"""

import re
import json
import hmac
import hashlib
import time
import requests
import base64
import sys
import pandas as pd
import numpy as np
from numpy import floor
from datetime import datetime, timedelta
from requests.auth import AuthBase
from requests import Request, Session
from models.helper.LogHelper import Logger
from urllib.parse import urlencode


DEFAULT_MAKER_FEE_RATE = 0.0015 # added 0.0005 to allow for price movements
DEFAULT_TAKER_FEE_RATE = 0.0015 # added 0.0005 to allow for price movements
DEFAULT_TRADE_FEE_RATE = 0.0015 # added 0.0005 to allow for price movements
DEFAULT_GRANULARITY="1h"
SUPPORTED_GRANULARITY = ['1m', '5m', '15m', '1h', '6h', '1d']
MULTIPLIER_EQUIVALENTS = [1, 5, 15, 60, 360, 1440]
FREQUENCY_EQUIVALENTS = ["T", "5T", "15T", "H", "6H", "D"]
DEFAULT_MARKET = "BTCGBP"


class AuthAPIBase():
    def _isMarketValid(self, market: str) -> bool:
        p = re.compile(r"^[A-Z0-9]{5,12}$")
        if p.match(market):
            return True
        return False


class AuthAPI(AuthAPIBase):
    def __init__(self, api_key: str='', api_secret: str='', api_url: str='https://api.binance.com', order_history: list=[]) -> None:
        """Binance API object model
    
        Parameters
        ----------
        api_key : str
            Your Binance account portfolio API key
        api_secret : str
            Your Binance account portfolio API secret
        api_url
            Binance API URL
        """

        # options
        self.debug = False
        self.die_on_api_error = False

        valid_urls = [
            'https://api.binance.com',
            'https://api.binance.us',
            'https://testnet.binance.vision'
        ]

        # validate Binance API
        if api_url not in valid_urls:
            raise ValueError('Binance API URL is invalid')

        # validates the api key is syntactically correct
        p = re.compile(r"^[A-z0-9]{64,64}$")
        if not p.match(api_key):
            self.handle_init_error('Binance API key is invalid')
 
        # validates the api secret is syntactically correct
        p = re.compile(r"^[A-z0-9]{64,64}$")
        if not p.match(api_secret):
            self.handle_init_error('Binance API secret is invalid')

        self._api_key = api_key
        self._api_secret = api_secret
        self._api_url = api_url

        # order history
        self.order_history = order_history


    def handle_init_error(self, err: str) -> None:
        if self.debug:
            raise TypeError(err)
        else:
            raise SystemExit(err)


    def _dispatch_request(self, method: str):
        session = Session()
        session.headers.update({
            'Content-Type': 'application/json; charset=utf-8',
            'X-MBX-APIKEY': self._api_key
        })
        return {
            'GET': session.get,
            'DELETE': session.delete,
            'PUT': session.put,
            'POST': session.post,
        }.get(method, 'GET')


    def createHash(self, uri: str=''):
        return hmac.new(self._api_secret.encode('utf-8'), uri.encode('utf-8'), hashlib.sha256).hexdigest()


    def getTimestamp(self):
        return int(time.time() * 1000)


    def getAccounts(self) -> pd.DataFrame:
        """Retrieves your list of accounts"""

        # GET /api/v3/account
        resp = self.authAPI('GET', '/api/v3/account')

        if 'balances' in resp:
            balances = resp['balances']

            if isinstance(balances, list):
                df = pd.DataFrame.from_dict(balances)
            else: 
                df = pd.DataFrame(balances, index=[0])
        else:
            return pd.DataFrame()
  
        if len(df) == 0:
            return pd.DataFrame()

        # exclude accounts that are locked
        df = df[df.locked != 0.0]
        df['locked'] = df['locked'].astype(bool)

        # reset the dataframe index to start from 0
        df = df.reset_index()

        df['id'] = df['index']
        df['hold'] = 0.0
        df['profile_id'] = None
        df['available'] = df['free']

        df['id'] = df['id'].astype(object)
        df['hold'] = df['hold'].astype(object)

        # exclude accounts with a nil balance
        df = df[df.available != '0.00000000']
        df = df[df.available != '0.00']

        # rename columns
        df.columns = ['index', 'currency', 'balance', 'trading_enabled', 'id', 'hold', 'profile_id', 'available']

        return df[['index', 'id', 'currency', 'balance', 'hold', 'available', 'profile_id', 'trading_enabled' ]]


    def getAccount(self, account: int) -> pd.DataFrame:
        """Retrieves a specific account"""

        # validates the account is syntactically correct
        if not isinstance(account, int):
            self.handle_init_error('Binance account is invalid')
    
        df = self.getAccounts()
        return df[df.id == account]


    def getFees(self, market: str='') -> pd.DataFrame:
        """Retrieves a account fees"""

        # GET /api/v3/account
        resp = self.authAPI('GET', '/api/v3/account')

        if 'makerCommission' in resp and 'takerCommission' in resp:
            maker_fee_rate = resp['makerCommission'] / 10000
            taker_fee_rate = resp['takerCommission'] / 10000
        else:
            maker_fee_rate = 0.001
            taker_fee_rate = 0.001
      
        return pd.DataFrame([{ 'maker_fee_rate': maker_fee_rate, 'taker_fee_rate': taker_fee_rate, 'usd_volume': 0, 'market': '' }])


    def getMakerFee(self, market: str='') -> float:
        if len(market):
            fees = self.getFees(market)
        else:
            fees = self.getFees()
        
        if len(fees) == 0 or 'maker_fee_rate' not in fees:
            Logger.error(f"error: 'maker_fee_rate' not in fees (using {DEFAULT_MAKER_FEE_RATE} as a fallback)")
            return DEFAULT_MAKER_FEE_RATE

        return float(fees['maker_fee_rate'].to_string(index=False).strip())

    
    def getTakerFee(self, market: str='') -> float:
        if len(market) != None:
            fees = self.getFees(market)
        else:
            fees = self.getFees()

        if len(fees) == 0 or 'taker_fee_rate' not in fees:
            Logger.error(f"error: 'taker_fee_rate' not in fees (using {DEFAULT_TAKER_FEE_RATE} as a fallback)")
            return DEFAULT_TAKER_FEE_RATE

        return float(fees['taker_fee_rate'].to_string(index=False).strip())


    def getUSDVolume(self) -> float:
        fees = self.getFees()
        return float(fees['usd_volume'].to_string(index=False).strip())


    def getMarkets(self) -> list:
        """Retrieves a list of markets on the exchange"""

        # GET /api/v3/allOrders
        resp = self.authAPI('GET', '/api/v3/exchangeInfo')

        if 'symbols' in resp:
            if isinstance(resp['symbols'], list):
                df = pd.DataFrame.from_dict(resp['symbols'])
            else: 
                df = pd.DataFrame(resp['symbols'], index=[0])
        else:
            df = pd.DataFrame()

        return df[df['isSpotTradingAllowed'] == True][['symbol']].squeeze().tolist()


    def getOrders(self, market: str='', action: str='', status: str='all', order_history: list=[]) -> pd.DataFrame:
        """Retrieves your list of orders with optional filtering"""

        # if market provided
        markets = None
        if market != '':
            # validates the market is syntactically correct
            if not self._isMarketValid(market):
                raise ValueError('Binance market is invalid.')
        else:
            if len(order_history) > 0:
                full_scan = False
                self.order_history = order_history
                markets = self.order_history
            else:
                full_scan = True
                markets = self.getMarkets()

        # if action provided
        if action != '':
            # validates action is either a buy or sell
            if not action in ['buy', 'sell']:
                raise ValueError('Invalid order action.')

        # validates status is either open, canceled, pending, done, active, or all
        if not status in ['open', 'canceled', 'pending', 'done', 'active', 'all']:
            raise ValueError('Invalid order status.')

        if markets is not None:
            df = pd.DataFrame()
            for market in markets:
                if full_scan is True:
                    print (f'scanning {market} order history.')

                # GET /api/v3/allOrders
                resp = self.authAPI('GET', '/api/v3/allOrders', { 'symbol': market })

                if full_scan is True:
                    time.sleep(0.25)

                if isinstance(resp, list):
                    df_tmp = pd.DataFrame.from_dict(resp)
                else: 
                    df_tmp = pd.DataFrame(resp, index=[0])

                if full_scan is True and len(df_tmp) > 0:
                    self.order_history.append(market)
                
                if len(df_tmp) > 0:
                    df = pd.concat([df, df_tmp])

            if full_scan is True:
                print ('add to order history to prevent full scan:', self.order_history)
        else:
            # GET /api/v3/allOrders
            resp = self.authAPI('GET', '/api/v3/allOrders', { 'symbol': market })
            
            if isinstance(resp, list):
                df = pd.DataFrame.from_dict(resp)
            else: 
                df = pd.DataFrame(resp, index=[0])

        # feature engineering

        def convert_time(epoch: int=0):
            epoch_str = str(epoch)[0:10]
            return datetime.fromtimestamp(int(epoch_str))

        df.time = df['time'].map(convert_time)
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize('UTC')

        df['size'] = np.where(df['side']=='BUY', df['cummulativeQuoteQty'], np.where(df['side']=='SELL', df['executedQty'], 222))
        df['fees'] = df['size'].astype(float) * 0.001
        df['fees'] = df['fees'].astype(object)

        df['side'] = df['side'].str.lower() 

        df.rename(columns={ 
            'time': 'created_at', 
            'symbol': 'market', 
            'side': 'action', 
            'executedQty': 'filled' 
        }, errors='raise', inplace=True)

        def convert_status(status: str=''):
            if status == 'FILLED':
                return 'done'
            elif status == 'NEW':
                return 'open'
            elif status == 'PARTIALLY_FILLED':
                return 'pending'
            else:
                return status    

        df.status = df.status.map(convert_status)
        df['status'] = df['status'].str.lower()

        # select columns
        df = df[[ 'created_at', 'market', 'action', 'type', 'size', 'filled', 'fees', 'price', 'status' ]]

        # filtering
        if action != '':
            df = df[df['action'] == action]
        if status != 'all':
            df = df[df['status'] == status]

        return df


    def getTime(self) -> datetime:
        """Retrieves the exchange time"""
    
        def convert_time(epoch: int=0):
            epoch_str = str(epoch)[0:10]
            return datetime.fromtimestamp(int(epoch_str))

        try:
            # GET /api/v3/time
            resp = self.authAPI('GET', '/api/v3/time')
            return convert_time(int(resp['serverTime']))
        except:
            return None


    def authAPI(self, method: str, uri: str, payload: str={}) -> dict:
        if not isinstance(method, str):
            raise TypeError('Method is not a string.')

        if not method in ['GET', 'POST']:
            raise TypeError('Method not GET or POST.')

        if not isinstance(uri, str):
            raise TypeError('URI is not a string.')

        signed_uri = [
            '/api/v3/account',
            '/api/v3/allOrders'
        ]

        query_string = urlencode(payload, True)
        if uri in signed_uri and query_string:
            query_string = "{}&timestamp={}".format(query_string, self.getTimestamp())
        elif uri in signed_uri:
            query_string = 'timestamp={}'.format(self.getTimestamp())

        if uri in signed_uri:
            url = self._api_url + uri + '?' + query_string + '&signature=' + self.createHash(query_string)
        else:
            url = self._api_url + uri + '?' + query_string
        
        params = {'url': url, 'params': {}}

        try:
            resp = self._dispatch_request(method)(**params)

            if resp.status_code != 200:               
                resp_message = resp.json()['msg']
                message = f'{method} ({resp.status_code}) {self._api_url}{uri} - {resp_message}'
                if self.die_on_api_error:
                    raise Exception(message)
                else:
                    Logger.error(f'Error: {message}')
                    return {}

            resp.raise_for_status()
            return resp.json()
        
        except requests.ConnectionError as err:
            return self.handle_api_error(err, 'ConnectionError')

        except requests.exceptions.HTTPError as err:
            return self.handle_api_error(err, 'HTTPError')

        except requests.Timeout as err:
            return self.handle_api_error(err, 'Timeout')

        except json.decoder.JSONDecodeError as err:
            return self.handle_api_error(err, 'JSONDecodeError')


    def handle_api_error(self, err: str, reason: str) -> dict:
        if self.debug:
            if self.die_on_api_error:
                raise SystemExit(err)
            else:
                Logger.debug(err)
                return {}
        else:
            if self.die_on_api_error:
                raise SystemExit(f"{reason}: {self._api_url}")
            else:
                Logger.info(f"{reason}: {self._api_url}")
                return {}


class PublicAPI(AuthAPIBase):
    def __init__(self, api_url='https://api.binance.com') -> None:
        """Binance API object model
    
        Parameters
        ----------
        api_url
            Binance API URL
        """

        # options
        self.debug = False
        self.die_on_api_error = False

        valid_urls = [
            'https://api.binance.com',
            'https://api.binance.us',
            'https://testnet.binance.vision'
        ]

        # validate Binance API
        if api_url not in valid_urls:
            raise ValueError('Binance API URL is invalid')

        self._api_url = api_url


    def getTime(self) -> datetime:
        """Retrieves the exchange time"""
    
        def convert_time(epoch: int=0):
            epoch_str = str(epoch)[0:10]
            return datetime.fromtimestamp(int(epoch_str))

        try:
            # GET /api/v3/time
            resp = self.authAPI('GET', '/api/v3/time')
            return convert_time(int(resp['serverTime']))
        except:
            return None


    def getTicker(self, market: str=DEFAULT_MARKET) -> tuple:
       # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError('Binance market required.')

        # GET /api/v3/ticker/price
        resp = self.authAPI('GET', '/api/v3/ticker/price', { 'symbol': market })

        now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        if 'price' in resp:
            return (now, float(resp['price']))
        else:
            return (now, 0.0)


    def authAPI(self, method: str, uri: str, payload: str={}) -> dict:
        if not isinstance(method, str):
            raise TypeError('Method is not a string.')

        if not method in ['GET', 'POST']:
            raise TypeError('Method not GET or POST.')

        if not isinstance(uri, str):
            raise TypeError('URI is not a string.')

        try:
            resp = requests.get(f'{self._api_url}{uri}', params=payload)

            if resp.status_code != 200:
                resp_message = resp.json()['msg']
                message = f'{method} ({resp.status_code}) {self._api_url}{uri} - {resp_message}'
                if self.die_on_api_error:
                    raise Exception(message)
                else:
                    Logger.error(f'Error: {message}')
                    return {}

            resp.raise_for_status()
            return resp.json()
        
        except requests.ConnectionError as err:
            return self.handle_api_error(err, 'ConnectionError')

        except requests.exceptions.HTTPError as err:
            return self.handle_api_error(err, 'HTTPError')

        except requests.Timeout as err:
            return self.handle_api_error(err, 'Timeout')

        except json.decoder.JSONDecodeError as err:
            return self.handle_api_error(err, 'JSONDecodeError')


    def handle_api_error(self, err: str, reason: str) -> dict:
        if self.debug:
            if self.die_on_api_error:
                raise SystemExit(err)
            else:
                Logger.debug(err)
                return {}
        else:
            if self.die_on_api_error:
                raise SystemExit(f"{reason}: {self._api_url}")
            else:
                Logger.info(f"{reason}: {self._api_url}")
                return {}