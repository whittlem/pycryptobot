import sys

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.exchange.coinbase import AuthAPI as CBAuthAPI  # noqa: E402
from models.exchange.Granularity import Granularity  # noqa: E402

app = PyCryptoBot(exchange="coinbase")

model = CBAuthAPI(app.api_key, app.api_secret, app.api_url, app=app)

# df = model.get_accounts()
# print(df)
# df = model.get_account("687c96ec-24bd-5607-9682-0f6947771112")
# print(df)

# df = model.get_products()
# print(df)

# df = model.get_fees()
# df = model.get_maker_fee()
# df = model.get_taker_fee()
# print(df)

df = model.get_historical_data("BTC-GBP", 60)
# df = model.get_historical_data("BTC-GBP", 300)
# df = model.get_historical_data("BTC-GBP", 900)
# df = model.get_historical_data("ADA-GBP", 3600)
# df = model.get_historical_data("ADA-GBP", 3600, iso8601start="2023-03-25T01:00:00", iso8601end="2023-03-25T05:00:00")
# df = model.get_historical_data("ADA-GBP", 3600, iso8601start="2023-03-25T01:00:00")
# df = model.get_historical_data("ADA-GBP", 3600, iso8601end="2023-03-25T01:00:00")
# df = model.get_historical_data("BTC-GBP", 21600)
# df = model.get_historical_data("BTC-GBP", 86400)
print(df)

# df = model.auth_api("GET", "api/v3/brokerage/orders/historical/batch")
# print(df)


"""
import http.client
import hmac
import hashlib
import time
import json
import datetime
import base64
import numpy as np

timestamp = str(int(time.time()))

secretKey = ""
accessKey = ""

conn = http.client.HTTPSConnection("api.coinbase.com")
method = "GET"
print ("method: ", method)
path = "/api/v3/brokerage/accounts"
print ("path: ", path)
int_order_id = np.random.randint(2**63)
print ("int_order_id: ", int_order_id)
payload = ""
print ("payload: ", payload)
message = timestamp + method + path.split("?")[0] + str(payload)
print ("message: ", message)
signature = hmac.new(secretKey.encode("utf-8"), message.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
print ("signature: ", signature)

headers = {"CB-ACCESS-KEY": accessKey, "CB-ACCESS-TIMESTAMP": timestamp, "CB-ACCESS-SIGN": signature, "accept": "application/json"}
print ("headers: ", headers)

print(payload)
conn.request(method, path, payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))


method:  GET
path:  /api/v3/brokerage/accounts
int_order_id:  1227264743523673463
payload:
message:  1679314615GET/api/v3/brokerage/accounts
signature:  51fbe3227bf74954b9fa2394230807ce841ddb5f5cd784fc5c45754dabc81227
headers:  {'CB-ACCESS-KEY': '', 'CB-ACCESS-TIMESTAMP': '1679314615', 'CB-ACCESS-SIGN': '51fbe3227bf74954b9fa2394230807ce841ddb5f5cd784fc5c45754dabc81227', 'accept': 'application/json'}
"""

"""
import requests
from requests.auth import AuthBase
import hmac
import hashlib
import time
import json


api_key = ""
api_secret = ""

api_url = 'https://api.coinbase.com'
orderep = '/api/v3/brokerage/accounts'
payload = ""


class CBAuth(AuthBase):
    def __init__(self, api_secret, api_key, orderep):
        # setup any auth-related data here
        self.api_secret = api_secret
        self.api_key = api_key
        self.api_url = orderep
        print(api_secret, api_key, api_url)

    def __call__(self, request):
        print ("method", request.method)
        print ("path", orderep)
        print ("payload", payload)
        timestamp = str(int(time.time()))
        message = timestamp + request.method + self.api_url + json.dumps(payload)
        print("message", message)
        signature = hmac.new(api_secret.encode("utf-8"), message.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
        print ("signature", signature)

        request.headers.update({
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': api_key,
            'accept': "application/json"

        })
        print("headers", request.headers)
        return request

auth = CBAuth(api_secret, api_key, orderep)
print(api_secret, api_key, orderep)

print(api_url)
print(orderep)
print(api_url + orderep)
r = requests.get(api_url + orderep, json=payload, auth=auth)  # .json()
print(r.json())
"""
