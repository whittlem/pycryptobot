"""Remotely control your Coinbase Pro account via their API"""

import pandas as pd
import re, json, hmac, hashlib, time, requests, base64, sys
from datetime import datetime, timedelta
from requests.auth import AuthBase

class AuthAPIBase():
    def _isMarketValid(self, market):
        p = re.compile(r"^[1-9A-Z]{2,5}\-[1-9A-Z]{2,5}$")
        return p.match(market)

class AuthAPI(AuthAPIBase):
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

        # options
        self.debug = False
        self.die_on_api_error = False

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
            err = 'Coinbase Pro API passphrase is invalid'
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
        
        if len(df) == 0:
            return pd.DataFrame()

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

    def getFees(self):
        return self.authAPI('GET', 'fees')

    def getMakerFee(self):
        fees = self.getFees()
        return float(fees['maker_fee_rate'].to_string(index=False).strip())

    def getTakerFee(self):
        fees = self.getFees()
        return float(fees['taker_fee_rate'].to_string(index=False).strip())

    def getUSDVolume(self):
        fees = self.getFees()
        return float(fees['usd_volume'].to_string(index=False).strip())

    def getOrders(self, market='', action='', status='all'):
        """Retrieves your list of orders with optional filtering"""

        # if market provided
        if market != '':
            # validates the market is syntactically correct
            if not self._isMarketValid(market):
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
            if status == 'open':
                df = resp.copy()[[ 'created_at', 'product_id', 'side', 'type', 'size', 'price', 'status' ]]
                df['value'] = float(df['price']) * float(df['size'])
            else:
                df = resp.copy()[[ 'created_at', 'product_id', 'side', 'type', 'filled_size', 'executed_value', 'fill_fees', 'status' ]]
        else:
            return pd.DataFrame()

        # calculates the price at the time of purchase
        if status != 'open':
            df['price'] = df.apply(lambda row: (float(row.executed_value) * 100) / (float(row.filled_size) * 100) if float(row.filled_size) > 0 else 0, axis=1)

        # rename the columns
        if status == 'open':
            df.columns = [ 'created_at', 'market', 'action', 'type', 'size', 'price', 'status', 'value' ]
            df = df[[ 'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price' ]]
        else:
            df.columns = [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'fees', 'status', 'price' ]
            df = df[[ 'created_at', 'market', 'action', 'type', 'size', 'value', 'fees', 'price', 'status' ]]
            df['fees'] = df['fees'].astype(float).round(2)

        df['size'] = df['size'].astype(float)
        df['value'] = df['value'].astype(float)
        df['price'] = df['price'].astype(float)

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

    def getTime(self):
        """Retrieves the exchange time"""
    
        try:
            resp = self.authAPI('GET', 'time')
            epoch = int(resp['epoch'])
            return datetime.fromtimestamp(epoch)
        except:
            return None

    def marketBuy(self, market='', quote_quantity=0):
        """Executes a market buy providing a funding amount"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise ValueError('Coinbase Pro market is invalid.')

        # validates quote_quantity is either an integer or float
        if not isinstance(quote_quantity, int) and not isinstance(quote_quantity, float):
            raise TypeError('The funding amount is not numeric.')

        # funding amount needs to be greater than 10
        if quote_quantity < 10:
            raise ValueError('Trade amount is too small (>= 10).')

        order = {
            'product_id': market,
            'type': 'market',
            'side': 'buy',
            'funds': quote_quantity
        }

        if self.debug == True:
            print (order)

        # connect to authenticated coinbase pro api
        model = AuthAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)

        # place order and return result
        return model.authAPI('POST', 'orders', order)

    def marketSell(self, market='', base_quantity=0):
        if not self._isMarketValid(market):
            raise ValueError('Coinbase Pro market is invalid.')

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError('The crypto amount is not numeric.')

        order = {
            'product_id': market,
            'type': 'market',
            'side': 'sell',
            'size': base_quantity
        }

        print (order)

        model = AuthAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)
        return model.authAPI('POST', 'orders', order)

    def limitSell(self, market='', base_quantity=0, futurePrice=0):
        if not self._isMarketValid(market):
            raise ValueError('Coinbase Pro market is invalid.')

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError('The crypto amount is not numeric.')

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError('The future crypto price is not numeric.')

        order = {
            'product_id': market,
            'type': 'limit',
            'side': 'sell',
            'size': base_quantity,
            'price': futurePrice
        }

        print (order)

        model = AuthAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)
        return model.authAPI('POST', 'orders', order)

    def cancelOrders(self, market=''):
        if not self._isMarketValid(market):
            raise ValueError('Coinbase Pro market is invalid.')

        model = AuthAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)
        return model.authAPI('DELETE', 'orders')

    def authAPI(self, method, uri, payload=''):
        if not isinstance(method, str):
            raise TypeError('Method is not a string.')

        if not method in ['DELETE','GET','POST']:
             raise TypeError('Method not DELETE, GET or POST.') 

        if not isinstance(uri, str):
            raise TypeError('Method is not a string.')

        try:
            if method == 'DELETE':
                resp = requests.delete(self.api_url + uri, auth=self)
            elif method == 'GET':
                resp = requests.get(self.api_url + uri, auth=self)
            elif method == 'POST':
                resp = requests.post(self.api_url + uri, json=payload, auth=self)

            if resp.status_code != 200:
                if self.die_on_api_error:
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
                if self.die_on_api_error:
                    raise SystemExit(err)
                else:
                    print (err)
                    return pd.DataFrame()
            else:
                if self.die_on_api_error:
                    raise SystemExit('ConnectionError: ' + self.api_url)
                else:
                    print ('ConnectionError: ' + self.api_url)
                    return pd.DataFrame()

        except requests.exceptions.HTTPError as err:
            if self.debug:
                if self.die_on_api_error:
                    raise SystemExit(err)
                else:
                    print (err)
                    return pd.DataFrame()
            else:
                if self.die_on_api_error:
                    raise SystemExit('HTTPError: ' + self.api_url)
                else:
                    print ('HTTPError: ' + self.api_url)
                    return pd.DataFrame()

        except requests.Timeout as err:
            if self.debug:
                if self.die_on_api_error:
                    raise SystemExit(err)
                else:
                    print (err)
                    return pd.DataFrame()
            else:
                if self.die_on_api_error:
                    raise SystemExit('Timeout: ' + self.api_url)
                else:
                    print ('Timeout: ' + self.api_url)
                    return pd.DataFrame()

        except json.decoder.JSONDecodeError as err:
            if self.debug:
                if self.die_on_api_error:
                    raise SystemExit(err)
                else:
                    print (err)
                    return pd.DataFrame()
            else:
                if self.die_on_api_error:
                    raise SystemExit('JSONDecodeError: ' + self.api_url)
                else:
                    print ('JSONDecodeError: ' + self.api_url)
                    return pd.DataFrame()          

class PublicAPI(AuthAPIBase):
    def __init__(self):
        # options
        self.debug = False
        self.die_on_api_error = False

        self.api_url = 'https://api.pro.coinbase.com/'

    def getHistoricalData(self, market='BTC-GBP', granularity=86400, iso8601start='', iso8601end=''):
        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError('Coinbase Pro market required.')

        # validates granularity is an integer
        if not isinstance(granularity, int):
            raise TypeError('Granularity integer required.')

        # validates the granularity is supported by Coinbase Pro
        if not granularity in [ 60, 300, 900, 3600, 21600, 86400 ]:
            raise TypeError('Granularity options: 60, 300, 900, 3600, 21600, 86400')

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

        resp = self.authAPI('GET','products/' + market + '/candles?granularity=' + str(granularity) + '&start=' + iso8601start + '&end=' + iso8601end)
        
        # convert the API response into a Pandas DataFrame
        df = pd.DataFrame(resp, columns=[ 'epoch', 'low', 'high', 'open', 'close', 'volume' ])
        # reverse the order of the response with earliest last
        df = df.iloc[::-1].reset_index()

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
            tsidx = pd.DatetimeIndex(pd.to_datetime(df['epoch'], unit='s'), dtype='datetime64[ns]', freq=freq)
            df.set_index(tsidx, inplace=True)
            df = df.drop(columns=['epoch','index'])
            df.index.names = ['ts']
            df['date'] = tsidx
        except ValueError:
            tsidx = pd.DatetimeIndex(pd.to_datetime(df['epoch'], unit='s'), dtype='datetime64[ns]')
            df.set_index(tsidx, inplace=True)
            df = df.drop(columns=['epoch','index'])
            df.index.names = ['ts']           
            df['date'] = tsidx
        
        df['market'] = market
        df['granularity'] = granularity

        # re-order columns
        df = df[[ 'date', 'market', 'granularity', 'low', 'high', 'open', 'close', 'volume' ]]

        return df

    def getTicker(self, market='BTC-GBP'):
       # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError('Coinbase Pro market required.')

        resp = self.authAPI('GET','products/' + market + '/ticker')
        if 'price' in resp:
            return float(resp['price'])

        return 0.0

    def getTime(self):
        """Retrieves the exchange time"""
    
        try:
            resp = self.authAPI('GET', 'time')
            epoch = int(resp['epoch'])
            return datetime.fromtimestamp(epoch)
        except:
            return None

    def authAPI(self, method, uri, payload=''):
        if not isinstance(method, str):
            raise TypeError('Method is not a string.')

        if not method in ['GET', 'POST']:
            raise TypeError('Method not GET or POST.')

        if not isinstance(uri, str):
            raise TypeError('Method is not a string.')

        try:
            if method == 'GET':
                resp = requests.get(self.api_url + uri)
            elif method == 'POST':
                resp = requests.post(self.api_url + uri, json=payload)

            if resp.status_code != 200:
                if self.die_on_api_error:
                    raise Exception(method.upper() + 'GET (' + '{}'.format(resp.status_code) + ') ' + self.api_url + uri + ' - ' + '{}'.format(resp.json()['message']))
                else:
                    print('error:', method.upper() + ' (' + '{}'.format(resp.status_code) + ') ' + self.api_url + uri + ' - ' + '{}'.format(resp.json()['message']))
                    return pd.DataFrame()

            resp.raise_for_status()
            json = resp.json()
            return json

        except requests.ConnectionError as err:
            if self.debug:
                if self.die_on_api_error:
                    raise SystemExit(err)
                else:
                    print(err)
                    return pd.DataFrame()
            else:
                if self.die_on_api_error:
                    raise SystemExit('ConnectionError: ' + self.api_url)
                else:
                    print('ConnectionError: ' + self.api_url)
                    return pd.DataFrame()

        except requests.exceptions.HTTPError as err:
            if self.debug:
                if self.die_on_api_error:
                    raise SystemExit(err)
                else:
                    print(err)
                    return pd.DataFrame()
            else:
                if self.die_on_api_error:
                    raise SystemExit('HTTPError: ' + self.api_url)
                else:
                    print('HTTPError: ' + self.api_url)
                    return pd.DataFrame()

        except requests.Timeout as err:
            if self.debug:
                if self.die_on_api_error:
                    raise SystemExit(err)
                else:
                    print(err)
                    return pd.DataFrame()
            else:
                if self.die_on_api_error:
                    raise SystemExit('Timeout: ' + self.api_url)
                else:
                    print('Timeout: ' + self.api_url)
                    return pd.DataFrame()

        except json.decoder.JSONDecodeError as err:
            if self.debug:
                if self.die_on_api_error:
                    raise SystemExit(err)
                else:
                    print (err)
                    return pd.DataFrame()
            else:
                if self.die_on_api_error:
                    raise SystemExit('JSONDecodeError: ' + self.api_url)
                else:
                    print ('JSONDecodeError: ' + self.api_url)
                    return pd.DataFrame()