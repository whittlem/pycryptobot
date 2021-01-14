import pandas as pd
import re, json, hmac, hashlib, time, requests, base64
from datetime import datetime, timedelta
from requests.auth import AuthBase

class CoinbaseProAPI():
    def __init__(self, api_key='', api_secret='', api_pass='', api_url='https://api.pro.coinbase.com'):
        self.debug = False

        valid_urls = [
            'https://api.pro.coinbase.com',
            'https://api.pro.coinbase.com/'
        ]

        if api_url not in valid_urls:
            raise ValueError('Coinbase Pro API URL is invalid')

        if api_url[-1] != '/':
            api_url = api_url + '/' 

        p = re.compile(r"^[a-f0-9]{32,32}$")
        if not p.match(api_key):
            err = 'Coinbase Pro API key is invalid'
            if self.debug:
                raise TypeError(err)
            else:
                raise SystemExit(err)
 
        p = re.compile(r"^[A-z0-9+\/]+==$")
        if not p.match(api_secret):
            err = 'Coinbase Pro API secret is invalid'
            if self.debug:
                raise TypeError(err)
            else:
                raise SystemExit(err)

        p = re.compile(r"^[a-z0-9]{11,11}$")
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
        df = self.authAPIGET('accounts')
        df = df[df.balance != '0.0000000000000000'] # non-zero
        df = df.reset_index()
        return df
    
    def getAccount(self, account):
        p = re.compile(r"^[a-f0-9\-]{36,36}$")
        if not p.match(account):
            err = 'Coinbase Pro account is invalid'
            if self.debug:
                raise TypeError(err)
            else:
                raise SystemExit(err)
    
        return self.authAPIGET('accounts/' + account)

    def getOrders(self, market='', action='', status='all'):
        if market != '':
            p = re.compile(r"^[A-Z]{3,4}\-[A-Z]{3,4}$")
            if not p.match(market):
                raise ValueError('Coinbase Pro market is invalid.')

        if action != '':
            if not action in ['buy', 'sell']:
                raise ValueError('Invalid order action.')

        if not status in ['open', 'pending', 'done', 'active', 'all']:
            raise ValueError('Invalid order status.')

        df = self.authAPIGET('orders?status=' + status)[['created_at','product_id','side','type','filled_size','executed_value','status']]

        df['price'] = df.apply(lambda row: (float(row.executed_value) * 100) / (float(row.filled_size) * 100), axis=1)
        df.columns = ['created_at', 'market', 'action', 'type', 'size', 'value', 'status','price']
        tsidx = pd.DatetimeIndex(pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%dT%H:%M%:%SZ'))
        df.set_index(tsidx, inplace=True)
        df = df.drop(columns=['created_at'])

        if market != '':
            df = df[df['market'] == market]

        if action != '':
            df = df[df['action'] == action]

        if status != 'all':
            df = df[df['status'] == status]

        df = df.iloc[::-1].reset_index()
        df[['size', 'value']] = df[['size', 'value']].apply(pd.to_numeric)
        return df

    def marketBuy(self, market='', fiatAmount=0):
        p = re.compile(r"^[A-Z]{3,4}\-[A-Z]{3,4}$")
        if not p.match(market):
            raise ValueError('Coinbase Pro market is invalid.')

        if not isinstance(fiatAmount, int) and not isinstance(fiatAmount, float):
            raise TypeError('The funding amount is not numeric.')

        if fiatAmount < 5:
            raise ValueError('Trade amount is too small (>= 10).')

        order = {
            'product_id': market,
            'type': 'market',
            'side': 'buy',
            'funds': fiatAmount
        }

        print (order)

        model = CoinbaseProAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)
        return model.authAPIPOST('orders', order)

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

        model = CoinbaseProAPI(self.api_key, self.api_secret, self.api_pass, self.api_url)
        return model.authAPIPOST('orders', order)

    def authAPIGET(self, uri):
        try:
            resp = requests.get(self.api_url + uri, auth=self)

            if resp.status_code != 200:
                raise Exception('GET (' + '{}'.format(resp.status_code) + ') ' + self.api_url + uri + ' - ' + '{}'.format(resp.json()['message']))

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
                raise SystemExit(err)
            else:
                raise SystemExit('ConnectionError: ' + self.api_url)
        except requests.exceptions.HTTPError as err:
            if self.debug:
                raise SystemExit(err)
            else:
                raise SystemExit('HTTPError: ' + self.api_url)
        except requests.Timeout as err:
            if self.debug:
                raise SystemExit(err)
            else:
                raise SystemExit('Timeout: ' + self.api_url) 

    def authAPIPOST(self, uri, payload):
        try:
            resp = requests.post(self.api_url + uri, json=payload, auth=self)

            if resp.status_code != 200:
                raise Exception('POST (' + '{}'.format(resp.status_code) + ') ' + self.api_url + uri + ' - ' + '{}'.format(resp.json()['message']))

            resp.raise_for_status()
            print (resp)
            return resp.json()

        except requests.ConnectionError as err:
            if self.debug:
                raise SystemExit(err)
            else:
                raise SystemExit('ConnectionError: ' + self.api_url)
        except requests.exceptions.HTTPError as err:
            if self.debug:
                raise SystemExit(err)
            else:
                raise SystemExit('HTTPError: ' + self.api_url)
        except requests.Timeout as err:
            if self.debug:
                raise SystemExit(err)
            else:
                raise SystemExit('Timeout: ' + self.api_url) 