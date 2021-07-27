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
    def __init__(self, api_key='', api_secret='', api_url='https://api.binance.com') -> None:
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

    def authAPI(self, method: str, uri: str, payload: str={}) -> dict:
        if not isinstance(method, str):
            raise TypeError('Method is not a string.')

        if not method in ['GET', 'POST']:
            raise TypeError('Method not GET or POST.')

        if not isinstance(uri, str):
            raise TypeError('URI is not a string.')

        public_uri = [
            '/api/v3/klines'
        ]

        query_string = urlencode(payload, True)
        if uri not in public_uri and query_string:
            query_string = "{}&timestamp={}".format(query_string, self.getTimestamp())
        elif uri not in public_uri:
            query_string = 'timestamp={}'.format(self.getTimestamp())

        if uri not in public_uri:
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