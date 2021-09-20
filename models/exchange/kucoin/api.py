"""Remotely control your Kucoin account via their API"""

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
from requests import Request
from urllib3.exceptions import HeaderParsingError
from models.helper.LogHelper import Logger

MARGIN_ADJUSTMENT = 0.0025
DEFAULT_MAKER_FEE_RATE = 0.018
DEFAULT_TAKER_FEE_RATE = 0.018
DEFAULT_TRADE_FEE_RATE = 0.018  # added 0.0005 to allow for price movements
MINIMUM_TRADE_AMOUNT = 10
SUPPORTED_GRANULARITY = ["1min", "3min", "5min", "15min", "30min", "1hour", "6hour", "1day"]
FREQUENCY_EQUIVALENTS = ["T", "5T", "15T", "H", "6H", "D"]
MAX_GRANULARITY = max(SUPPORTED_GRANULARITY)
DEFAULT_MARKET = "BTC"


class AuthAPIBase:
    def _isMarketValid(self, market: str) -> bool:
        p = re.compile(r"^[1-9A-Z]{2,5}\-[1-9A-Z]{2,5}$")
        if p.match(market):
            return True
        return False

class AuthAPI(AuthAPIBase):
    def __init__(
        self,
        api_key="",
        api_secret="",
        api_passphrase="",
        api_url="",
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
        self.debug = True
        self.die_on_api_error = False

        valid_urls = [
            "https://api.kucoin.com",
            "https://api.kucoin.com/",
            "https://openapi-sandbox.kucoin.com",
            "https://openapi-sandbox.kucoin.com/",
        ]

        # validate Kucoin API
        if api_url not in valid_urls:
            raise ValueError("kucoin API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        # validates the api key is syntactically correct
        p = re.compile(r"^[a-f0-9]{24,24}$")
        if not p.match(api_key):
            self.handle_init_error("Kucoin API key is invalid")

        # validates the api secret is syntactically correct
        p = re.compile(r"^[A-z0-9-]{36,36}$")
        if not p.match(api_secret):
            self.handle_init_error("Kucoin API secret is invalid")

        # validates the api passphase is syntactically correct
        p = re.compile(r"^[A-z0-9#$%=@!{},`~&*()<>?.:;_|^/+\[\]]{8,32}$")
        if not p.match(api_passphrase):
            self.handle_init_error("Kucoin API passphrase is invalid")

        self._api_key = api_key
        self._api_secret = api_secret
        self._api_passphrase = api_passphrase
        self._api_url = api_url

    def handle_init_error(self, err: str) -> None:
        """Handle initialisation error"""

        if self.debug:
            raise TypeError(err)
        else:
            raise SystemExit(err)

    def __call__(self, request) -> Request:
        """Signs the request"""

        timestamp = int(time.time() * 1000)
        body = (request.body or b"").decode()
        message = f"{timestamp}{request.method}{request.path_url}{body}"

        signature = base64.b64encode(
                hmac.new(self._api_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest())
        passphrase = base64.b64encode(hmac.new(self._api_secret.encode('utf-8'), self._api_passphrase.encode('utf-8'), hashlib.sha256).digest())

        request.headers.update({
                "KC-API-SIGN": signature,
                "KC-API-TIMESTAMP": str(timestamp),
                "KC-API-KEY": self._api_key,
                "KC-API-PASSPHRASE": passphrase,
                "KC-API-KEY-VERSION": str("2"),
            })

        return request

    def getAccounts(self) -> pd.DataFrame:
        """Retrieves your list of accounts"""

        # GET /accounts
        df = self.authAPI("GET", "api/v1/accounts?type=trade")

        if len(df) == 0:
            return pd.DataFrame()

        # exclude accounts with a nil balance
        df = df[df.balance != "0.0000000000000000"]

        # reset the dataframe index to start from 0
        df = df.reset_index()
        return df

    def getAccount(self, account: str) -> pd.DataFrame:
        """Retrieves a specific account"""

        # validates the account is syntactically correct
        p = re.compile(r"^[a-f0-9\-]{24,24}$")
        if not p.match(account):
            self.handle_init_error("Kucoin account is invalid")

        return self.authAPI("GET", f"api/v1/accounts/{account}")

    def getFees(self, market: str = "") -> pd.DataFrame:
        """Retrieves market fees"""

        df = self.authAPI("GET", f"api/v1/base-fee")

        if len(market):
            df["market"] = market
        else:
            df["market"] = ""

        return df

    def getMakerFee(self, market: str = "") -> float:
        """Retrieves maker fee"""

        if len(market):
            fees = self.getFees(market)
        else:
            fees = self.getFees()

        if len(fees) == 0 or "makerFeeRate" not in fees:
            Logger.error(
                f"error: 'makerFeeRate' not in fees (using {DEFAULT_MAKER_FEE_RATE} as a fallback)"
            )
            return DEFAULT_MAKER_FEE_RATE

        return float(fees["makerFeeRate"].to_string(index=False).strip())

    def getTakerFee(self, market: str = "") -> float:
        """Retrieves taker fee"""

        if len(market) != None:
            fees = self.getFees(market)
        else:
            fees = self.getFees()

        if len(fees) == 0 or "takerFeeRate" not in fees:
            Logger.error(
                f"error: 'takerFeeRate' not in fees (using {DEFAULT_TAKER_FEE_RATE} as a fallback)"
            )
            return DEFAULT_TAKER_FEE_RATE

        return float(fees["takerFeeRate"].to_string(index=False).strip())

    def getUSDVolume(self) -> float:
        """Retrieves USD volume"""

        fees = self.getFees()
        return float(fees["usd_volume"].to_string(index=False).strip())

    def getMarkets(self) -> list:
        """Retrieves a list of markets on the exchange"""

        # GET /api/v3/allOrders
        resp = self.authAPI("GET", f"api/v1/symbols")


        if isinstance(resp, list):
            df = pd.DataFrame.from_dict(resp)
        else:
            df = pd.DataFrame(resp)


        return df[df["enableTrading"] == True]

    def getOrders(
        self, market: str = "", action: str = "", status: str = "all"
    ) -> pd.DataFrame:
        """Retrieves your list of orders with optional filtering"""

        # if market provided
        if market != "":
            # validates the market is syntactically correct
            if not self._isMarketValid(market):
                raise ValueError("Kucoin market is invalid.")

        # if action provided
        if action != "":
            # validates action is either a buy or sell
            if not action in ["buy", "sell"]:
                raise ValueError("Invalid order action.")

        # validates status is either open, pending, done, active, or all
        if not status in ["done", "active", "all"]:
            raise ValueError("Invalid order status.")

        # GET /orders?status
        resp = self.authAPI("GET", f"api/v1/orders")
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
                df["value"] = float(df["price"]) * float(df["size"]) - (
                    float(df["price"]) * MARGIN_ADJUSTMENT
                )
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

        # calculates the price at the time of purchase
        if status != "active":
            df["price"] = df.copy().apply(
                lambda row: (float(row.dealFunds) * 100)
                / (float(row.dealSize) * 100)
                if float(row.dealSize) > 0
                else 0,
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
        tsidx = pd.DatetimeIndex(
            pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%dT%H:%M:%S.%Z")
        )
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

        # for sell orders size is filled
        df["size"] = df["size"].fillna(df["filled"])

        return df

    #def getTime(self) -> datetime:
    #    """Retrieves the exchange time"""

    #    try:
    #        resp = self.authAPI("GET", "api/v1/timestamp")
    #        epoch = int(resp["data"] / 1000)
    #        return datetime.fromtimestamp(epoch)
    #    except:
    #        return None

    def marketBuy(self, market: str = "", quote_quantity: float = 0) -> pd.DataFrame:
        """Executes a market buy providing a funding amount"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise ValueError("Kucoin market is invalid.")

        # validates quote_quantity is either an integer or float
        if not isinstance(quote_quantity, int) and not isinstance(
            quote_quantity, float
        ):
            Logger.critical(
                "Please report this to Michael Whittle: "
                + str(quote_quantity)
                + " "
                + str(type(quote_quantity))
            )
            raise TypeError("The funding amount is not numeric.")

        # funding amount needs to be greater than 10
        if quote_quantity < MINIMUM_TRADE_AMOUNT:
            raise ValueError(f"Trade amount is too small (>= {MINIMUM_TRADE_AMOUNT}).")

        dt_obj = datetime.strptime(str(datetime.now()), '%Y-%m-%d %H:%M:%S.%f')
        millisec = dt_obj.timestamp() * 1000

        order = {
            "clientOid": str(millisec),
            "symbol": market,
            "type": "market",
            "side": "buy",
            "funds": self.marketQuoteIncrement(market, quote_quantity),
        }

        Logger.debug(order)

        # connect to authenticated Kucoin api
        model = AuthAPI(
            self._api_key, self._api_secret, self._api_passphrase, self._api_url
        )

        # place order and return result
        return model.authAPI("POST", "api/v1/orders", order)

    def marketSell(self, market: str = "", base_quantity: float = 0) -> pd.DataFrame:
        """Executes a market sell providing a crypto amount"""

        if not self._isMarketValid(market):
            raise ValueError("Kucoin market is invalid.")

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError("The crypto amount is not numeric.")

        dt_obj = datetime.strptime(str(datetime.now()), '%Y-%m-%d %H:%M:%S.%f')
        millisec = dt_obj.timestamp() * 1000


        order = {
            "clientOid": str(millisec),
            "symbol": market,
            "type": "market",
            "side": "sell",
            "size": self.marketBaseIncrement(market, base_quantity),
        }

        Logger.debug(order)

        model = AuthAPI(
            self._api_key, self._api_secret, self._api_passphrase, self._api_url
        )
        return model.authAPI("POST", "api/v1/orders", order)

    def limitSell(
        self, market: str = "", base_quantity: float = 0, future_price: float = 0
    ) -> pd.DataFrame:
        """Initiates a limit sell order"""

        if not self._isMarketValid(market):
            raise ValueError("Kucoin market is invalid.")

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError("The crypto amount is not numeric.")

        if not isinstance(future_price, int) and not isinstance(future_price, float):
            raise TypeError("The future crypto price is not numeric.")

        order = {
            "product_id": market,
            "type": "limit",
            "side": "sell",
            "size": self.marketBaseIncrement(market, base_quantity),
            "price": future_price,
        }

        Logger.debug(order)

        model = AuthAPI(
            self._api_key, self._api_secret, self._api_passphrase, self._api_url
        )
        return model.authAPI("POST", "orders", order)

    def getTradeFee(self, market: str) -> float:
        """Retrieves the trade fees"""

        # GET /sapi/v1/asset/tradeFee
        resp = self.authAPI(
            "GET",
            f"api/v1/trade-fees?symbols={market}",
        )

        if len(resp) == 1 and "takerFeeRate" in resp:
            return float(resp["takerFeeRate"])
        else:
            return DEFAULT_TRADE_FEE_RATE

    def cancelOrders(self, market: str = "") -> pd.DataFrame:
        """Cancels an order"""

        if not self._isMarketValid(market):
            raise ValueError("Kucoin market is invalid.")

        model = AuthAPI(
            self._api_key, self._api_secret, self._api_passphrase, self._api_url
        )
        return model.authAPI("DELETE", "orders")

    def marketBaseIncrement(self, market, amount) -> float:
        """Retrives the market base increment"""
        pMarket = market.split('-')[0]
        product = self.authAPI("GET", f"api/v1/symbols?{pMarket}")

        if "baseIncrement" not in product:
            return amount

        base_increment = str(product["baseIncrement"].values[0])

        if "." in str(base_increment):
            nb_digits = len(str(base_increment).split(".")[1])
        else:
            nb_digits = 0

        return floor(amount * 10 ** nb_digits) / 10 ** nb_digits

    def marketQuoteIncrement(self, market, amount) -> float:
        """Retrieves the market quote increment"""

        product = self.authAPI("GET", f"api/v1/symbols?{market}")

        if "quoteIncrement" not in product:
            return amount

        quote_increment = str(product["quoteIncrement"].values[0])

        if "." in str(quote_increment):
            nb_digits = len(str(quote_increment).split(".")[1])
        else:
            nb_digits = 0

        return floor(amount * 10 ** nb_digits) / 10 ** nb_digits

    def authAPI(self, method: str, uri: str, payload: str = "") -> pd.DataFrame:
        """Initiates a REST API call"""

        if not isinstance(method, str):
            raise TypeError("Method is not a string.")

        if not method in ["DELETE", "GET", "POST"]:
            raise TypeError("Method not DELETE, GET or POST.")

        if not isinstance(uri, str):
            raise TypeError("URI is not a string.")

        try:
            if method == "DELETE":
                resp = requests.delete(self._api_url + uri, auth=self)
            elif method == "GET":
                #resp = requests.request('GET', self._api_url + uri, headers=headers)
                resp = requests.get(self._api_url + uri, auth=self)
            elif method == "POST":
                resp = requests.post(self._api_url + uri, json=payload, auth=self)

            Logger.debug(resp.json())
            if resp.status_code != 200:
                if self.die_on_api_error or resp.status_code == 401:
                    # disable traceback
                    sys.tracebacklimit = 0

                    raise Exception(
                        method.upper()
                        + " ("
                        + "{}".format(resp.status_code)
                        + ") "
                        + self._api_url
                        + uri
                        + " - "
                        + "{}".format(resp.json()["message"])
                    )
                else:
                    Logger.error(
                        "error: "
                        + method.upper()
                        + " ("
                        + "{}".format(resp.status_code)
                        + ") "
                        + self._api_url
                        + uri
                        + " - "
                        + "{}".format(resp.json()["msg"])
                    )
                    return pd.DataFrame()

            resp.raise_for_status()

            mjson = resp.json()
            if isinstance(mjson, list):
                df = pd.DataFrame.from_dict(mjson)

            if "data" in mjson:
                mjson = mjson["data"]
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

            return df

        except requests.ConnectionError as err:
            return self.handle_api_error(err, "ConnectionError")

        except requests.exceptions.HTTPError as err:
            return self.handle_api_error(err, "HTTPError")

        except requests.Timeout as err:
            return self.handle_api_error(err, "Timeout")

        except json.decoder.JSONDecodeError as err:
            return self.handle_api_error(err, "JSONDecodeError")

    def handle_api_error(self, err: str, reason: str) -> pd.DataFrame:
        """Handle API errors"""

        if self.debug:
            if self.die_on_api_error:
                raise SystemExit(err)
            else:
                Logger.debug(err)
                return pd.DataFrame()
        else:
            if self.die_on_api_error:
                raise SystemExit(f"{reason}: {self._api_url}")
            else:
                Logger.info(f"{reason}: {self._api_url}")
                return pd.DataFrame()


class PublicAPI(AuthAPIBase):
    def __init__(self, api_url: str = 'https://openapi-sandbox.kucoin.com/') -> None:
        # options
        self.debug = False
        self.die_on_api_error = False
        self._api_url = api_url

        self.debug = True
        self.die_on_api_error = False

        valid_urls = [
            "https://api.kucoin.com",
            "https://api.kucoin.com/",
            "https://openapi-sandbox.kucoin.com",
            "https://openapi-sandbox.kucoin.com/",
        ]

        # validate Kucoin API
        if api_url not in valid_urls:
            raise ValueError("kucoin API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        self._api_url = api_url

    def getHistoricalData(
        self,
        market: str = DEFAULT_MARKET,
        granularity: int = MAX_GRANULARITY,
        iso8601start: str = "",
        iso8601end: str = "",
    ) -> pd.DataFrame:
        """Retrieves historical market data"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError("Kucoin market required.")

        # validates granularity is an integer
        if not isinstance(granularity, str):
            raise TypeError("Granularity string required.")

        # validates the granularity is supported by Kucoin
        if not granularity in SUPPORTED_GRANULARITY:
            raise TypeError(
                "Granularity options: " + ", ".join(map(str, SUPPORTED_GRANULARITY))
            )

        # validates the ISO 8601 start date is a string (if provided)
        if not isinstance(iso8601start, str):
            raise TypeError("ISO8601 start integer as string required.")

        # validates the ISO 8601 end date is a string (if provided)
        if not isinstance(iso8601end, str):
            raise TypeError("ISO8601 end integer as string required.")

        if iso8601start != "" and iso8601end == "":
            startTime = int(
                datetime.timestamp(datetime.strptime(iso8601start, "%Y-%m-%dT%H:%M:%S")))
            resp = self.authAPI(
                "GET",
                f"api/v1/market/candles?type={granularity}&symbol={market}&startAt={startTime}",
            )
        elif iso8601start != "" and iso8601end != "":
            startTime = int(
                datetime.timestamp(datetime.strptime(iso8601start, "%Y-%m-%dT%H:%M:%S")))

            endTime = int(
                datetime.timestamp(datetime.strptime(iso8601end, "%Y-%m-%dT%H:%M:%S")))
            resp = self.authAPI(
                "GET",
                f"api/v1/market/candles?type={granularity}&symbol={market}&startAt={startTime}&endAt={endTime}",
            )
        else:
            resp = self.authAPI(
                "GET", f"api/v1/market/candles?type={granularity}&symbol={market}"
            )

        # convert the API response into a Pandas DataFrame
        df = pd.DataFrame(
            resp['data'], columns=["epoch", "open", "close", "high", "low", "volume", "turnover"]
        )
        # reverse the order of the response with earliest last
        df = df.iloc[::-1].reset_index()

        try:
            freq = FREQUENCY_EQUIVALENTS[SUPPORTED_GRANULARITY.index(granularity)]
        except:
            freq = "D"

        # convert the DataFrame into a time series with the date as the index/key
        try:
            tsidx = pd.DatetimeIndex(
                pd.to_datetime(df["epoch"], unit="s"), dtype="datetime64[ns]", freq=freq
            )
            df.set_index(tsidx, inplace=True)
            df = df.drop(columns=["epoch", "index"])
            df.index.names = ["ts"]
            df["date"] = tsidx
        except ValueError:
            tsidx = pd.DatetimeIndex(
                pd.to_datetime(df["epoch"], unit="s"), dtype="datetime64[ns]"
            )
            df.set_index(tsidx, inplace=True)
            df = df.drop(columns=["epoch", "index"])
            df.index.names = ["ts"]
            df["date"] = tsidx

        df["market"] = market
        df["granularity"] = granularity

        # re-order columns
        df = df[
            ["date", "market", "granularity", "low", "high", "open", "close", "volume"]
        ]

        df["low"] = pd.to_numeric(df["low"])
        df["high"] = pd.to_numeric(df["high"])
        df["open"] = pd.to_numeric(df["open"])
        df["close"] = pd.to_numeric(df["close"])
        df["volume"] = pd.to_numeric(df["volume"])
        #convert_columns = {'close': float}
        #resp.asType(convert_columns)
        return df

    def getTicker(self, market: str = DEFAULT_MARKET) -> tuple:
        """Retrives the market ticker"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError("Kucoin market required.")

        resp = self.authAPI("GET", f"api/v1/market/orderbook/level1?symbol={market}")

        if "time" in resp["data"] and "price" in resp["data"]:
            test = datetime.fromtimestamp(int(resp["data"]["time"]) / 1000)
            return (
                datetime.strptime(str(datetime.fromtimestamp(int(resp["data"]["time"]) / 1000)), "%Y-%m-%d %H:%M:%S.%f").strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                float(resp["data"]["price"]),
            )

        now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        return (now, 0.0)

    def getTime(self) -> datetime:
        """Retrieves the exchange time"""

        try:
            resp = self.authAPI("GET", "api/v1/timestamp")
            epoch = int(resp["data"] / 1000)

            return datetime.fromtimestamp(epoch)
        except:
            return None

    def authAPI(self, method: str, uri: str, payload: str = "") -> dict:
        """Initiates a REST API call"""

        if not isinstance(method, str):
            raise TypeError("Method is not a string.")

        if not method in ["GET", "POST"]:
            raise TypeError("Method not GET or POST.")

        if not isinstance(uri, str):
            raise TypeError("URI is not a string.")

        try:
            if method == "GET":
                resp = requests.get(self._api_url + uri)
            elif method == "POST":
                resp = requests.post(self._api_url + uri, json=payload)
            
            Logger.debug(resp.json())
            if resp.status_code != 200:
                resp_message = resp.json()["msg"]
                message = f"{method} ({resp.status_code}) {self._api_url}{uri} - {resp_message}"
                if self.die_on_api_error:
                    raise Exception(message)
                else:
                    Logger.error(f"Error: {message}")
                    return {}

            resp.raise_for_status()
            return resp.json()

        except requests.ConnectionError as err:
            return self.handle_api_error(err, "ConnectionError")

        except requests.exceptions.HTTPError as err:
            return self.handle_api_error(err, "HTTPError")

        except requests.Timeout as err:
            return self.handle_api_error(err, "Timeout")

        except json.decoder.JSONDecodeError as err:
            return self.handle_api_error(err, "JSONDecodeError")

    def handle_api_error(self, err: str, reason: str) -> dict:
        """Handle API errors"""

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
