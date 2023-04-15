"""Remotely control your Kucoin account via their API"""

from ctypes import wstring_at
from genericpath import exists
import re
import json
import hmac
import hashlib
import time
import math
import requests
import base64
import sys
import os
import pandas as pd
from numpy import floor
from datetime import datetime, timezone
from requests import Request
from views.PyCryptoBot import RichText
from threading import Thread
from websocket import create_connection, WebSocketConnectionClosedException
from models.exchange.Granularity import Granularity
from urllib import parse

MARGIN_ADJUSTMENT = 0.0025
DEFAULT_MAKER_FEE_RATE = 0.018
DEFAULT_TAKER_FEE_RATE = 0.018
DEFAULT_TRADE_FEE_RATE = 0.018  # added 0.0005 to allow for self.price movements
MINIMUM_TRADE_AMOUNT = 10
SUPPORTED_GRANULARITY = [
    "1min",
    "3min",
    "5min",
    "15min",
    "30min",
    "1hour",
    "6hour",
    "1day",
]
FREQUENCY_EQUIVALENTS = ["T", "5T", "15T", "H", "6H", "D"]
MAX_GRANULARITY = max(SUPPORTED_GRANULARITY)
DEFAULT_MARKET = "BTC-USDT"


class AuthAPIBase:
    def _is_market_valid(self, market: str) -> bool:
        p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
        if p.match(market):
            return True
        return False

    def convert_time(self, epoch: int = 0):
        if math.isnan(epoch) is False:
            epoch_str = str(epoch)[0:10]
            return datetime.fromtimestamp(int(epoch_str))
        else:
            return datetime.fromtimestamp(epoch)


class AuthAPI(AuthAPIBase):
    def __init__(
        self, api_key="", api_secret="", api_passphrase="", api_url="https://api.kucoin.com", cache_path="cache", use_cache=False, app: object = None
    ) -> None:
        """kucoin API object model

        Parameters
        ----------
        api_key : str
            Your kucoin account portfolio API key
        api_secret : str
            Your kucoin account portfolio API secret
        api_passphrase : str
            Your kucoin account portfolio API passphrase
        api_url
            kucoin API URL
        """

        # options
        self.die_on_api_error = False

        valid_urls = [
            "https://api.kucoin.com",
            "https://api.kucoin.com/",
            "https://openapi-sandbox.kucoin.com",
            "https://openapi-sandbox.kucoin.com/",
        ]

        # validate Kucoin API
        if api_url not in valid_urls:
            raise ValueError("Kucoin API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        # validates the api key is syntactically correct
        p = re.compile(r"^[a-f0-9]{24,24}$")
        if not p.match(api_key):
            self.handle_init_error("Kucoin API key is invalid", app=app)

        # validates the api secret is syntactically correct
        p = re.compile(r"^[A-z0-9-]{36,36}$")
        if not p.match(api_secret):
            self.handle_init_error("Kucoin API secret is invalid", app=app)

        # validates the api passphase is syntactically correct
        p = re.compile(r"^[A-z0-9#$%=@!{},`~&*()<>?.:;_|^/+\[\]]{8,32}$")
        if not p.match(api_passphrase):
            self.handle_init_error("Kucoin API passphrase is invalid", app=app)

        # app
        self.app = app

        self._api_key = api_key
        self._api_secret = api_secret
        self._api_passphrase = api_passphrase
        self._api_url = api_url

        if use_cache:
            # Make the cache folder if it doesn't exist

            if not os.path.exists(cache_path):
                os.makedirs(cache_path)

            self._cache_path = cache_path
            self._cache_filepath = cache_path + os.path.sep + "kucoin_order_cache.json"
            self._cache_lock_filepath = cache_path + os.path.sep + "kucoin_order_cache.lock"

        self.usekucoincache = use_cache
        # use pagination if cache is enabled
        self.usepagination = use_cache

    def handle_init_error(self, err: str, app: object = None) -> None:
        """Handle initialisation error"""

        if app is not None and app.debug is True:
            raise TypeError(err)
        else:
            raise SystemExit(err)

    def __call__(self, request) -> Request:
        """Signs the request"""

        timestamp = int(time.time() * 1000)
        body = (request.body or b"").decode()
        message = f"{timestamp}{request.method}{request.path_url}{body}"

        signature = base64.b64encode(
            hmac.new(
                self._api_secret.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        )
        passphrase = base64.b64encode(
            hmac.new(
                self._api_secret.encode("utf-8"),
                self._api_passphrase.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        )

        request.headers.update(
            {
                "KC-API-SIGN": signature,
                "KC-API-TIMESTAMP": str(timestamp),
                "KC-API-KEY": self._api_key,
                "KC-API-PASSPHRASE": passphrase,
                "KC-API-KEY-VERSION": str("2"),
            }
        )

        return request

    def get_accounts(self) -> pd.DataFrame:
        """Retrieves your list of accounts"""

        # GET /accounts
        df = self.auth_api("GET", "api/v1/accounts?type=trade")

        if len(df) == 0:
            return pd.DataFrame()

        # exclude accounts with a nil balance
        # df = df[df.balance != "0.0000000000000000"]
        df = df[df.balance > "0"]

        # reset the dataframe index to start from 0
        df = df.reset_index()
        return df

    def get_account(self, account: str) -> pd.DataFrame:
        """Retrieves a specific account"""

        # validates the account is syntactically correct
        p = re.compile(r"^[a-f0-9\-]{24,24}$")
        if not p.match(self.account):
            self.handle_init_error("Kucoin account is invalid", app=self.app)

        return self.auth_api("GET", f"api/v1/accounts/{account}")

    def get_fees(self, market: str = "") -> pd.DataFrame:
        """Retrieves market fees"""

        df = self.auth_api("GET", "api/v1/base-fee")

        if len(market):
            df["market"] = market
        else:
            df["market"] = ""

        return df

    def get_maker_fee(self, market: str = "") -> float:
        """Retrieves maker fee"""

        if len(market):
            fees = self.get_fees(market)
        else:
            fees = self.get_fees()

        if len(fees) == 0 or "makerFeeRate" not in fees:
            if self.app:
                RichText.notify(f"error: 'makerFeeRate' not in fees (using {DEFAULT_MAKER_FEE_RATE} as a fallback)", self.app, "error")
            return DEFAULT_MAKER_FEE_RATE

        return float(fees["makerFeeRate"].to_string(index=False).strip())

    def get_taker_fee(self, market: str = "") -> float:
        """Retrieves taker fee"""

        if len(market) is not None:
            fees = self.get_fees(market)
        else:
            fees = self.get_fees()

        if len(fees) == 0 or "takerFeeRate" not in fees:
            if self.app:
                RichText.notify(f"error: 'takerFeeRate' not in fees (using {DEFAULT_TAKER_FEE_RATE} as a fallback)", self.app, "error")
            return DEFAULT_TAKER_FEE_RATE

        return float(fees["takerFeeRate"].to_string(index=False).strip())

    def get_usd_volume(self) -> float:
        """Retrieves USD volume"""

        fees = self.get_fees()
        return float(fees["usd_volume"].to_string(index=False).strip())

    def getMarkets(self) -> list:
        """Retrieves a list of markets on the exchange"""

        # GET /api/v1/symbols
        resp = self.auth_api("GET", "api/v1/symbols")

        if isinstance(resp, list):
            df = pd.DataFrame.from_dict(resp)
        else:
            df = pd.DataFrame(resp)

        # exclude pairs not available for trading
        df = df[df["enableTrading"] == True]  # noqa: E712

        # reset the dataframe index to start from 0
        df = df.reset_index()
        return df

    def get_orders(self, market: str = "", action: str = "", status: str = "all") -> pd.DataFrame:
        """Retrieves your list of orders with optional filtering"""

        # if market provided
        if market != "":
            # validates the market is syntactically correct
            if not self._is_market_valid(market):
                raise ValueError("Kucoin market is invalid.")

        # if action provided
        if action != "":
            # validates action is either a buy or sell
            if action not in ["buy", "sell"]:
                raise ValueError("Invalid order action.")

        # validates status is either open, pending, done, active, or all
        if status not in ["done", "active", "all"]:
            raise ValueError("Invalid order status.")

        # Update Cache if needed before continuing on any bot for Kucoin
        if self.usekucoincache:
            self.buildOrderHistoryCache()

        # GET /orders?status
        resp = self.auth_api("GET", f"api/v1/orders?symbol={market}", use_order_cache=self.usekucoincache, use_pagination=self.usepagination)
        if len(resp) > 0:
            if status == "active":
                df = resp.copy()[
                    [
                        "created_at",
                        "symbol",
                        "side",
                        "type",
                        "size",
                        "price",
                        "isActive",
                    ]
                ]
                df["value"] = float(df["price"]) * float(df["size"]) - (float(df["price"]) * MARGIN_ADJUSTMENT)
            else:
                if "funds" in resp:
                    df = resp.copy()[
                        [
                            "createdAt",
                            "symbol",
                            "side",
                            "type",
                            "size",
                            "funds",
                            "dealSize",
                            "dealFunds",
                            "fee",
                            "isActive",
                            "price",
                        ]
                    ]
                else:
                    # manual limit orders do not contain 'specified_funds'
                    df_tmp = resp.copy()
                    df_tmp["funds"] = None
                    df = df_tmp[
                        [
                            "createdAt",
                            "symbol",
                            "side",
                            "type",
                            "size",
                            "funds",
                            "dealSize",
                            "dealFunds",
                            "fee",
                            "isActive",
                            "price",
                        ]
                    ]
        else:
            return pd.DataFrame()

        # replace null NaN values with 0
        df.copy().fillna(0, inplace=True)

        df_tmp = df.copy()
        df_tmp["price"] = 0.0
        df_tmp["size"] = df_tmp["size"].astype(float)
        df_tmp["funds"] = df_tmp["funds"].astype(float)
        df_tmp["dealSize"] = df_tmp["dealSize"].astype(float)
        df_tmp["dealFunds"] = df_tmp["dealFunds"].astype(float)
        df_tmp["fee"] = df_tmp["fee"].astype(float)
        df = df_tmp

        df["isActive"] = df.copy().apply(lambda row: str("done") if not bool(row.isActive) else str("active"), axis=1)

        # calculates the self.price at the time of purchase
        if status != "active":
            df["price"] = df.copy().apply(
                lambda row: (float(row.dealFunds) * 100) / (float(row.dealSize) * 100) if float(row.dealSize) > 0 else 0,
                axis=1,
            )
            # df.loc[df['filled_size'] > 0, 'price'] = (df['executed_value'] * 100) / (df['filled_size'] * 100)

        # rename the columns
        if status == "active":
            df.columns = [
                "created_at",
                "market",
                "action",
                "type",
                "size",
                "price",
                "status",
                "value",
            ]
            df = df[
                [
                    "created_at",
                    "market",
                    "action",
                    "type",
                    "size",
                    "value",
                    "status",
                    "price",
                ]
            ]
            df["size"] = df["size"].astype(float).round(8)
        else:
            df.columns = [
                "created_at",
                "market",
                "action",
                "type",
                "size",
                "funds",
                "filled",
                "dealFunds",
                "fees",
                "status",
                "price",
            ]
            df = df[
                [
                    "created_at",
                    "market",
                    "action",
                    "type",
                    "size",
                    "funds",
                    "filled",
                    "dealFunds",
                    "fees",
                    "status",
                    "price",
                ]
            ]
            df.columns = [
                "created_at",
                "market",
                "action",
                "type",
                "size",
                "funds",
                "filled",
                "dealFunds",
                "fees",
                "status",
                "price",
            ]
            df_tmp = df.copy()
            df_tmp["filled"] = df_tmp["filled"].astype(float).round(8)
            df_tmp["size"] = df_tmp["size"].astype(float).round(8)
            df_tmp["fees"] = df_tmp["fees"].astype(float).round(8)
            df_tmp["price"] = df_tmp["price"].astype(float).round(8)
            df = df_tmp

        # convert dataframe to a time series
        tsidx = pd.DatetimeIndex(pd.to_datetime(df["created_at"], unit="ms").dt.strftime("%Y-%m-%dT%H:%M:%S.%Z"))
        df.set_index(tsidx, inplace=True)
        df = df.drop(columns=["created_at"])

        # if marker provided
        if market != "":
            # filter by market
            df = df[df["market"] == market]

        # if action provided
        if action != "":
            # filter by action
            df = df[df["action"] == action]

        # if status provided
        if status != "all":
            # filter by status
            df = df[df["status"] == status]

        # reverse orders and reset index
        df = df.iloc[::-1].reset_index()

        if len(df) > 0:
            if df["type"][0] == "market":
                df["size"] = df["funds"]

        # for sell orders size is filled
        df["size"] = df["size"].fillna(df["filled"])

        return df

    def market_buy(self, market: str = "", quote_quantity: float = 0) -> pd.DataFrame:
        """Executes a market buy providing a funding amount"""

        # validates the market is syntactically correct
        if not self._is_market_valid(market):
            raise ValueError("Kucoin market is invalid.")

        # validates quote_quantity is either an integer or float
        if not isinstance(quote_quantity, int) and not isinstance(quote_quantity, float):
            raise TypeError("The funding amount is not numeric.")

        # funding amount needs to be greater than 10
        if quote_quantity < MINIMUM_TRADE_AMOUNT:
            raise ValueError(f"Trade amount is too small (>= {MINIMUM_TRADE_AMOUNT}).")

        dt_obj = datetime.strptime(str(datetime.now()), "%Y-%m-%d %H:%M:%S.%f")
        millisec = dt_obj.timestamp() * 1000

        order = {
            "clientOid": str(millisec),
            "symbol": market,
            "type": "market",
            "side": "buy",
            "funds": self.market_quote_increment(market, quote_quantity),
        }

        # place order and return result
        return self.auth_api("POST", "api/v1/orders", order)

    def market_sell(self, market: str = "", base_quantity: float = 0) -> pd.DataFrame:
        """Executes a market sell providing a crypto amount"""

        if not self._is_market_valid(market):
            raise ValueError("Kucoin market is invalid.")

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError("The crypto amount is not numeric.")

        dt_obj = datetime.strptime(str(datetime.now()), "%Y-%m-%d %H:%M:%S.%f")
        millisec = dt_obj.timestamp() * 1000

        order = {
            "clientOid": str(millisec),
            "symbol": market,
            "type": "market",
            "side": "sell",
            "size": self.market_base_increment(market, base_quantity),
        }

        model = AuthAPI(self._api_key, self._api_secret, self._api_passphrase, self._api_url)
        return model.auth_api("POST", "api/v1/orders", order)

    def limit_sell(self, market: str = "", base_quantity: float = 0, future_price: float = 0) -> pd.DataFrame:
        """Initiates a limit sell order"""

        if not self._is_market_valid(market):
            raise ValueError("Kucoin market is invalid.")

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError("The crypto amount is not numeric.")

        if not isinstance(future_price, int) and not isinstance(future_price, float):
            raise TypeError("The future crypto self.price is not numeric.")

        order = {
            "product_id": market,
            "type": "limit",
            "side": "sell",
            "size": self.market_base_increment(market, base_quantity),
            "price": future_price,
        }

        model = AuthAPI(self._api_key, self._api_secret, self._api_passphrase, self._api_url)
        return model.auth_api("POST", "orders", order)

    def get_trade_fee(self, market: str) -> float:
        """Retrieves the trade fees"""

        # GET /sapi/v1/asset/tradeFee
        resp = self.auth_api(
            "GET",
            f"api/v1/trade-fees?symbols={market}",
        )

        if len(resp) == 1 and "takerFeeRate" in resp:
            return float(resp["takerFeeRate"])
        else:
            return DEFAULT_TRADE_FEE_RATE

    def cancel_orders(self, market: str = "") -> pd.DataFrame:
        """Cancels an order"""

        if not self._is_market_valid(market):
            raise ValueError("Kucoin market is invalid.")

        model = AuthAPI(self._api_key, self._api_secret, self._api_passphrase, self._api_url)
        return model.auth_api("DELETE", "orders")

    def market_base_increment(self, market, amount) -> float:
        """Retrieves the market base increment"""
        pMarket = market.split("-")[0]
        product = self.auth_api("GET", f"api/v1/symbols?{pMarket}")

        for ind in product.index:
            if product["symbol"][ind] == market:
                if "baseIncrement" not in product:
                    return amount

                base_increment = str(product["baseIncrement"][ind])
                break

        if "." in str(base_increment):
            nb_digits = len(str(base_increment).split(".")[1])
        else:
            nb_digits = 0

        return floor(amount * 10**nb_digits) / 10**nb_digits

    def market_quote_increment(self, market, amount) -> float:
        """Retrieves the market quote increment"""

        products = self.auth_api("GET", f"api/v1/symbols?{market}")

        for ind in products.index:
            if products["symbol"][ind] == market:
                if "quoteIncrement" not in products:
                    return amount

                quote_increment = str(products["quoteIncrement"][ind])
                break

        if "." in str(quote_increment):
            nb_digits = len(str(quote_increment).split(".")[1])
        else:
            nb_digits = 0

        return floor(amount * 10**nb_digits) / 10**nb_digits

    def validateJSONFile(self, jsonFile):
        if exists(jsonFile):
            with open(jsonFile) as json_data:
                try:
                    json.load(json_data)
                except ValueError:
                    return False
                return True
        else:
            return False

    def buildOrderHistoryCache(self, days_to_keep=45, enable_purge=True) -> bool:
        """Intelligently builds an order history cache to use in subsequent api calls"""

        if exists(self._cache_lock_filepath):
            # Lock file exists - wait
            last_modified_lock = datetime.now() - datetime.fromtimestamp(os.path.getmtime(os.path.join(self._cache_lock_filepath)))
            while exists(self._cache_lock_filepath):
                try:
                    last_modified_lock = datetime.now() - datetime.fromtimestamp(os.path.getmtime(os.path.join(self._cache_lock_filepath)))
                    if last_modified_lock > 1799:
                        # lock has existed for longer than 30 mins - try and salvage
                        break
                except Exception:
                    pass
                time.sleep(5)

        if exists(self._cache_filepath):
            last_modified = datetime.now() - datetime.fromtimestamp(os.path.getmtime(os.path.join(self._cache_filepath)))

            # If last build over a day ago
            if last_modified.seconds < 21599:
                # print (f"Last modified cache: {last_modified.seconds}")
                return True

        # pd.set_option('display.max_rows', 4000)

        now = int(round(time.time() * 1000))
        hour = 1 * 3600 * 1000
        day = 24 * hour
        week = 7 * day
        month = day * 30  # noqa: F841
        # Date of Kucoin Starting
        since = 1504224000000
        end = min(since + week, now)  # noqa: F841

        purgeAfter = now - (day * days_to_keep)
        # endAt = min(since + week, now)
        startAt = now - (30 * day)

        break_build = False
        last_timestamp_check = now - (12 * hour)

        # Validate the json cache file
        if not self.validateJSONFile(self._cache_filepath):
            # Delete the json file so it can be rebuilt
            if exists(self._cache_filepath):
                os.remove(self._cache_filepath)

        # If a previous cache file exists - load it up into the df
        if exists(self._cache_filepath):
            df = pd.read_json(self._cache_filepath)
        else:
            df = pd.DataFrame()

        if not df.empty:
            if len(df.columns) > 1:
                if "createdAt" in df.columns:
                    df = df.sort_values(by="createdAt", ascending=True)
                    startAt = df.createdAt.iloc[-1] + 1

        while (now - (12 * hour)) > startAt:

            st_dt = datetime.fromtimestamp(startAt / 1000.0)
            st_str = st_dt.strftime("%m/%d/%Y, %H:%M:%S")
            print(f"Start at HR: {st_str}")

            # Create the lock file
            if not exists(self._cache_lock_filepath):
                with open(self._cache_lock_filepath, "w") as fp:
                    pass
                fp.close()

            print("Doing historic orders build... ")
            resp = self.auth_api("GET", f"api/v1/orders?startAt={startAt}", use_pagination=True)
            if last_timestamp_check == startAt:
                # print ("Hit Last timestamp check")
                resp = self.auth_api("GET", "api/v1/orders?", use_pagination=True)
                break_build = True
            if len(resp) > 0:
                df = df.append(resp)
                df = df.drop_duplicates("id")
                df = df.reset_index(drop=True)

                if "createdAt" in df.columns:
                    df = df.sort_values(by="createdAt", ascending=True)
                    startAt = df.createdAt.iloc[-1] + 1
                    last_timestamp_check = startAt

            if break_build:
                break

            time.sleep(5)

        df = df.drop_duplicates("id")
        # Purge anything older than a month
        if enable_purge:
            df = df[df["createdAt"] > purgeAfter]
        # Do final sort
        if "createdAt" in df.columns:
            df = df.sort_values(by="createdAt", ascending=True)
            startAt = df.createdAt.iloc[-1] + 1
        df = df.reset_index(drop=True)

        # Remove json cache - and then recreate with latest data
        if exists(self._cache_filepath):
            os.remove(self._cache_filepath)
        time.sleep(1)
        df.to_json(self._cache_filepath, orient="records")
        time.sleep(1)
        # Delete Lock File
        if exists(self._cache_lock_filepath):
            os.remove(self._cache_lock_filepath)
        return df

    def auth_api(
        self,
        method: str,
        uri: str,
        payload: str = "",
        use_order_cache: bool = False,
        getting_pages: bool = False,
        page_num: int = 1,
        per_page: int = 500,
        use_pagination: bool = False,
    ) -> pd.DataFrame:
        """Initiates a REST API call"""

        if not isinstance(method, str):
            raise TypeError("Method is not a string.")

        if method not in ["DELETE", "GET", "POST"]:
            raise TypeError("Method not DELETE, GET or POST.")

        if not isinstance(uri, str):
            raise TypeError("URI is not a string.")

        reason, msg = (None, None)
        trycnt, maxretry, connretry = (1, 5, 10)
        while trycnt <= connretry:
            try:
                # Store the original URI for use later
                orig_uri = uri
                symbol = ""

                if method == "GET" and use_pagination and getting_pages:
                    # We are getting this and subsequent pages
                    uri = uri + f"&currentPage={page_num}&pageSize={per_page}"
                elif method == "GET" and use_pagination and not getting_pages:
                    uri = uri + f"&currentPage=1&pageSize={per_page}"

                # Get the symbol from the URL if it exists in parameters
                if use_order_cache and ("symbol" in (self._api_url + uri)) and not ("symbols" in (self._api_url + uri)):
                    try:
                        symbol = parse.parse_qs(parse.urlparse(self._api_url + uri).query)["symbol"][0]
                    except Exception:
                        pass
                    if len(symbol) == 0:
                        symbol = None
                else:
                    symbol = None

                if method == "DELETE":
                    resp = requests.delete(self._api_url + uri, auth=self)
                elif method == "GET":
                    resp = requests.get(self._api_url + uri, auth=self)
                elif method == "POST":
                    resp = requests.post(self._api_url + uri, json=payload, auth=self)

                trycnt += 1
                resp.raise_for_status()

                if resp.status_code == 200 and len(resp.json()) > 0:
                    mjson = resp.json()
                    if isinstance(mjson, list):
                        df = pd.DataFrame.from_dict(mjson)

                    if "data" in mjson:
                        mjson = mjson["data"]

                    if use_pagination:
                        # Setup vars
                        current_page = None
                        max_pages = None
                        page_size = None

                        if "currentPage" in mjson:
                            current_page = mjson["currentPage"]
                        if "totalPage" in mjson:
                            max_pages = mjson["totalPage"]
                        if "pageSize" in mjson:
                            page_size = mjson["pageSize"]  # noqa: F841

                    if "items" in mjson:
                        if isinstance(mjson["items"], list):
                            df = pd.DataFrame.from_dict(mjson["items"])
                        else:
                            df = pd.DataFrame(mjson["items"], index=[0])
                    elif "data" in mjson:
                        if isinstance(mjson, list):
                            df = pd.DataFrame.from_dict(mjson)
                        else:
                            df = pd.DataFrame(mjson, index=[0])
                    else:
                        if isinstance(mjson, list):
                            df = pd.DataFrame.from_dict(mjson)
                        else:
                            df = pd.DataFrame(mjson, index=[0])

                    if "code" in df.columns:
                        if int(df["code"].values[0]) != 200000:
                            raise RuntimeError(df["msg"].iloc[0])

                    # If a previous cache file exists - load it up into the df
                    if use_order_cache and exists(self._cache_filepath) and "v1/orders" in uri and method == "GET":
                        if exists(self._cache_lock_filepath):
                            # Lock file exists - wait
                            while exists(self._cache_lock_filepath):
                                time.sleep(5)
                        cache_df = pd.read_json(self._cache_filepath)
                        df = df.append(cache_df)
                        df = df.drop_duplicates("id")
                    else:
                        cache_df = None

                    if use_pagination:
                        # Get subsequent pages - if in original AuthAPI call
                        if max_pages is not None:
                            if (not getting_pages) and (not use_order_cache) and (max_pages > current_page):
                                page_counter = 1
                                while page_counter <= max_pages:
                                    time.sleep(10)
                                    page_counter += 1
                                    append_df = self.auth_api(
                                        method=method, uri=orig_uri, payload=payload, getting_pages=True, page_num=page_counter, per_page=per_page
                                    )
                                    df = df.append(append_df)
                                    if page_counter == max_pages:
                                        break

                        # Sort by created Date and only return symbol if that was requested
                        if symbol is not None:
                            df = df[df["symbol"] == symbol]
                        if "createdAt" in df.columns:
                            df = df.sort_values(by="createdAt", ascending=False)

                    return df

                else:
                    msg = f"Kucoin auth_api Error: {method.upper()} ({resp.status_code}) {self._api_url} {uri} - {resp.json()['msg']}"
                    reason = "Invalid Response"

            except requests.ConnectionError as err:
                reason, msg = ("ConnectionError", err)

            except requests.exceptions.HTTPError as err:
                reason, msg = ("HTTPError", err)

            except requests.Timeout as err:
                reason, msg = ("TimeoutError", err)

            except json.decoder.JSONDecodeError as err:
                reason, msg = ("JSONDecodeError", err)

            except RuntimeError as err:
                reason, msg = ("RuntimeError", err)

            except Exception as err:
                reason, msg = ("GeneralException", err)

            if trycnt >= maxretry:
                if reason in ("ConnectionError", "HTTPError") and trycnt <= connretry:
                    if self.app:
                        RichText.notify(f"{reason}:  URI: {uri} trying again.  Attempt: {trycnt}", self.app, "error")
                    if trycnt > 5:
                        time.sleep(30)
                else:
                    if msg is None:
                        msg = f"Unknown Kucoin Private API Error: call to {uri} attempted {trycnt} times, resulted in error"
                    if reason is None:
                        reason = "Unknown Error"
                    return self.handle_api_error(msg, reason)
            else:
                if self.app:
                    RichText.notify(f"{str(msg)} - trying again.  Attempt: {trycnt}", self.app, "error")
                time.sleep(15)

        else:
            return self.handle_api_error(f"Kucoin API Error: call to {uri} attempted {trycnt} times without valid response", "Kucoin Private API Error")

    def handle_api_error(self, err: str, reason: str, app: object = None) -> pd.DataFrame:
        """Handle API errors"""

        if app is not None and app.debug is True:
            if self.die_on_api_error:
                raise SystemExit(err)
            else:
                if self.app:
                    RichText.notify(err, self.app, "debug")
                return pd.DataFrame()
        else:
            if self.die_on_api_error:
                raise SystemExit(f"{reason}: {self._api_url}")
            else:
                if self.app:
                    RichText.notify(f"{reason}: {self._api_url}", self.app, "error")
                return pd.DataFrame()


class PublicAPI(AuthAPIBase):
    def __init__(self, api_url: str = "https://api.kucoin.com", app: object = None) -> None:
        # options
        self.die_on_api_error = False
        self._api_url = api_url

        valid_urls = [
            "https://api.kucoin.com",
            "https://api.kucoin.com/",
            "https://openapi-sandbox.kucoin.com",
            "https://openapi-sandbox.kucoin.com/",
        ]

        # validate Kucoin API
        if api_url not in valid_urls:
            raise ValueError("Kucoin API URL is invalid")

        # app
        self.app = app

        if api_url[-1] != "/":
            api_url = api_url + "/"

        self._api_url = api_url

    def get_historical_data(
        self,
        market: str = DEFAULT_MARKET,
        granularity: Granularity = Granularity.ONE_HOUR,
        websocket=None,
        iso8601start: str = "",
        iso8601end: str = "",
    ) -> pd.DataFrame:
        """Retrieves historical market data"""

        # validates the market is syntactically correct
        if not self._is_market_valid(market):
            raise TypeError("Kucoin market required.")

        # validates granularity is an enum
        if not isinstance(granularity, Granularity):
            raise TypeError("Granularity Enum required.")

        # validates the ISO 8601 start date is a string (if provided)
        if not isinstance(iso8601start, str):
            raise TypeError("ISO8601 start integer as string required.")

        # validates the ISO 8601 end date is a string (if provided)
        if not isinstance(iso8601end, str):
            raise TypeError("ISO8601 end integer as string required.")

        using_websocket = False
        if websocket is not None:
            if websocket.candles is not None:
                try:
                    df = websocket.candles.loc[websocket.candles["market"] == market]
                    using_websocket = True
                except Exception:
                    using_websocket = False

        # if not using websocket
        if websocket is None or (websocket is not None and using_websocket is False):

            resp = {}
            trycnt, maxretry = (0, 5)
            while trycnt < maxretry:

                if iso8601start != "" and iso8601end == "":
                    startTime = int(datetime.timestamp(datetime.strptime(iso8601start, "%Y-%m-%dT%H:%M:%S")))
                    resp = self.auth_api(
                        "GET",
                        f"api/v1/market/candles?type={granularity.to_medium}&symbol={market}&startAt={startTime}",
                    )
                elif iso8601start != "" and iso8601end != "":
                    startTime = int(datetime.timestamp(datetime.strptime(iso8601start, "%Y-%m-%dT%H:%M:%S")))
                    endTime = int(datetime.timestamp(datetime.strptime(iso8601end, "%Y-%m-%dT%H:%M:%S")))
                    resp = self.auth_api(
                        "GET",
                        f"api/v1/market/candles?type={granularity.to_medium}&symbol={market}&startAt={startTime}&endAt={endTime}",
                    )
                else:
                    resp = self.auth_api(
                        "GET",
                        f"api/v1/market/candles?type={granularity.to_medium}&symbol={market}",
                    )

                if "code" in resp and resp["code"] != "200000":
                    raise ValueError(f"Kucoin API error: {resp['msg']} ({market})")

                trycnt += 1
                try:
                    if "data" in resp:
                        # convert the API response into a Pandas DataFrame
                        df = pd.DataFrame(
                            resp["data"],
                            columns=["time", "open", "close", "high", "low", "volume", "turnover"],
                        )
                        # reverse the order of the response with earliest last
                        df = df.iloc[::-1].reset_index()

                        try:
                            freq = granularity.get_frequency
                        except Exception:
                            freq = "D"

                        # convert the DataFrame into a time series with the date as the index/key
                        tsidx = pd.DatetimeIndex(pd.to_datetime(df["time"], unit="s"), dtype="datetime64[ns]", freq=freq)
                        df.set_index(tsidx, inplace=True)
                        df = df.drop(columns=["time", "index"])
                        df.index.names = ["ts"]
                        df["date"] = tsidx

                        break
                    else:
                        if trycnt >= (maxretry):
                            raise Exception(f"Kucoin API Error for Historical Data - attempted {trycnt} times - API did not return correct response")
                        time.sleep(15)

                except Exception as err:
                    if trycnt >= (maxretry):
                        raise Exception(f"Kucoin API Error for Historical Data - attempted {trycnt} times - Error: {err}")
                    time.sleep(15)

            df["market"] = market
            df["granularity"] = granularity.to_medium

            # re-order columns
            df = df[["date", "market", "granularity", "low", "high", "open", "close", "volume"]]

            df["low"] = df["low"].astype(float).fillna(0)
            df["high"] = df["high"].astype(float).fillna(0)
            df["open"] = df["open"].astype(float).fillna(0)
            df["close"] = df["close"].astype(float).fillna(0)
            df["volume"] = df["volume"].astype(float).fillna(0)

            # reset pandas dataframe index
            df.reset_index()
        return df

    def get_ticker(self, market: str = DEFAULT_MARKET, websocket=None) -> tuple:
        """Retrieves the market ticker"""

        # validates the market is syntactically correct
        if not self._is_market_valid(market):
            raise TypeError("Kucoin market required.")

        # now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        if websocket is not None and websocket.tickers is not None:
            try:
                row = websocket.tickers.loc[websocket.tickers["market"] == market]
                ticker_date = datetime.strptime(
                    re.sub(r".0*$", "", str(row["date"].values[0])),
                    "%Y-%m-%dT%H:%M:%S",
                ).strftime("%Y-%m-%d %H:%M:%S")
                ticker_price = float(row["price"].values[0])
            except Exception:
                pass

            if ticker_date is None:
                ticker_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            return (ticker_date, ticker_price)

        resp = {}
        trycnt, maxretry = (1, 5)
        while trycnt <= maxretry:
            try:
                resp = self.auth_api("GET", f"api/v1/market/orderbook/level1?symbol={market}")
                return (
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    float(resp["data"]["price"]),
                )

            except ValueError as err:
                trycnt += 1
                if trycnt >= maxretry:
                    if self.app:
                        RichText.notify(f"Kucoin API Error for Get Ticker - attempted {trycnt} times - Error: {err}", self.app, "warning")
                    return (datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), 0.0)
                time.sleep(15)

    def get_time(self) -> datetime:
        """Retrieves the exchange time"""

        try:
            resp = self.auth_api("GET", "api/v1/timestamp")
            # epoch = int(resp["data"] / 1000)
            return self.convert_time(int(resp["data"]))
            # return datetime.fromtimestamp(epoch)
        except Exception:
            return None

    def getSocketToken(self):
        return self.auth_api("POST", "api/v1/bullet-public")

    def get_markets_24hr_stats(self) -> pd.DataFrame():
        """Retrieves exchange markets 24hr stats"""

        try:
            return self.auth_api("GET", "api/v1/market/allTickers")
        except Exception:
            return pd.DataFrame()

    def auth_api(self, method: str, uri: str, payload: str = "") -> dict:
        """Initiates a REST API call"""

        if not isinstance(method, str):
            raise TypeError("Method is not a string.")

        if method not in ["GET", "POST"]:
            raise TypeError("Method not GET or POST.")

        if not isinstance(uri, str):
            raise TypeError("URI is not a string.")

        # If API returns an error status code, retry request up to 5 times
        reason, msg = (None, None)
        trycnt, maxretry, connretry = (1, 5, 10)
        while trycnt <= connretry:
            try:
                if method == "GET":
                    resp = requests.get(self._api_url + uri)
                elif method == "POST":
                    resp = requests.post(self._api_url + uri, json=payload)

                trycnt += 1
                resp.raise_for_status()

                if resp.status_code == 200 and len(resp.json()) > 0:
                    return resp.json()
                else:
                    msg = f"{method} ({resp.status_code}) {self._api_url}{uri} - {resp.json()['msg']}"
                    reason = "Invalid Response"

            except requests.ConnectionError as err:
                reason, msg = ("ConnectionError", err)

            except requests.exceptions.HTTPError as err:
                reason, msg = ("HTTPError", err)

            except requests.Timeout as err:
                reason, msg = ("TimeoutError", err)

            except json.decoder.JSONDecodeError as err:
                reason, msg = ("JSONDecodeError", err)

            except Exception as err:
                reason, msg = ("GeneralException", err)

            if trycnt >= maxretry:
                if reason in ("ConnectionError", "HTTPError") and trycnt <= connretry:
                    if self.app:
                        RichText.notify(f"{reason}:  URI: {uri} trying again.  Attempt: {trycnt}", self.app, "error")
                    if trycnt > 5:
                        time.sleep(30)
                else:
                    if msg is None:
                        msg = f"Unknown Kucoin Public API Error: call to {uri} attempted {trycnt} times, resulted in error"
                    if reason is None:
                        reason = "Unknown Error"
                    return self.handle_api_error(msg, reason)
            else:
                time.sleep(15)

        else:
            return self.handle_api_error(f"Kucoin API Error: call to {uri} attempted {trycnt} times without valid response", "Kucoin Public API Error")

    def handle_api_error(self, err: str, reason: str, app: object = None) -> dict:
        """Handler for API errors"""

        if app is not None and app.debug is True:
            if self.die_on_api_error:
                raise SystemExit(err)
            else:
                if self.app:
                    RichText.notify(err, self.app, "error")
                return {}
        else:
            if self.die_on_api_error:
                raise SystemExit(f"{reason}: {self._api_url}")
            else:
                if self.app:
                    RichText.notify(f"{reason}: {self._api_url}", self.app, "info")
                return {}


class WebSocket(AuthAPIBase):
    def __init__(
        self,
        markets=None,
        # granularity=None,
        granularity: Granularity = Granularity.ONE_HOUR,
        api_url="https://api.kucoin.com",
        ws_url="wss://ws-api.kucoin.com",
        app: object = None,
    ) -> None:
        valid_urls = [
            "https://api.kucoin.com",
            "https://api.kucoin.com/",
            "https://openapi-sandbox.kucoin.com",
        ]

        # validate Coinbase Pro API
        if api_url not in valid_urls:
            raise ValueError("Coinbase Pro API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        valid_ws_urls = [
            "wss://ws-api.kucoin.com",
        ]

        # validate Coinbase Pro Websocket URL
        if ws_url not in valid_ws_urls:
            raise ValueError("Kucoin WebSocket URL is invalid")

        # app
        self.app = app

        self._ws_url = ws_url
        self._api_url = api_url

        self.markets = None
        self.granularity = granularity
        self.type = "subscribe"
        self.stop = True
        self.error = None
        self.ws = None
        self.thread = None
        self.start_time = None
        self.time_elapsed = 0

    def start(self):
        def _go():
            self._connect()
            self._listen()
            self._disconnect()

        self.stop = False
        self.on_open()
        self.thread = Thread(target=_go)
        self.keepalive = Thread(target=self._keepalive)
        self.thread.start()

    def _connect(self):
        if self.markets is None:
            print("Error: no market specified!")
            sys.exit()
        elif not isinstance(self.markets, list):
            self.markets = [self.markets]

        self.ws = create_connection(self._ws_url + f"/endpoint?token={self.token}")
        self.ws.send(json.dumps({"type": "subscribe", "topic": f"/market/ticker:{','.join(self.markets)}", "privateChannel": "false", "response": "true"}))

        self.start_time = datetime.now()

    def _keepalive(self, interval=30):
        if (self.ws is not None) and (hasattr(self.ws, "connected")):
            while self.ws.connected:
                self.ws.ping("keepalive")
                time.sleep(interval)

    def _listen(self):
        self.keepalive.start()
        while not self.stop:
            try:
                data = self.ws.recv()
                if data != "":
                    msg = json.loads(data)
                else:
                    msg = {}
            # testing to see if it helps JSON errors
            except ValueError as e:
                self.on_error(e)
            except Exception as e:
                self.on_error(e)
            else:
                self.on_message(msg)

    def _disconnect(self):
        try:
            if self.ws:
                self.ws.close()
        except WebSocketConnectionClosedException:
            pass
        finally:
            self.keepalive.join()

    def close(self):
        self.stop = True
        self.start_time = None
        self.time_elapsed = 0
        self._disconnect()
        self.thread.join()

    def on_open(self):
        if self.app:
            RichText.notify("-- Websocket Subscribed! --", self.app, "info")

    def on_close(self):
        if self.app:
            RichText.notify("-- Websocket Closed --", self.app, "info")

    def on_message(self, msg):
        if self.app:
            RichText.notify(msg, self.app, "info")

    def on_error(self, e, data=None):
        if self.app:
            RichText.notify(e, self.app, "error")
            RichText.notify("{} - data: {}".format(e, data), self.app, "error")

        self.stop = True
        try:
            self.ws = None
            self.tickers = None
            self.candles = None
            self.start_time = None
            self.time_elapsed = 0
        except Exception:
            pass

    def getStartTime(self) -> datetime:
        return self.start_time

    def get_timeElapsed(self) -> int:
        return self.time_elapsed


class WebSocketClient(WebSocket):
    def __init__(
        self,
        markets: list = [DEFAULT_MARKET],
        granularity: Granularity = Granularity.ONE_HOUR,
        api_url="https://api.kucoin.com/",
        ws_url: str = "wss://ws-api.kucoin.com",
        app: object = None,
    ) -> None:
        if len(markets) == 0:
            raise ValueError("A list of one or more markets is required.")

        for market in markets:
            # validates the market is syntactically correct
            if not self._is_market_valid(market):
                raise ValueError("Kucoin market is invalid.")

        # validates granularity is an integer
        if not isinstance(granularity.to_medium, str):
            raise TypeError("Granularity string required.")

        # validates the granularity is supported by Coinbase Pro
        if granularity.to_medium not in SUPPORTED_GRANULARITY:
            raise TypeError("Granularity options: " + ", ".join(map(str, SUPPORTED_GRANULARITY)))

        valid_urls = [
            "https://api.kucoin.com",
            "https://api.kucoin.com/",
            "https://openapi-sandbox.kucoin.com",
            "https://openapi-sandbox.kucoin.com/",
        ]

        # validate Coinbase Pro API
        if api_url not in valid_urls:
            raise ValueError("Kucoin API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        valid_ws_urls = [
            "wss://ws-api.kucoin.com",
        ]

        # validate Kucoin Websocket URL
        if ws_url not in valid_ws_urls:
            raise ValueError("Kucoin WebSocket URL is invalid")

        # app
        self.app = app

        self._ws_url = ws_url

        self.markets = markets
        self.granularity = granularity
        self.tickers = None
        self.candles = None
        self.start_time = None
        self.time_elapsed = 0

        api = PublicAPI(api_url)
        ts = api.getSocketToken()
        # print("token: " + ts["data"]["token"])
        self.token = ts["data"]["token"]

    def on_open(self):
        self.message_count = 0

    def on_message(self, msg):
        if self.start_time is not None:
            self.time_elapsed = round((datetime.now() - self.start_time).total_seconds())
        # if any new errors, len(msg) > 0 is new
        if len(msg) > 0 and "data" in msg and "time" in msg["data"] and "price" in msg["data"]:
            # create dataframe from websocket message
            df = pd.DataFrame(
                columns=["date", "market", "price"],
                data=[
                    [
                        # pd.to_datetime(msg["data"]["time"], origin="1970-01-01"), #.dt.strftime("%Y-%m-%d %H:%M:%S"),
                        self.convert_time(msg["data"]["time"]),
                        self.markets[0],
                        msg["data"]["price"],
                    ]
                ],
            )

            # set column types

            df["date"] = df["date"].astype("datetime64[ns]")
            df["price"] = df["price"].astype("float64")

            # form candles
            df["candle"] = df["date"].dt.floor(freq=self.granularity.frequency)

            # candles dataframe is empty
            if self.candles is None:
                resp = PublicAPI().get_historical_data(str(df["market"].values[0]), self.granularity)
                if len(resp) > 0:
                    self.candles = resp
                else:
                    # create dataframe from websocket message
                    self.candles = pd.DataFrame(
                        columns=[
                            "date",
                            "market",
                            "granularity",
                            "open",
                            "high",
                            "close",
                            "low",
                            "volume",
                        ],
                        data=[
                            [
                                self.convert_time(df["candle"].values[0]),
                                df["market"].values[0],
                                self.granularity.to_integer,
                                df["price"].values[0],
                                df["price"].values[0],
                                df["price"].values[0],
                                df["price"].values[0],
                                msg["data"]["size"],
                            ]
                        ],
                    )
            # candles dataframe contains some data
            else:
                # check if the current candle exists
                candle_exists = ((self.candles["date"] == df["candle"].values[0]) & (self.candles["market"] == df["market"].values[0])).any()
                if not candle_exists:
                    # populate historical data via api if it does not exist
                    if len(self.candles[self.candles["market"] == df["market"].values[0]]) == 0:
                        resp = PublicAPI().get_historical_data(df["market"].values[0], self.granularity)
                        if len(resp) > 0:
                            df_new_candle = resp
                        else:
                            # create dataframe from websocket message
                            df_new_candle = pd.DataFrame(
                                columns=[
                                    "date",
                                    "market",
                                    "granularity",
                                    "open",
                                    "high",
                                    "close",
                                    "low",
                                    "volume",
                                ],
                                data=[
                                    [
                                        self.convert_time(df["candle"].values[0]),
                                        df["market"].values[0],
                                        self.granularity.to_integer,
                                        df["price"].values[0],
                                        df["price"].values[0],
                                        df["price"].values[0],
                                        df["price"].values[0],
                                        msg["data"]["size"],
                                    ]
                                ],
                            )

                    else:
                        df_new_candle = pd.DataFrame(
                            columns=[
                                "date",
                                "market",
                                "granularity",
                                "open",
                                "high",
                                "close",
                                "low",
                                "volume",
                            ],
                            data=[
                                [
                                    df["candle"].values[0],
                                    df["market"].values[0],
                                    self.granularity.to_integer,
                                    df["price"].values[0],
                                    df["price"].values[0],
                                    df["price"].values[0],
                                    df["price"].values[0],
                                    msg["data"]["size"],
                                ]
                            ],
                        )
                    df_new_candle.index = df_new_candle["date"]
                    self.candles = pd.concat([self.candles, df_new_candle])
                    df_new_candle = None
                else:
                    candle = self.candles[((self.candles["date"] == df["candle"].values[0]) & (self.candles["market"] == df["market"].values[0]))]

                    # set high on high
                    if float(df["price"].values[0]) > float(candle.high.values[0]):
                        self.candles.at[candle.index.values[0], "high"] = df["price"].values[0]

                    self.candles.at[candle.index.values[0], "close"] = df["price"].values[0]

                    # set low on low
                    if float(df["price"].values[0]) < float(candle.low.values[0]):
                        self.candles.at[candle.index.values[0], "low"] = df["price"].values[0]

                    # increment candle base volume
                    self.candles.at[candle.index.values[0], "volume"] = float(candle["volume"].values[0]) + float(msg["data"]["size"])

            # insert first entry
            if self.tickers is None and len(df) > 0:
                self.tickers = df
            # append future entries without duplicates
            elif self.tickers is not None and len(df) > 0:
                self.tickers = pd.concat([self.tickers, df]).drop_duplicates(subset="market", keep="last").reset_index(drop=True)

            # convert dataframes to a time series
            tsidx = pd.DatetimeIndex(pd.to_datetime(self.tickers["date"]).dt.strftime("%Y-%m-%dT%H:%M:%S.%Z"))
            self.tickers.set_index(tsidx, inplace=True)
            self.tickers.index.name = "ts"

            tsidx = pd.DatetimeIndex(pd.to_datetime(self.candles["date"]).dt.strftime("%Y-%m-%dT%H:%M:%S.%Z"))
            self.candles.set_index(tsidx, inplace=True)
            self.candles.index.name = "ts"

            # set correct column types
            self.candles["open"] = self.candles["open"].astype("float64")
            self.candles["high"] = self.candles["high"].astype("float64")
            self.candles["close"] = self.candles["close"].astype("float64")
            self.candles["low"] = self.candles["low"].astype("float64")
            self.candles["volume"] = self.candles["volume"].astype("float64")

            # keep last 300 candles per market
            self.candles = self.candles.groupby("market").tail(300)

            # print (f'{msg["time"]} {msg["product_id"]} {msg["price"]}')
            # print(json.dumps(msg, indent=4, sort_keys=True))

        self.message_count += 1
