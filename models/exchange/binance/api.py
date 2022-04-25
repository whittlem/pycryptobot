"""Remotely control your Binance account via their API : https://binance-docs.github.io/apidocs/spot/en"""

import hashlib
import hmac
import json
import math
import re
import sys
import time
from datetime import datetime, timedelta
from threading import Thread
from urllib.parse import urlencode

import numpy as np
import pandas as pd
import requests
from requests import Session
from websocket import create_connection, WebSocketConnectionClosedException

from models.exchange.Granularity import Granularity
from models.helper.LogHelper import Logger

DEFAULT_MAKER_FEE_RATE = 0.0015  # added 0.0005 to allow for price movements
DEFAULT_TAKER_FEE_RATE = 0.0015  # added 0.0005 to allow for price movements
DEFAULT_TRADE_FEE_RATE = 0.0015  # added 0.0005 to allow for price movements
MULTIPLIER_EQUIVALENTS = [1, 5, 15, 60, 360, 1440]
DEFAULT_MARKET = "BTCGBP"


class AuthAPIBase:
    def _isMarketValid(self, market: str) -> bool:
        p = re.compile(r"^[A-Z0-9]{5,17}$")
        if p.match(market):
            return True
        return False

    def convert_time(self, epoch: int = 0):
        if math.isnan(epoch) is False:
            epoch_str = str(epoch)[0:10]
            return datetime.fromtimestamp(int(epoch_str))


class AuthAPI(AuthAPIBase):
    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        api_url: str = "https://api.binance.com",
        order_history: list = [],
        recv_window: int = 5000,
    ) -> None:
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
            "https://api.binance.com",
            "https://api.binance.us",
            "https://testnet.binance.vision",
        ]

        # validate Binance API
        if api_url not in valid_urls:
            raise ValueError("Binance API URL is invalid")

        # validates the api key is syntactically correct
        p = re.compile(r"^[A-z0-9]{64,64}$")
        if not p.match(api_key):
            self.handle_init_error("Binance API key is invalid")

        # validates the api secret is syntactically correct
        p = re.compile(r"^[A-z0-9]{64,64}$")
        if not p.match(api_secret):
            self.handle_init_error("Binance API secret is invalid")

        self._api_key = api_key
        self._api_secret = api_secret
        self._api_url = api_url

        # order history
        self.order_history = order_history

        # api recvWindow
        self.recv_window = recv_window

    def handle_init_error(self, err: str) -> None:
        if self.debug:
            raise TypeError(err)
        else:
            raise SystemExit(err)

    def _dispatch_request(self, method: str):
        session = Session()
        session.headers.update(
            {
                "Content-Type": "application/json; charset=utf-8",
                "X-MBX-APIKEY": self._api_key,
            }
        )
        return {
            "GET": session.get,
            "DELETE": session.delete,
            "PUT": session.put,
            "POST": session.post,
        }.get(method, "GET")

    def createHash(self, uri: str = ""):
        return hmac.new(
            self._api_secret.encode("utf-8"), uri.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def getTimestamp(self):
        return int(time.time() * 1000)

    def getAccounts(self) -> pd.DataFrame:
        """Retrieves your list of accounts"""

        # GET /api/v3/account
        try:
            resp = self.authAPI(
                "GET", "/api/v3/account", {"recvWindow": self.recv_window}
            )

            # unexpected data, then return
            if len(resp) == 0 or "balances" not in resp:
                return pd.DataFrame()

            if isinstance(resp["balances"], list):
                df = pd.DataFrame.from_dict(resp["balances"])
            else:
                df = pd.DataFrame(resp["balances"], index=[0])

            # unexpected data, then return
            if len(df) == 0:
                return pd.DataFrame()

            # exclude accounts that are locked
            df = df[df.locked != 0.0]
            df["locked"] = df["locked"].astype(bool)

            # reset the dataframe index to start from 0
            df = df.reset_index()

            df["id"] = df["index"]
            df["hold"] = 0.0
            df["profile_id"] = None
            df["available"] = df["free"]

            df["id"] = df["id"].astype(object)
            df["hold"] = df["hold"].astype(object)

            # exclude accounts with a nil balance
            df = df[df.available != "0.00000000"]
            df = df[df.available != "0.00"]

            # inconsistent columns, then return
            if len(df.columns) != 8:
                return pd.DataFrame()

            # rename columns
            df.columns = [
                "index",
                "currency",
                "balance",
                "trading_enabled",
                "id",
                "hold",
                "profile_id",
                "available",
            ]

            # return if currency is missing
            if "currency" not in df:
                return df.DataFrame()

            return df[
                [
                    "index",
                    "id",
                    "currency",
                    "balance",
                    "hold",
                    "available",
                    "profile_id",
                    "trading_enabled",
                ]
            ]

        except:
            return pd.DataFrame()

    def getAccount(self) -> pd.DataFrame:
        """Retrieves all accounts for Binance as there is no specific account id"""

        return self.getAccounts()

    def getFees(self, market: str = "") -> pd.DataFrame:
        """Retrieves a account fees"""

        volume = 0
        try:
            # GET /api/v3/klines
            resp = self.authAPI(
                "GET",
                "/api/v3/klines",
                {"symbol": "BTCUSDT", "interval": "1d", "limit": 30},
            )

            # if response is empty, then return
            if len(resp) == 0:
                return pd.DataFrame()

            # convert the API response into a Pandas DataFrame
            df = pd.DataFrame(
                resp,
                columns=[
                    "open_time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "close_time",
                    "quote_asset_volume",
                    "number_of_trades",
                    "taker_buy_base_asset_volume",
                    "traker_buy_quote_asset_volume",
                    "ignore",
                ],
            )

            df["volume"] = df["volume"].astype(float)
            volume = np.round(float(df[["volume"]].mean()))
        except:
            pass

        # GET /api/v3/account
        resp = self.authAPI("GET", "/api/v3/account", {"recvWindow": self.recv_window})

        # unexpected data, then return
        if len(resp) == 0:
            return pd.DataFrame()

        if "makerCommission" in resp and "takerCommission" in resp:
            maker_fee_rate = resp["makerCommission"] / 10000
            taker_fee_rate = resp["takerCommission"] / 10000
        else:
            maker_fee_rate = 0.001
            taker_fee_rate = 0.001

        return pd.DataFrame(
            [
                {
                    "maker_fee_rate": maker_fee_rate,
                    "taker_fee_rate": taker_fee_rate,
                    "usd_volume": volume,
                    "market": "",
                }
            ]
        )

    def getMakerFee(self, market: str = "") -> float:
        """Retrieves the maker fee"""

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
        """Retrieves the taker fee"""

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
        """Retrieves the USD volume"""

        fees = self.getFees()
        return float(fees["usd_volume"].to_string(index=False).strip())

    def getMarkets(self) -> list:
        """Retrieves a list of markets on the exchange"""

        try:
            # GET /api/v3/exchangeInfo
            resp = self.authAPI("GET", "/api/v3/exchangeInfo")

            # unexpected data, then return
            if len(resp) == 0:
                return pd.DataFrame()

            if "symbols" in resp:
                if isinstance(resp["symbols"], list):
                    df = pd.DataFrame.from_dict(resp["symbols"])
                else:
                    df = pd.DataFrame(resp["symbols"], index=[0])
            else:
                df = pd.DataFrame()

            return df[df["isSpotTradingAllowed"] == True][["symbol"]].squeeze().tolist()

        except:
            return pd.DataFrame()

    def getOrders( #pylint: disable=invalid-name 
        self,
        market: str = "",
        action: str = "",
        status: str = "done",
        order_history: list = []
    ) -> pd.DataFrame: #pylint: disable=dangerous-default-value
        """Retrieves your list of orders with optional filtering"""

        # if market provided
        markets = None
        if market != "":
            # validates the market is syntactically correct
            if not self._isMarketValid(market):
                raise ValueError("Binance market is invalid.")
        else:
            if len(order_history) > 0 or status != "all":
                full_scan = False
                self.order_history = order_history
                if len(self.order_history) > 0:
                    if self._isMarketValid(market) and market not in self.order_history:
                        self.order_history.append(market)
                    markets = self.order_history
            else:
                full_scan = True
                markets = self.getMarkets()

        # if action provided
        if action != "":
            # validates action is either a buy or sell
            if not action in ["buy", "sell"]:
                raise ValueError("Invalid order action.")

        # validates status is either open, canceled, pending, done, active, or all
        if not status in ["open", "canceled", "pending", "done", "active", "all"]:
            raise ValueError("Invalid order status.")

        try:
            if markets is not None:
                df = pd.DataFrame()
                for market in markets:
                    if full_scan is True:
                        print(f"scanning {market} order history.")

                    # GET /api/v3/allOrders
                    resp = self.authAPI(
                        "GET",
                        "/api/v3/allOrders",
                        {"symbol": market, "recvWindow": self.recv_window},
                    )

                    # unexpected data, then return
                    if len(resp) == 0:
                        return pd.DataFrame()

                    if full_scan is True:
                        time.sleep(0.25)

                    if isinstance(resp, list):
                        df_tmp = pd.DataFrame.from_dict(resp)
                    else:
                        df_tmp = pd.DataFrame(resp, index=[0])

                    # unexpected data, then return
                    if len(df_tmp) == 0:
                        return pd.DataFrame()

                    if full_scan is True and len(df_tmp) > 0:
                        self.order_history.append(market)

                    if len(df_tmp) > 0:
                        df = pd.concat([df, df_tmp])

                if full_scan is True:
                    print(
                        f"add to order history to prevent full scan: {self.order_history}"
                    )
            else:
                # GET /api/v3/allOrders
                resp = self.authAPI(
                    "GET",
                    "/api/v3/allOrders",
                    {"symbol": market, "recvWindow": self.recv_window},
                )

                # unexpected data, then return
                if len(resp) == 0:
                    return pd.DataFrame()

                if isinstance(resp, list):
                    df = pd.DataFrame.from_dict(resp)
                else:
                    df = pd.DataFrame(resp, index=[0])

            if len(df) == 0 or "time" not in df:
                return pd.DataFrame()

            # feature engineering

            df.time = df["time"].map(self.convert_time)
            df["time"] = pd.to_datetime(df["time"]).dt.tz_localize("UTC")

            df["size"] = np.where(
                df["side"] == "BUY",
                df["cummulativeQuoteQty"],
                np.where(df["side"] == "SELL", df["executedQty"], 222),
            )
            df["fees"] = df["size"].astype(float) * 0.001
            df["fees"] = df["fees"].astype(object)

            df["side"] = df["side"].str.lower()

            df.rename(
                columns={
                    "time": "created_at",
                    "symbol": "market",
                    "side": "action",
                    "executedQty": "filled",
                },
                errors="raise",
                inplace=True,
            )

            def convert_status(status: str = ""):
                if status == "FILLED":
                    return "done"
                elif status == "NEW":
                    return "open"
                elif status == "PARTIALLY_FILLED":
                    return "pending"
                else:
                    return status

            df.status = df.status.map(convert_status)
            df["status"] = df["status"].str.lower()

            def calculate_price(row):
                if row.type == "LIMIT" and float(row.price) > 0:
                    return row.price
                elif row.action == "buy":
                    return float(row.cummulativeQuoteQty) / float(row.filled)
                elif row.action == "sell":
                    return float(row.cummulativeQuoteQty) / float(row.filled)
                else:
                    return row.price

            df["price"] = df.copy().apply(calculate_price, axis=1)

            # select columns
            df = df[
                [
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
            ]

            # filtering
            if action != "":
                df = df[df["action"] == action]
            if status != "all":
                df = df[df["status"] == status]

            return df

        except:
            return pd.DataFrame()

    def getTime(self) -> datetime:
        """Retrieves the exchange time"""

        try:
            # GET /api/v3/time
            resp = self.authAPI("GET", "/api/v3/time")
            return self.convert_time(int(resp["serverTime"])) - timedelta(hours=1)
        except Exception as e:
            Logger.error(f"Error: {e}")
            return None

    def getMarketInfoFilters(self, market: str) -> pd.DataFrame:
        """Retrieves markets exchange info"""

        df = pd.DataFrame()

        try:
            # GET /api/v3/exchangeInfo
            resp = self.authAPI("GET", "/api/v3/exchangeInfo", {"symbol": market})

            # unexpected data, then return
            if len(resp) == 0:
                return pd.DataFrame()

            if "symbols" in resp:
                if isinstance(resp["symbols"], list):
                    if "filters" in resp["symbols"][0]:
                        df = pd.DataFrame.from_dict(resp["symbols"][0]["filters"])
                else:
                    if "filers" in resp["symbols"][0]:
                        df = pd.DataFrame(resp["symbols"][0]["filters"], index=[0])

            return df

        except:
            return df

    def getTradeFee(self, market: str) -> float:
        """Retrieves the trade fees"""

        # Binance US does not currently define "/sapi/v1/asset/tradeFee" in its API
        if self._api_url == "https://api.binance.us":
            return DEFAULT_TRADE_FEE_RATE

        try:
            # GET /sapi/v1/asset/tradeFee
            resp = self.authAPI(
                "GET",
                "/sapi/v1/asset/tradeFee",
                {"symbol": market, "recvWindow": self.recv_window},
            )

            # unexpected data, then return
            if len(resp) == 0:
                return pd.DataFrame()

            if len(resp) == 1 and "takerCommission" in resp[0]:
                return float(resp[0]["takerCommission"])
            else:
                return DEFAULT_TRADE_FEE_RATE

        except:
            return DEFAULT_TRADE_FEE_RATE

    def getTicker(self, market: str = DEFAULT_MARKET, websocket=None) -> tuple:
        """Retrieves the market ticker"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError("Binance market required.")

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

        try:
            # GET /api/v3/ticker/price
            resp = self.authAPI("GET", "/api/v3/ticker/price", {"symbol": market})

            # unexpected data, then return
            if len(resp) == 0:
                return pd.DataFrame()

            if "price" in resp:
                return (str(self.getTime()), float(resp["price"]))
            else:
                return (now, 0.0)
        except:
            return (now, 0.0)

    def marketBuy(
        self, market: str = "", quote_quantity: float = 0, test: bool = False
    ) -> list:
        """Executes a market buy providing a funding amount"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise ValueError("Binance market is invalid.")

        # validates quote_quantity is either an integer or float
        if not isinstance(quote_quantity, int) and not isinstance(
            quote_quantity, float
        ):
            raise TypeError("The funding amount is not numeric.")

        try:
            current_price = self.getTicker(market)[1]

            base_quantity = np.divide(quote_quantity, current_price)

            df_filters = self.getMarketInfoFilters(market)
            step_size = float(
                df_filters.loc[df_filters["filterType"] == "LOT_SIZE"]["stepSize"]
            )
            precision = int(round(-math.log(step_size, 10), 0))

            # remove fees
            base_quantity = base_quantity - (base_quantity * self.getTradeFee(market))

            # execute market buy
            stepper = 10.0 ** precision
            truncated = math.trunc(stepper * base_quantity) / stepper

            order = {
                "symbol": market,
                "side": "BUY",
                "type": "MARKET",
                "quantity": truncated,
                "recvWindow": self.recv_window,
            }

            # Logger.debug(order)

            # POST /api/v3/order/test
            if test is True:
                resp = self.authAPI("POST", "/api/v3/order/test", order)
            else:
                resp = self.authAPI("POST", "/api/v3/order", order)

            return resp
        except Exception as err:
            ts = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            Logger.error(f"{ts} Binance  marketBuy {str(err)}")
            return []

    def marketSell(
        self, market: str = "", base_quantity: float = 0, test: bool = False, use_fees: bool = True
    ) -> list:
        """Executes a market sell providing a crypto amount"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise ValueError("Binance market is invalid.")

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError("The crypto amount is not numeric.")

        try:
            df_filters = self.getMarketInfoFilters(market)
            step_size = float(
                df_filters.loc[df_filters["filterType"] == "LOT_SIZE"]["stepSize"]
            )
            precision = int(round(-math.log(step_size, 10), 0))

            # remove fees
            if use_fees:
                base_quantity = base_quantity - (base_quantity * self.getTradeFee(market))

            # execute market sell
            stepper = 10.0 ** precision
            truncated = math.trunc(stepper * base_quantity) / stepper

            order = {
                "symbol": market,
                "side": "SELL",
                "type": "MARKET",
                "quantity": truncated,
                "recvWindow": self.recv_window,
            }

            # Logger.debug(order)

            # POST /api/v3/order/test
            if test is True:
                resp = self.authAPI("POST", "/api/v3/order/test", order)
            else:
                resp = self.authAPI("POST", "/api/v3/order", order)

            return resp
        except Exception as err:
            ts = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            Logger.error(f"{ts} Binance  marketSell {str(err)}")
            return []

    def authAPI(self, method: str, uri: str, payload: str = {}) -> dict:
        """Initiates a REST API call to the exchange"""

        if not isinstance(method, str):
            raise TypeError("Method is not a string.")

        if not method in ["GET", "POST"]:
            raise TypeError("Method not GET or POST.")

        if not isinstance(uri, str):
            raise TypeError("URI is not a string.")

        signed_uri = [
            "/api/v3/account",
            "/api/v3/allOrders",
            "/api/v3/order",
            "/api/v3/order/test",
            "/sapi/v1/asset/tradeFee",
        ]

        query_string = urlencode(payload, True)
        if uri in signed_uri and query_string:
            query_string = "{}&timestamp={}".format(query_string, self.getTimestamp())
        elif uri in signed_uri:
            query_string = "timestamp={}".format(self.getTimestamp())

        if uri in signed_uri:
            url = (
                self._api_url
                + uri
                + "?"
                + query_string
                + "&signature="
                + self.createHash(query_string)
            )
        else:
            url = self._api_url + uri + "?" + query_string

        params = {"url": url, "params": {}}

        try:
            resp = self._dispatch_request(method)(**params)

            if "msg" in resp.json():
                resp_message = resp.json()["msg"]
            elif "message" in resp.json():
                resp_message = resp.json()["message"]
            else:
                resp_message = ""

            if resp.status_code == 400 and (
                resp_message
                == "Timestamp for this request is outside of the recvWindow."
            ):
                message = f"{method} ({resp.status_code}) {self._api_url}{uri} - {resp_message} (hint: increase recvWindow with --recvWindow <5000-60000>)"
                Logger.error(f"Error: {message}")
                return {}
            elif resp.status_code == 400 and resp_message.__contains__("Invalid quantity"):
                message = f"{method} Invalid order quantity (hint: (binance only) try using use_sell_fee: 0)"
                Logger.error(f"{message}")
                return {}
            elif resp.status_code == 429 and (
                resp_message.startswith("Too much request weight used")
            ):
                message = f"{method} ({resp.status_code}) {self._api_url}{uri} - {resp_message} (sleeping for 5 seconds to prevent being banned)"
                Logger.error(f"Error: {message}")
                time.sleep(5)
                return {}
            elif resp.status_code != 200:
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
        """Handler for API errors"""

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


class PublicAPI(AuthAPIBase):
    def __init__(self, api_url="https://api.binance.com") -> None:
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
            "https://api.binance.com",
            "https://api.binance.us",
            "https://testnet.binance.vision",
        ]

        # validate Binance API
        if api_url not in valid_urls:
            raise ValueError("Binance API URL is invalid")

        self._api_url = api_url

    def getTime(self) -> datetime:
        """Retrieves the exchange time"""

        try:
            # GET /api/v3/time
            resp = self.authAPI("GET", "/api/v3/time")
            return self.convert_time(int(resp["serverTime"])) - timedelta(hours=1)
        except Exception as e:
            Logger.error(f"Error: {e}")
            return None

    def getMarkets24HrStats(self) -> pd.DataFrame():
        """Retrieves exchange markets 24hr stats"""

        try:
            return self.authAPI("GET", "/api/v3/ticker/24hr")
        except:
            return pd.DataFrame()

    def getTicker(self, market: str = DEFAULT_MARKET, websocket=None) -> tuple:
        """Retrieves the market ticker"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError("Binance market required.")

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

        # GET /api/v3/ticker/price
        resp = self.authAPI("GET", "/api/v3/ticker/price", {"symbol": market})

        if "price" in resp:
            return (str(self.getTime()), float(resp["price"]))
        else:
            return (now, 0.0)

    def getHistoricalData(
        self,
        market: str = DEFAULT_MARKET,
        granularity: Granularity = Granularity.ONE_HOUR,
        websocket=None,
        iso8601start: str = "",
        iso8601end: str = "",
    ) -> pd.DataFrame:
        """Retrieves historical market data"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError("Binance market required.")

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
                startTime = int(
                    datetime.timestamp(
                        datetime.strptime(iso8601start, "%Y-%m-%dT%H:%M:%S")
                    )
                    * 1000
                )

                # GET /api/v3/klines
                resp = self.authAPI(
                    "GET",
                    "/api/v3/klines",
                    {
                        "symbol": market,
                        "interval": granularity.to_short,
                        "startTime": startTime,
                        "limit": 300,
                    },
                )
            elif iso8601start != "" and iso8601end != "":
                startTime = int(
                    datetime.timestamp(
                        datetime.strptime(iso8601start, "%Y-%m-%dT%H:%M:%S")
                    )
                    * 1000
                )

                # GET /api/v3/klines
                resp = self.authAPI(
                    "GET",
                    "/api/v3/klines",
                    {
                        "symbol": market,
                        "interval": granularity.to_short,
                        "startTime": startTime,
                        "limit": 300,
                    },
                )
            else:
                # GET /api/v3/klines
                resp = self.authAPI(
                    "GET",
                    "/api/v3/klines",
                    {"symbol": market, "interval": granularity.to_short, "limit": 300},
                )

            # convert the API response into a Pandas DataFrame
            df = pd.DataFrame(
                resp,
                columns=[
                    "open_time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "close_time",
                    "quote_asset_volume",
                    "number_of_trades",
                    "taker_buy_base_asset_volume",
                    "traker_buy_quote_asset_volume",
                    "ignore",
                ],
            )

            df["market"] = market
            df["granularity"] = granularity.to_short

            # binance epoch is too long
            df["open_time"] = df["open_time"] + 1
            df["open_time"] = df["open_time"].astype(str)
            df["open_time"] = df["open_time"].str.replace(r"\d{3}$", "", regex=True)

            try:
                freq = granularity.get_frequency
            except:
                freq = "D"

            # convert the DataFrame into a time series with the date as the index/key
            try:
                tsidx = pd.DatetimeIndex(
                    pd.to_datetime(df["open_time"], unit="s"),
                    dtype="datetime64[ns]",
                    freq=freq,
                )
                df.set_index(tsidx, inplace=True)
                df = df.drop(columns=["open_time"])
                df.index.names = ["ts"]
                df["date"] = tsidx
            except ValueError:
                tsidx = pd.DatetimeIndex(
                    pd.to_datetime(df["open_time"], unit="s"), dtype="datetime64[ns]"
                )
                df.set_index(tsidx, inplace=True)
                df = df.drop(columns=["open_time"])
                df.index.names = ["ts"]
                df["date"] = tsidx

            # if specified, fix end time
            if iso8601end != "":
                df = df[df["date"] <= iso8601end]

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

            # correct column types
            df["low"] = df["low"].astype(float)
            df["high"] = df["high"].astype(float)
            df["open"] = df["open"].astype(float)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)

            # reset pandas dataframe index
            df.reset_index()

        return df

    def authAPI(self, method: str, uri: str, payload: str = {}) -> dict:
        """Initiates a REST API call to exchange"""

        if not isinstance(method, str):
            raise TypeError("Method is not a string.")

        if not method in ["GET", "POST"]:
            raise TypeError("Method not GET or POST.")

        if not isinstance(uri, str):
            raise TypeError("URI is not a string.")

        try:
            resp = requests.get(f"{self._api_url}{uri}", params=payload)

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
        """Handler for API errors"""

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
        market=None,
        granularity: Granularity = None,
        api_url="https://api.binance.com",
        ws_url: str = "wss://stream.binance.com:9443",
    ) -> None:
        # options
        self.debug = False

        valid_urls = [
            "https://api.binance.com",
            "https://api.binance.us",
            "https://testnet.binance.vision",
        ]

        # validate Binance API
        if api_url not in valid_urls:
            raise ValueError("Binance API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        valid_ws_urls = [
            "wss://stream.binance.com:9443",
            "wss://stream.binance.com:9443/",
        ]

        # validate Binance Websocket URL
        if ws_url not in valid_ws_urls:
            raise ValueError("Binance WebSocket URL is invalid")

        if ws_url[-1] != "/":
            ws_url = ws_url + "/"

        self._ws_url = ws_url
        self._api_url = api_url

        self.markets = None
        self.granularity = granularity
        self.type = "SUBSCRIBE"
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

        params = []
        for market in self.markets:
            params.append(f"{market.lower()}@miniTicker")
            params.append(f"{market.lower()}@kline_{self.granularity.to_short}")

        self.ws = create_connection(f"{self._ws_url}ws")
        self.ws.send(
            json.dumps(
                {
                    "method": "SUBSCRIBE",
                    "params": params,
                    "id": 1,
                }
            )
        )

        self.start_time = datetime.now()

    def _keepalive(self, interval=30):
        if (self.ws is not None) and (hasattr(self.ws,"connected")):
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


class WebSocketClient(WebSocket, AuthAPIBase):
    def __init__(
        self,
        markets: list = [DEFAULT_MARKET],
        granularity: Granularity = Granularity.ONE_HOUR,
        api_url="https://api.binance.com",
        ws_url: str = "wss://stream.binance.com:9443",
    ) -> None:
        if len(markets) == 0:
            raise ValueError("A list of one or more markets is required.")

        for market in markets:
            # validates the market is syntactically correct
            if not self._isMarketValid(market):
                raise ValueError("Binance market is invalid.")

        valid_urls = [
            "https://api.binance.com",
            "https://api.binance.us",
            "https://testnet.binance.vision",
        ]

        # validate Binance API
        if api_url not in valid_urls:
            raise ValueError("Binance API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        if api_url == "https://api.binance.us":
            valid_ws_urls = [
                "wss://stream.binance.us:9443",
                "wss://stream.binance.us:9443/",
            ]
        else:
            valid_ws_urls = [
                "wss://stream.binance.com:9443",
                "wss://stream.binance.com:9443/",
            ]

        # validate Binance Websocket URL
        if ws_url not in valid_ws_urls:
            raise ValueError("Binance WebSocket URL is invalid")

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
        self.start_time = datetime.now()
        self.message_count = 0

    def on_message(self, msg):
        if self.start_time is not None:
            self.time_elapsed = round(
                (datetime.now() - self.start_time).total_seconds()
            )

        if "e" in msg:
            df = None
            if (
                msg["e"] == "24hrMiniTicker"
                and "E" in msg
                and "s" in msg
                and "c" in msg
            ):
                # create dataframe from websocket message
                df = pd.DataFrame(
                    columns=["date", "market", "price"],
                    data=[
                        [
                            self.convert_time(msg["E"]),
                            msg["s"],
                            msg["c"],
                        ]
                    ],
                )

                # set column types
                df["date"] = df["date"].astype("datetime64[ns]")
                df["price"] = df["price"].astype("float64")
                df["candle"] = df["date"].dt.floor(freq=self.granularity.get_frequency)

            if df is not None:
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
                    pd.to_datetime(self.tickers["date"]).dt.strftime(
                        "%Y-%m-%dT%H:%M:%S.%Z"
                    )
                )
                self.tickers.set_index(tsidx, inplace=True)
                self.tickers.index.name = "ts"

            if msg["e"] == "kline" and "s" in msg and "k" in msg:
                k = msg["k"]
                if (
                    "i" in k
                    and "t" in k
                    and "o" in k
                    and "h" in k
                    and "c" in k
                    and "l" in k
                    and "v" in k
                ):
                    # create dataframe from websocket message
                    df = pd.DataFrame(
                        columns=[
                            "date",
                            "market",
                            "granularity",
                            "low",
                            "high",
                            "open",
                            "close",
                            "volume",
                        ],
                        data=[
                            [
                                self.convert_time(k["t"]), # - timedelta(hours=1),
                                msg["s"],
                                k["i"],
                                float(k["l"]),
                                float(k["h"]),
                                float(k["o"]),
                                float(k["c"]),
                                float(k["V"]),
                            ]
                        ],
                    )

                    if self.candles is None:
                        resp = PublicAPI().getHistoricalData(
                            df["market"].values[0], self.granularity
                        )
                        if len(resp) > 0:
                            self.candles = resp
                        else:
                            self.candles = pd.DataFrame(
                                columns=[
                                    "date",
                                    "market",
                                    "granularity",
                                    "low",
                                    "high",
                                    "open",
                                    "close",
                                    "volume",
                                ],
                                data=[],
                            )

                    if k["i"] == self.granularity.to_short and k["x"] is True:
                        # check if the current candle exists
                        candle_exists = (
                            (self.candles["date"] == df["date"].values[0])
                            & (self.candles["market"] == df["market"].values[0])
                        ).any()
                        if not candle_exists:
                            self.candles = pd.concat([self.candles, df]) #self.candles.append(df)

                        tsidx = pd.DatetimeIndex(
                            pd.to_datetime(self.candles["date"]).dt.strftime(
                                "%Y-%m-%dT%H:%M:%S.%Z"
                            )
                        )
                        self.candles.set_index(tsidx, inplace=True)
                        self.candles.index.name = "ts"

                    if self.candles is not None:
                        # keep last 300 candles per market
                        self.candles = self.candles.groupby("market").tail(300)
                        # sort columns by date
                        self.candles = self.candles.copy().sort_values(by=["date"])
                        # set correct column types
                        self.candles["open"] = self.candles["open"].astype("float64")
                        self.candles["high"] = self.candles["high"].astype("float64")
                        self.candles["close"] = self.candles["close"].astype("float64")
                        self.candles["low"] = self.candles["low"].astype("float64")
                        self.candles["volume"] = self.candles["volume"].astype(
                            "float64"
                        )
        self.message_count += 1
