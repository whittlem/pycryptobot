import pandas as pd
import re, json, hmac, hashlib, time, requests, base64
from requests.auth import AuthBase

class CoinbaseProAPI():
    def __init__(self, api_key='', api_secret='', api_pass='', api_url='https://api.pro.coinbase.com/'):
        self.debug = False

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
        df = self.authAPIRequest('accounts')
        return df[df.balance != '0.0000000000000000'] # non-zero
    
    def getAccount(self, account):
        p = re.compile(r"^[a-f0-9\-]{36,36}$")
        if not p.match(account):
            err = 'Coinbase Pro account is invalid'
            if self.debug:
                raise TypeError(err)
            else:
                raise SystemExit(err)
    
        return self.authAPIRequest('accounts/' + account)

    def authAPIRequest(self, uri):
        try:
            resp = requests.get(self.api_url + uri, auth=self)

            if resp.status_code != 200:
                raise Exception('GET ' + self.api_url + ' {}'.format(resp.status_code))

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