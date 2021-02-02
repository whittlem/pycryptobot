"""Remotely control your Coinbase Pro account via their API"""

import pandas as pd
import re, json, hmac, hashlib, time, requests, base64
from datetime import datetime, timedelta
from requests.auth import AuthBase

die_on_api_error = False

class CoinbaseProAPI():
    def __init__(self, api_key='', api_secret='', api_pass='', api_url='https://api.pro.coinbase.com'):
        """Coinbase Pro API object model
    
        Parameters
        ----------
        api_key : str
            Your Coinbase Pro account portfolio API key
        api_secret : str
            Your Coinbase Pro account portfolio API secret
        api_pass : str
            Your Coinbase Pro account portfolio API passphrase
        api_url
            Coinbase Pro API URL
        """

        # enable for verbose messaging
        self.debug = False

        valid_urls = [
            'https://api.pro.coinbase.com',
            'https://api.pro.coinbase.com/'
        ]

        # validate Coinbase Pro API
        if api_url not in valid_urls:
            raise ValueError('Coinbase Pro API URL is invalid')

        if api_url[-1] != '/':
            api_url = api_url + '/' 

        # validates the api key is syntactically correct
        p = re.compile(r"^[a-f0-9]{32,32}$")
        if not p.match(api_key):
            err = 'Coinbase Pro API key is invalid'
            if self.debug:
                raise TypeError(err)
            else:
                raise SystemExit(err)
 
        # validates the api secret is syntactically correct
        p = re.compile(r"^[A-z0-9+\/]+==$")
        if not p.match(api_secret):
            err = 'Coinbase Pro API secret is invalid'
            if self.debug:
                raise TypeError(err)
            else:
                raise SystemExit(err)

        # validates the api passphase is syntactically correct
        p = re.compile(r"^[a-z0-9]{10,11}$")
        if not p.match(api_pass):
            err = 'Coinbase Pro API passphase is invalid'
            if self.debug:
                raise TypeError(err)
            else:
                raise SystemExit(err)

        self.api_key = api_key
        self.api_secret = api_secret
        self.api_pass = api_pass
        self.api_url = api_url

    def __call__(self, request):
        """Signs the request"""

        timestamp = str(time.time())
        message = timestamp + request.method + request.path_url + (request.body or b'').decode()
        hmac_key = base64.b64decode(self.api_secret)
        signature = hmac.new(hmac_key, message.encode(), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode()

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.api_pass,
            'Content-Type': 'application/json'
        })

        return request

    def getAccounts(self):
        """Retrieves your list of accounts"""

        # GET /accounts
        df = self.authAPI('GET', 'accounts')
        
        # exclude accounts with a nil balance
        df = df[df.balance != '0.0000000000000000']

        # reset the dataframe index to start from 0
        df = df.reset_index()
        return df
    
    def getAccount(self, account):
        """Retrieves a specific account"""

        # validates the account is syntactically correct
        p = re.compile(r"^[a-f0-9\-]{36,36}$")
        if not p.match(account):
            err = 'Coinbase Pro account is invalid'
            if self.debug:
                raise TypeError(err)
            else:
                raise SystemExit(err)
    
        return self.authAPI('GET', 'accounts/' + account)

    def getOrders(self, market='', action='', status='all'):
        """Retrieves your list of orders with optional filtering"""

        # if market provided
        if market != '':
            # validates the market is syntactically correct
            p = re.compile(r"^[A-Z]{3,4}\-[A-Z]{3,4}$")
            if not p.match(market):
                raise ValueError('Coinbase Pro market is invalid.')

        # if action provided
        if action != '':
            # validates action is either a buy or sell
            if not action in ['buy', 'sell']:
                raise ValueError('Invalid order action.')

        # validates status is either open, pending, done, active, or all
        if not status in ['open', 'pending', 'done', 'active', 'all']:
            raise ValueError('Invalid order status.')

        # GET /orders?status
        resp = self.authAPI('GET', 'orders?status=' + status)
        if len(resp) > 0:
            df = resp.copy()[['created_at','product_id','side','type','filled_size','executed_value','status']]
        else:
            return pd.DataFrame()

        # calculates the price at the time of purchase
        df['price'] = df.apply(lambda row: (float(row.executed_value) * 100) / (float(row.filled_size) * 100), axis=1)

        # rename the columns
        df.columns = ['created_at', 'market', 'action', 'type', 'size', 'value', 'status','price']
        
        # convert dataframe to a time series
        tsidx = pd.DatetimeIndex(pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%dT%H:%M:%S.%Z'))
        df.set_index(tsidx, inplace=True)
        df = df.drop(columns=['created_at'])

        # if marker provided
        if market != '':
            # filter by market
            df = df[df['market'] == market]

        # if action provided
        if action != '':
            # filter by action
            df = df[df['action'] == action]

        # if status provided
        if status != 'all':
            # filter by status
            df = df[df['status'] == status]

        # reverse orders and reset index
        df = df.iloc[::-1].reset_index()

        # converts size and value to numeric type
        df[['size', 'value']] = df[['size', 'value']].apply(pd.to_numeric)
        return df

    def marketBuy(self, market='', fiatAmount=0):
        """Executes a market buy providing a funding amount"""

        # validates the market is syntactically correct
        p = re.compile(r"^[A-Z]{3,4}\-[A-Z]{3,4}$")
        if not p.match(market):
            raise ValueError('Coinbase Pro market is invalid.')

        # validates fiatAmount is either an integer or float
        if not isinstance(fiatAmount, int) and not isinstance(fiatAmount, float):
            raise TypeError('The funding amount is not numeric.')

        # funding amount needs to be greater than 10
        if fiatAmount < 10:
            raise ValueError('Trade amount is too small (>= 10).')

        order = {
            'product_id': market,
            'type': 'market',
            'side': 'buy',
            'funds': fiatAmount
        }

        if self.debug == True:
            print (order)

        # connect to authenticated coinbase pro api
        model = CoinbaseProAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)

        # place order and return result
        return model.authAPI('POST', 'orders', order)

    def marketSell(self, market='', cryptoAmount=0):
        p = re.compile(r"^[A-Z]{3,4}\-[A-Z]{3,4}$")
        if not p.match(market):
            raise ValueError('Coinbase Pro market is invalid.')

        if not isinstance(cryptoAmount, int) and not isinstance(cryptoAmount, float):
            raise TypeError('The crypto amount is not numeric.')

        order = {
            'product_id': market,
            'type': 'market',
            'side': 'sell',
            'size': cryptoAmount
        }

        print (order)

        model = CoinbaseProAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)
        return model.authAPI('POST', 'orders', order)

    def authAPI(self, method, uri, payload=''):
        if not isinstance(method, str):
            raise TypeError('Method is not a string.')

        if not method in ['GET','POST']:
             raise TypeError('Method not GET or POST.') 

        if not isinstance(uri, str):
            raise TypeError('Method is not a string.')

        try:
            if method == 'GET':
                resp = requests.get(self.api_url + uri, auth=self)
            elif method == 'POST':
                resp = requests.post(self.api_url + uri, json=payload, auth=self)

            if resp.status_code != 200:
                if die_on_api_error:
                    raise Exception(method.upper() + 'GET (' + '{}'.format(resp.status_code) + ') ' + self.api_url + uri + ' - ' + '{}'.format(resp.json()['message']))
                else:
                    print ('error:', method.upper() + ' (' + '{}'.format(resp.status_code) + ') ' + self.api_url + uri + ' - ' + '{}'.format(resp.json()['message']))
                    return pd.DataFrame()

            resp.raise_for_status()
            json = resp.json()

            if isinstance(json, list):
                df = pd.DataFrame.from_dict(json)
                return df
            else: 
                df = pd.DataFrame(json, index=[0])
                return df

        except requests.ConnectionError as err:
            if self.debug:
                if die_on_api_error:
                    raise SystemExit(err)
                else:
                    print (err)
                    return pd.DataFrame()
            else:
                if die_on_api_error:
                    raise SystemExit('ConnectionError: ' + self.api_url)
                else:
                    print ('ConnectionError: ' + self.api_url)
                    return pd.DataFrame()

        except requests.exceptions.HTTPError as err:
            if self.debug:
                if die_on_api_error:
                    raise SystemExit(err)
                else:
                    print (err)
                    return pd.DataFrame()
            else:
                if die_on_api_error:
                    raise SystemExit('HTTPError: ' + self.api_url)
                else:
                    print ('HTTPError: ' + self.api_url)
                    return pd.DataFrame()

        except requests.Timeout as err:
            if self.debug:
                if die_on_api_error:
                    raise SystemExit(err)
                else:
                    print (err)
                    return pd.DataFrame()
            else:
                if die_on_api_error:
                    raise SystemExit('Timeout: ' + self.api_url)
                else:
                    print ('Timeout: ' + self.api_url)
                    return pd.DataFrame()