"""Remotely control your Coinbase Pro account via their API"""

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
from threading import Thread
from websocket import create_connection, WebSocketConnectionClosedException
from models.helper.LogHelper import Logger
from models.exchange.Granularity import Granularity

MARGIN_ADJUSTMENT = 0.0025
DEFAULT_MAKER_FEE_RATE = 0.005
DEFAULT_TAKER_FEE_RATE = 0.005
MINIMUM_TRADE_AMOUNT = 10
DEFAULT_GRANULARITY = 3600
SUPPORTED_GRANULARITY = [60, 300, 900, 3600, 21600, 86400]
FREQUENCY_EQUIVALENTS = ["T", "5T", "15T", "H", "6H", "D"]
MAX_GRANULARITY = max(SUPPORTED_GRANULARITY)
DEFAULT_MARKET = "BTC-GBP"


class AuthAPIBase:
    def _isMarketValid(self, market: str) -> bool:
        p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
        if p.match(market):
            return True
        return False

    # def to_coinbasepro_granularity(self, granularity) -> str:
    #     if isinstance(granularity, int):
    #         if granularity in SUPPORTED_GRANULARITY:
    #             return granularity
    #         else:
    #             raise ValueError(f"Invalid Binance granularity: {granularity}")
    #     else:
    #         return {"1min" : 60, "5min" : 300, "15min" : 900, "1hour" : 3600, "6hour" : 21600, "1day" : 86400} [
    #             granularity
    #         ]

class AuthAPI(AuthAPIBase):
    def __init__(
        self,
        api_key="",
        api_secret="",
        api_passphrase="",
        api_url="https://api.pro.coinbase.com",
    ) -> None:
        """Coinbase Pro API object model

        Parameters
        ----------
        api_key : str
            Your Coinbase Pro account portfolio API key
        api_secret : str
            Your Coinbase Pro account portfolio API secret
        api_passphrase : str
            Your Coinbase Pro account portfolio API passphrase
        api_url
            Coinbase Pro API URL
        """

        # options
        self.debug = False
        self.die_on_api_error = False

        valid_urls = [
            "https://api.pro.coinbase.com",
            "https://api.pro.coinbase.com/",
            "https://public.sandbox.pro.coinbase.com",
            "https://public.sandbox.pro.coinbase.com/",
        ]

        # validate Coinbase Pro API
        if api_url not in valid_urls:
            raise ValueError("Coinbase Pro API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        # validates the api key is syntactically correct
        p = re.compile(r"^[a-f0-9]{32}$")
        if not p.match(api_key):
            self.handle_init_error("Coinbase Pro API key is invalid")

        # validates the api secret is syntactically correct
        p = re.compile(r"^[A-z0-9+\/]+==$")
        if not p.match(api_secret):
            self.handle_init_error("Coinbase Pro API secret is invalid")

        # validates the api passphrase is syntactically correct
        p = re.compile(r"^[A-z0-9#$%=@!{},`~&*()<>?.:;_|^/+\[\]]{8,32}$")
        if not p.match(api_passphrase):
            self.handle_init_error("Coinbase Pro API passphrase is invalid")

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

        timestamp = str(time.time())
        body = (request.body or b"").decode()
        message = f"{timestamp}{request.method}{request.path_url}{body}"
        hmac_key = base64.b64decode(self._api_secret)
        signature = hmac.new(hmac_key, message.encode(), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode()

        request.headers.update(
            {
                "CB-ACCESS-SIGN": signature_b64,
                "CB-ACCESS-TIMESTAMP": timestamp,
                "CB-ACCESS-KEY": self._api_key,
                "CB-ACCESS-PASSPHRASE": self._api_passphrase,
                "Content-Type": "application/json",
            }
        )

        return request

    def getAccounts(self) -> pd.DataFrame:
        """Retrieves your list of accounts"""

        # GET /api/v3/account
        try:
            df = self.authAPI("GET", "accounts")
        except:
            return pd.DataFrame()

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
        p = re.compile(r"^[a-f0-9\-]{36,36}$")
        if not p.match(account):
            self.handle_init_error("Coinbase Pro account is invalid")

        try:
            return self.authAPI("GET", f"accounts/{account}")
        except:
            return pd.DataFrame()

    def getFees(self, market: str = "") -> pd.DataFrame:
        """Retrieves market fees"""

        try:
            df = self.authAPI("GET", "fees")

            if len(df) == 0:
                return pd.DataFrame()

            if len(market):
                df["market"] = market
            else:
                df["market"] = ""

            return df

        except:
            return pd.DataFrame()

    def getMakerFee(self, market: str = "") -> float:
        """Retrieves maker fee"""

        if len(market):
            fees = self.getFees(market)
        else:
            fees = self.getFees()

        if len(fees) == 0 or "maker_fee_rate" not in fees:
            Logger.error(
                f"error: 'maker_fee_rate' not in fees (using {DEFAULT_MAKER_FEE_RATE} as a fallback)"
            )
            return DEFAULT_MAKER_FEE_RATE

        return float(fees["maker_fee_rate"].to_string(index=False).strip())

    def getTakerFee(self, market: str = "") -> float:
        """Retrieves taker fee"""

        if len(market) != None:
            fees = self.getFees(market)
        else:
            fees = self.getFees()

        if len(fees) == 0 or "taker_fee_rate" not in fees:
            Logger.error(
                f"error: 'taker_fee_rate' not in fees (using {DEFAULT_TAKER_FEE_RATE} as a fallback)"
            )
            return DEFAULT_TAKER_FEE_RATE

        return float(fees["taker_fee_rate"].to_string(index=False).strip())

    def getUSDVolume(self) -> float:
        """Retrieves USD volume"""

        try:
            fees = self.getFees()
            if "usd_volume" in fees:
                return float(fees["usd_volume"].to_string(index=False).strip())
            else:
                return 0
        except:
            return 0

    def getOrders(
        self, market: str = "", action: str = "", status: str = "all"
    ) -> pd.DataFrame:
        """Retrieves your list of orders with optional filtering"""

        # if market provided
        if market != "":
            # validates the market is syntactically correct
            if not self._isMarketValid(market):
                raise ValueError("Coinbase Pro market is invalid.")

        # if action provided
        if action != "":
            # validates action is either a buy or sell
            if not action in ["buy", "sell"]:
                raise ValueError("Invalid order action.")

        # validates status is either open, pending, done, active, or all
        if not status in ["open", "pending", "done", "active", "all"]:
            raise ValueError("Invalid order status.")

        try:
            # GET /orders?status
            resp = self.authAPI("GET", f"orders?status={status}")
            if len(resp) > 0:
                if status == "open":
                    df = resp.copy()[
                        [
                            "created_at",
                            "product_id",
                            "side",
                            "type",
                            "size",
                            "price",
                            "status",
                        ]
                    ]
                    df["value"] = float(df["price"]) * float(df["size"]) - (
                        float(df["price"]) * MARGIN_ADJUSTMENT
                    )
                else:
                    if "specified_funds" in resp:
                        df = resp.copy()[
                            [
                                "created_at",
                                "product_id",
                                "side",
                                "type",
                                "filled_size",
                                "specified_funds",
                                "executed_value",
                                "fill_fees",
                                "status",
                            ]
                        ]
                    else:
                        # manual limit orders do not contain 'specified_funds'
                        df_tmp = resp.copy()
                        df_tmp["specified_funds"] = None
                        df = df_tmp[
                            [
                                "created_at",
                                "product_id",
                                "side",
                                "type",
                                "filled_size",
                                "specified_funds",
                                "executed_value",
                                "fill_fees",
                                "status",
                            ]
                        ]
            else:
                return pd.DataFrame()

            # replace null NaN values with 0
            df.copy().fillna(0, inplace=True)

            df_tmp = df.copy()
            df_tmp["price"] = 0.0
            df_tmp["filled_size"] = df_tmp["filled_size"].astype(float)
            df_tmp["specified_funds"] = df_tmp["specified_funds"].astype(float)
            df_tmp["executed_value"] = df_tmp["executed_value"].astype(float)
            df_tmp["fill_fees"] = df_tmp["fill_fees"].astype(float)
            df = df_tmp

            # calculates the price at the time of purchase
            if status != "open":
                df["price"] = df.copy().apply(
                    lambda row: (float(row.executed_value) * 100)
                    / (float(row.filled_size) * 100)
                    if float(row.filled_size) > 0
                    else 0,
                    axis=1,
                )
                # df.loc[df['filled_size'] > 0, 'price'] = (df['executed_value'] * 100) / (df['filled_size'] * 100)

            # rename the columns
            if status == "open":
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
                    "value",
                    "size",
                    "filled",
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
                        "value",
                        "fees",
                        "price",
                        "status",
                    ]
                ]
                df.columns = [
                    "created_at",
                    "market",
                    "action",
                    "type",
                    "size",
                    "filled",
                    "fees",
                    "price",
                    "status",
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

        except:
            return pd.DataFrame()

    def getTime(self) -> datetime:
        """Retrieves the exchange time"""

        try:
            resp = self.authAPI("GET", "time")
            if "epoch" in resp:
                epoch = int(resp["epoch"])
                return datetime.fromtimestamp(epoch)
            else:
                Logger.error(resp)
                return None
        except Exception as e:
            Logger.error(f"Error: {e}")
            return None

    def marketBuy(self, market: str = "", quote_quantity: float = 0) -> pd.DataFrame:
        """Executes a market buy providing a funding amount"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise ValueError("Coinbase Pro market is invalid.")

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
            Logger.warning(f"Trade amount is too small (>= {MINIMUM_TRADE_AMOUNT}).")
            return pd.DataFrame()
            # raise ValueError(f"Trade amount is too small (>= {MINIMUM_TRADE_AMOUNT}).")

        try:
            order = {
                "product_id": market,
                "type": "market",
                "side": "buy",
                "funds": self.marketQuoteIncrement(market, quote_quantity),
            }

            Logger.debug(order)

            # connect to authenticated coinbase pro api
            model = AuthAPI(
                self._api_key, self._api_secret, self._api_passphrase, self._api_url
            )

            # place order and return result
            return model.authAPI("POST", "orders", order)

        except:
            return pd.DataFrame()

    def marketSell(self, market: str = "", base_quantity: float = 0) -> pd.DataFrame:
        """Executes a market sell providing a crypto amount"""

        if not self._isMarketValid(market):
            raise ValueError("Coinbase Pro market is invalid.")

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError("The crypto amount is not numeric.")

        try:
            order = {
                "product_id": market,
                "type": "market",
                "side": "sell",
                "size": self.marketBaseIncrement(market, base_quantity),
            }

            Logger.debug(order)

            model = AuthAPI(
                self._api_key, self._api_secret, self._api_passphrase, self._api_url
            )
            return model.authAPI("POST", "orders", order)

        except:
            return pd.DataFrame()

    def limitSell(
        self, market: str = "", base_quantity: float = 0, future_price: float = 0
    ) -> pd.DataFrame:
        """Initiates a limit sell order"""

        if not self._isMarketValid(market):
            raise ValueError("Coinbase Pro market is invalid.")

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError("The crypto amount is not numeric.")

        if not isinstance(future_price, int) and not isinstance(future_price, float):
            raise TypeError("The future crypto price is not numeric.")

        try:
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

        except:
            return pd.DataFrame()

    def cancelOrders(self, market: str = "") -> pd.DataFrame:
        """Cancels an order"""

        if not self._isMarketValid(market):
            raise ValueError("Coinbase Pro market is invalid.")

        try:
            model = AuthAPI(
                self._api_key, self._api_secret, self._api_passphrase, self._api_url
            )
            return model.authAPI("DELETE", "orders")

        except:
            return pd.DataFrame()

    def marketBaseIncrement(self, market, amount) -> float:
        """Retrieves the market base increment"""

        product = self.authAPI("GET", f"products/{market}")

        if "base_increment" not in product:
            return amount

        base_increment = str(product["base_increment"].values[0])

        if "." in str(base_increment):
            nb_digits = len(str(base_increment).split(".")[1])
        else:
            nb_digits = 0

        return floor(amount * 10 ** nb_digits) / 10 ** nb_digits

    def marketQuoteIncrement(self, market, amount) -> float:
        """Retrieves the market quote increment"""

        product = self.authAPI("GET", f"products/{market}")

        if "quote_increment" not in product:
            return amount

        quote_increment = str(product["quote_increment"].values[0])

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
                resp = requests.get(self._api_url + uri, auth=self)
            elif method == "POST":
                resp = requests.post(self._api_url + uri, json=payload, auth=self)

            if "msg" in resp.json():
                resp_message = resp.json()["msg"]
            elif "message" in resp.json():
                resp_message = resp.json()["message"]
            else:
                resp_message = ""

            if resp.status_code == 401 and (
                resp_message == "request timestamp expired"
            ):
                message = f"{method} ({resp.status_code}) {self._api_url}{uri} - {resp_message} (hint: check your system time is using NTP)"
                Logger.error(f"Error: {message}")
                return {}
            elif resp.status_code != 200:
                if self.die_on_api_error or resp.status_code == 401:
                    # disable traceback
                    sys.tracebacklimit = 0

                    raise Exception(
                        f"{method.upper()} ({resp.status_code}) {self._api_url}{uri} - {resp_message}"
                    )
                else:
                    Logger.error(
                        f"error: {method.upper()} ({resp.status_code}) {self._api_url}{uri} - {resp_message}"
                    )
                    return pd.DataFrame()

            resp.raise_for_status()

            if isinstance(resp.json(), list):
                df = pd.DataFrame.from_dict(resp.json())
                return df
            else:
                df = pd.DataFrame(resp.json(), index=[0])
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
                Logger.error(err)
                return pd.DataFrame()
        else:
            if self.die_on_api_error:
                raise SystemExit(f"{reason}: {self._api_url}")
            else:
                Logger.info(f"{reason}: {self._api_url}")
                return pd.DataFrame()


class PublicAPI(AuthAPIBase):
    def __init__(self) -> None:
        # options
        self.debug = False
        self.die_on_api_error = False
        self._api_url = "https://api.pro.coinbase.com/"

    def getHistoricalData(
        self,
        market: str = DEFAULT_MARKET,
        # granularity: int = MAX_GRANULARITY,
        granularity: Granularity = Granularity.ONE_HOUR,
        websocket=None,
        iso8601start: str = "",
        iso8601end: str = "",
    ) -> pd.DataFrame:
        """Retrieves historical market data"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError("Coinbase Pro market required.")

        # validates granularity is an integer
        if not isinstance(granularity.to_integer, int):
            raise TypeError("Granularity integer required.")

        # validates the granularity is supported by Coinbase Pro
        if not granularity.to_integer in SUPPORTED_GRANULARITY:
            raise TypeError(
                "Granularity options: " + ", ".join(map(str, SUPPORTED_GRANULARITY))
            )

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
                except:
                    pass

        if websocket is None or (websocket is not None and using_websocket is False):
            if iso8601start != "" and iso8601end == "":
                resp = self.authAPI(
                    "GET",
                    f"products/{market}/candles?granularity={granularity.to_integer}&start={iso8601start}",
                )
            elif iso8601start != "" and iso8601end != "":
                resp = self.authAPI(
                    "GET",
                    f"products/{market}/candles?granularity={granularity.to_integer}&start={iso8601start}&end={iso8601end}",
                )
            else:
                resp = self.authAPI(
                    "GET", f"products/{market}/candles?granularity={granularity.to_integer}"
                )

            # convert the API response into a Pandas DataFrame
            df = pd.DataFrame(
                resp, columns=["epoch", "low", "high", "open", "close", "volume"]
            )
            # reverse the order of the response with earliest last
            df = df.iloc[::-1].reset_index()

            try:
                freq = FREQUENCY_EQUIVALENTS[SUPPORTED_GRANULARITY.index(granularity.to_integer)]
            except:
                freq = "D"

            # convert the DataFrame into a time series with the date as the index/key
            try:
                tsidx = pd.DatetimeIndex(
                    pd.to_datetime(df["epoch"], unit="s"),
                    dtype="datetime64[ns]",
                    freq=freq,
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
            df["granularity"] = granularity.to_integer

            # re-order columns
            df = df[
                [
                    "date",
                    "market",
                    "granularity",
                    "low",
                    "high",
                    "open",
                    "close",
                    "volume",
                ]
            ]

        return df

    def getTicker(self, market: str = DEFAULT_MARKET, websocket=None) -> tuple:
        """Retrieves the market ticker"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError("Coinbase Pro market required.")

        now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        if websocket is not None and websocket.tickers is not None:
            try:
                row = websocket.tickers.loc[websocket.tickers["market"] == market]
                return (
                    datetime.strptime(
                        re.sub(r".0*$", "", str(row["date"].values[0])),
                        "%Y-%m-%dT%H:%M:%S",
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    float(row["price"].values[0]),
                )

            except:
                return (now, 0.0)

        resp = self.authAPI("GET", f"products/{market}/ticker")

        if "time" in resp and "price" in resp:

            """Check if milliseconds (%f) are more then 6 digits. If so truncate for datetime which doesn't support more"""
            if len(resp["time"].split('.')[1]) > 7: resp["time"]=resp["time"][:26] + 'Z'

            return (
                datetime.strptime(resp["time"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                float(resp["price"]),
            )

        return (now, 0.0)

    def getTime(self) -> datetime:
        """Retrieves the exchange time"""

        try:
            resp = self.authAPI("GET", "time")
            if "epoch" in resp:
                epoch = int(resp["epoch"])
                return datetime.fromtimestamp(epoch)
            else:
                Logger.error(
                    "resp does not contain the epoch key for some reason!"
                )  # remove this later
                Logger.error(resp)
                return None
        except Exception as e:
            Logger.error(f"Error: {e}")
            return None

    def getMarkets24HrStats(self) -> pd.DataFrame():
        """Retrieves exchange markets 24hr stats"""

        try:
            return self.authAPI("GET", "products/stats")
        except:
            return pd.DataFrame()

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

            trycnt, maxretry = (1, 5)
            while trycnt <= maxretry:
                if resp.status_code != 200:
                    resp_message = resp.json()["message"]
                    message = f"{method} ({resp.status_code}) {self._api_url}{uri} - {resp_message}"
                    if self.die_on_api_error:
                        raise Exception(message)
                    else:
                        Logger.error(
                            f"Coinbase Pro API request error - retry attempt {trycnt}: {message}"
                        )
                    time.sleep(15)
                    trycnt += 1
                else:
                    break

                if method == "GET":
                    resp = requests.get(self._api_url + uri)
                elif method == "POST":
                    resp = requests.post(self._api_url + uri, json=payload)

            resp.raise_for_status()
            return resp.json()

        except requests.ConnectionError as err:
            Logger.error("requests.ConnectionError")  # remove this later
            return self.handle_api_error(err, "ConnectionError")

        except requests.exceptions.HTTPError as err:
            Logger.error("requests.exceptions.HTTPError")  # remove this later
            return self.handle_api_error(err, "HTTPError")

        except requests.Timeout as err:
            Logger.error("requests.Timeout")  # remove this later
            return self.handle_api_error(err, "Timeout")

        except json.decoder.JSONDecodeError as err:
            Logger.error("json.decoder.JSONDecodeError")  # remove this later
            return self.handle_api_error(err, "JSONDecodeError")

    def handle_api_error(self, err: str, reason: str) -> dict:
        """Handle API errors"""

        if self.debug:
            if self.die_on_api_error:
                raise SystemExit(err)
            else:
                Logger.error(err)
                return {}
        else:
            if self.die_on_api_error:
                raise SystemExit(f"{reason}: {self._api_url}")
            else:
                Logger.info(f"{reason}: {self._api_url}")
                return {}


class WebSocket(AuthAPIBase):
    def __init__(
        self,
        markets=None,
        # granularity=None,
        granularity: Granularity = Granularity.ONE_HOUR,
        api_url="https://api.pro.coinbase.com",
        ws_url="wss://ws-feed.pro.coinbase.com",
    ) -> None:
        # options
        self.debug = False

        valid_urls = [
            "https://api.pro.coinbase.com",
            "https://api.pro.coinbase.com/",
            "https://public.sandbox.pro.coinbase.com",
            "https://public.sandbox.pro.coinbase.com/",
        ]

        # validate Coinbase Pro API
        if api_url not in valid_urls:
            raise ValueError("Coinbase Pro API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        valid_ws_urls = [
            "wss://ws-feed.pro.coinbase.com",
            "wss://ws-feed.pro.coinbase.com/",
        ]

        # validate Coinbase Pro Websocket URL
        if ws_url not in valid_ws_urls:
            raise ValueError("Coinbase Pro WebSocket URL is invalid")

        if ws_url[-1] != "/":
            ws_url = ws_url + "/"

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

        self.ws = create_connection(self._ws_url)
        self.ws.send(
            json.dumps(
                {
                    "type": "subscribe",
                    "product_ids": self.markets,
                    "channels": ["matches"],
                }
            )
        )

        self.start_time = datetime.now()

    def _keepalive(self, interval=30):
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
        Logger.info("-- Websocket Subscribed! --")

    def on_close(self):
        Logger.info("-- Websocket Closed --")

    def on_message(self, msg):
        Logger.info(msg)

    def on_error(self, e, data=None):
        Logger.error(e)
        Logger.error("{} - data: {}".format(e, data))

        self.stop = True
        try:
            self.ws = None
            self.tickers = None
            self.candles = None
            self.start_time = None
            self.time_elapsed = 0
        except:
            pass

    def getStartTime(self) -> datetime:
        return self.start_time

    def getTimeElapsed(self) -> int:
        return self.time_elapsed


class WebSocketClient(WebSocket):
    def __init__(
        self,
        markets: list = [DEFAULT_MARKET],
        # granularity: str = DEFAULT_GRANULARITY,
        granularity: Granularity = Granularity.ONE_HOUR,
        api_url="https://api.pro.coinbase.com/",
        ws_url: str = "wss://ws-feed.pro.coinbase.com",
    ) -> None:
        if len(markets) == 0:
            raise ValueError("A list of one or more markets is required.")

        for market in markets:
            # validates the market is syntactically correct
            if not self._isMarketValid(market):
                raise ValueError("Coinbase Pro market is invalid.")

        # validates granularity is an integer
        if not isinstance(granularity.to_integer, int):
            raise TypeError("Granularity integer required.")

        # validates the granularity is supported by Coinbase Pro
        if not granularity.to_integer in SUPPORTED_GRANULARITY:
            raise TypeError(
                "Granularity options: " + ", ".join(map(str, SUPPORTED_GRANULARITY))
            )

        valid_urls = [
            "https://api.pro.coinbase.com",
            "https://api.pro.coinbase.com/",
            "https://public.sandbox.pro.coinbase.com",
            "https://public.sandbox.pro.coinbase.com/",
        ]

        # validate Coinbase Pro API
        if api_url not in valid_urls:
            raise ValueError("Coinbase Pro API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        valid_ws_urls = [
            "wss://ws-feed.pro.coinbase.com",
            "wss://ws-feed.pro.coinbase.com/",
        ]

        # validate Coinbase Pro Websocket URL
        if ws_url not in valid_ws_urls:
            raise ValueError("Coinbase Pro WebSocket URL is invalid")

        if ws_url[-1] != "/":
            ws_url = ws_url + "/"

        self._ws_url = ws_url

        self.markets = markets
        self.granularity = granularity
        self.tickers = None
        self.candles = None
        self.start_time = None
        self.time_elapsed = 0

    def on_open(self):
        self.message_count = 0

    def on_message(self, msg):
        if self.start_time is not None:
            self.time_elapsed = round(
                (datetime.now() - self.start_time).total_seconds()
            )

        if "time" in msg and "product_id" in msg and "price" in msg:
            # create dataframe from websocket message
            df = pd.DataFrame(
                columns=["date", "market", "price"],
                data=[
                    [
                        datetime.strptime(
                            msg["time"], "%Y-%m-%dT%H:%M:%S.%fZ"
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        msg["product_id"],
                        msg["price"],
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
                resp = PublicAPI().getHistoricalData(
                    df["market"].values[0], self.granularity
                )
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
                                df["candle"].values[0],
                                df["market"].values[0],
                                self.granularity.to_integer,
                                df["price"].values[0],
                                df["price"].values[0],
                                df["price"].values[0],
                                df["price"].values[0],
                                msg["size"],
                            ]
                        ],
                    )
            # candles dataframe contains some data
            else:
                # check if the current candle exists
                candle_exists = (
                    (self.candles["date"] == df["candle"].values[0])
                    & (self.candles["market"] == df["market"].values[0])
                ).any()
                if not candle_exists:
                    # populate historical data via api if it does not exist
                    if (
                        len(
                            self.candles[
                                self.candles["market"] == df["market"].values[0]
                            ]
                        )
                        == 0
                    ):
                        resp = PublicAPI().getHistoricalData(
                            df["market"].values[0], self.granularity
                        )
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
                                        df["candle"].values[0],
                                        df["market"].values[0],
                                        self.granularity.to_integer,
                                        df["price"].values[0],
                                        df["price"].values[0],
                                        df["price"].values[0],
                                        df["price"].values[0],
                                        msg["size"],
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
                                    msg["size"],
                                ]
                            ],
                        )
                    self.candles = self.candles.append(df_new_candle)
                else:
                    candle = self.candles[
                        (
                            (self.candles["date"] == df["candle"].values[0])
                            & (self.candles["market"] == df["market"].values[0])
                        )
                    ]

                    # set high on high
                    if float(df["price"].values[0]) > float(candle.high.values[0]):
                        self.candles.at[candle.index.values[0], "high"] = df[
                            "price"
                        ].values[0]

                    self.candles.at[candle.index.values[0], "close"] = df[
                        "price"
                    ].values[0]

                    # set low on low
                    if float(df["price"].values[0]) < float(candle.low.values[0]):
                        self.candles.at[candle.index.values[0], "low"] = df[
                            "price"
                        ].values[0]

                    # increment candle base volume
                    self.candles.at[candle.index.values[0], "volume"] = float(
                        candle["volume"].values[0]
                    ) + float(msg["size"])

            # insert first entry
            if self.tickers is None and len(df) > 0:
                self.tickers = df
            # append future entries without duplicates
            elif self.tickers is not None and len(df) > 0:
                self.tickers = (
                    pd.concat([self.tickers, df])
                    .drop_duplicates(subset="market", keep="last")
                    .reset_index(drop=True)
                )

            # convert dataframes to a time series
            tsidx = pd.DatetimeIndex(
                pd.to_datetime(self.tickers["date"]).dt.strftime("%Y-%m-%dT%H:%M:%S.%Z")
            )
            self.tickers.set_index(tsidx, inplace=True)
            self.tickers.index.name = "ts"

            tsidx = pd.DatetimeIndex(
                pd.to_datetime(self.candles["date"]).dt.strftime("%Y-%m-%dT%H:%M:%S.%Z")
            )
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
