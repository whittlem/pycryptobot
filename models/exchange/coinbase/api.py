"""Remotely control your Coinbase account via their API"""

import re
import sys
import json
import hmac
import hashlib
import time
import requests
import pandas as pd
import numpy as np
from numpy import floor
from datetime import datetime, timedelta
from requests.auth import AuthBase
from requests import Request
from threading import Thread
from websocket import create_connection, WebSocketConnectionClosedException
from models.exchange.Granularity import Granularity
from views.PyCryptoBot import RichText

MARGIN_ADJUSTMENT = 0.0025
DEFAULT_MAKER_FEE_RATE = 0.004
DEFAULT_TAKER_FEE_RATE = 0.006
MINIMUM_TRADE_AMOUNT = 10
DEFAULT_GRANULARITY = 3600
SUPPORTED_GRANULARITY = [60, 300, 900, 3600, 21600, 86400]
FREQUENCY_EQUIVALENTS = ["T", "5T", "15T", "H", "6H", "D"]
MAX_GRANULARITY = max(SUPPORTED_GRANULARITY)
DEFAULT_MARKET = "BTC-GBP"


class AuthAPIBase:
    def _is_market_valid(self, market: str) -> bool:
        p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
        if p.match(market):
            return True
        return False


class AuthAPI(AuthAPIBase):
    def __init__(self, api_key="", api_secret="", api_url="https://api.coinbase.com", app: object = None) -> None:
        """Coinbase API object model

        Parameters
        ----------
        api_key : str
            Your Coinbase account portfolio API key
        api_secret : str
            Your Coinbase account portfolio API secret
        api_url
            Coinbase API URL
        """

        # options
        self.die_on_api_error = False

        valid_urls = [
            "https://api.coinbase.com",
            "https://api.coinbase.com/",
        ]

        # validate Coinbase API
        if api_url not in valid_urls:
            raise ValueError("Coinbase API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        # validates the api key is syntactically correct
        p = re.compile(r"^[a-zA-Z0-9]{16}$")
        if not p.match(api_key):
            self.handle_init_error("Coinbase API key is invalid", app=app)

        # validates the api secret is syntactically correct
        p = re.compile(r"^[a-zA-Z0-9]{32}$")
        if not p.match(api_secret):
            self.handle_init_error("Coinbase API secret is invalid", app=app)

        # app
        self.app = app

        self._api_key = api_key
        self._api_secret = api_secret
        self._api_url = api_url

    def handle_init_error(self, err: str, app: object = None) -> None:
        """Handle initialisation error"""

        if app is not None and app.debug is True:
            raise TypeError(err)
        else:
            raise SystemExit(err)

    def __call__(self, request) -> Request:
        """Signs the request"""

        timestamp = str(int(time.time()))
        body = (request.body or b"").decode()
        url = request.path_url.split("?")[0]
        message = f"{timestamp}{request.method}{url}{body}"
        signature = hmac.new(self._api_secret.encode("utf-8"), message.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()

        request.headers.update(
            {
                "CB-ACCESS-SIGN": signature,
                "CB-ACCESS-TIMESTAMP": timestamp,
                "CB-ACCESS-KEY": self._api_key,
                "Content-Type": "application/json",
            }
        )

        return request

    # wallet:accounts:read
    def get_accounts(self) -> pd.DataFrame:
        """Retrieves your list of accounts"""

        # GET /api/v3/brokerage/accounts
        try:
            df = self.auth_api("GET", "api/v3/brokerage/accounts")
        except Exception:
            return pd.DataFrame()

        if len(df) == 0:
            return pd.DataFrame()

        # exclude accounts with a nil balance
        df = df[df.balance != "0.0000000000000000"]

        # return standard columns
        df.drop(columns=["name", "default", "deleted_at", "created_at", "updated_at", "type", "ready"], inplace=True)
        df.columns = ["id", "currency", "trading_enabled", "balance", "hold"]
        df["balance"] = pd.to_numeric(df["balance"])
        df["hold"] = pd.to_numeric(df["hold"])
        df["available"] = df["balance"] - df["hold"]
        df["profile_id"] = None
        df["index"] = df.index
        df = df[["index", "id", "currency", "balance", "hold", "available", "profile_id", "trading_enabled"]]

        # reset the dataframe index to start from 0
        df = df.reset_index(drop=True)

        return df

    # wallet:accounts:read
    def get_account(self, uuid: str) -> pd.DataFrame:
        """Retrieves an account"""

        # GET /api/v3/brokerage/accounts
        try:
            df = self.auth_api("GET", "api/v3/brokerage/accounts/" + uuid)
        except Exception:
            return pd.DataFrame()

        if len(df) == 0:
            return pd.DataFrame()

        # return standard columns
        df.drop(columns=["name", "default", "deleted_at", "created_at", "updated_at", "type", "ready"], inplace=True)
        df.columns = ["id", "currency", "trading_enabled", "balance", "hold"]
        df["balance"] = pd.to_numeric(df["balance"])
        df["hold"] = pd.to_numeric(df["hold"])
        df["available"] = df["balance"] - df["hold"]
        df["profile_id"] = None
        df["index"] = df.index
        df = df[["index", "id", "currency", "balance", "hold", "available", "profile_id", "trading_enabled"]]

        # reset the dataframe index to start from 0
        df = df.reset_index(drop=True)

        return df

    # wallet:user:read
    def get_products(self) -> pd.DataFrame:
        """Retrieves your list of products"""

        # GET /api/v3/brokerage/products
        try:
            df = self.auth_api("GET", "api/v3/brokerage/products")
        except Exception:
            return pd.DataFrame()

        if len(df) == 0:
            return pd.DataFrame()

        # reset the dataframe index to start from 0
        df = df.reset_index()

        return df

    # wallet:user:read
    def get_product(self, market: str = DEFAULT_MARKET) -> pd.DataFrame:
        """Retrieves a product"""

        # GET /api/v3/brokerage/products
        try:
            df = self.auth_api("GET", "api/v3/brokerage/products/" + market)
        except Exception:
            return pd.DataFrame()

        if len(df) == 0:
            return pd.DataFrame()

        return df

    # wallet:user:read
    def get_ticker(self, market: str = DEFAULT_MARKET, websocket=None) -> tuple:
        """Retrieves the market ticker"""

        # validates the market is syntactically correct
        if not self._is_market_valid(market):
            raise TypeError("Coinbase market required.")

        if websocket is not None and websocket.tickers is not None:
            try:
                row = websocket.tickers.loc[websocket.tickers["market"] == market]
                ticker_date = datetime.strptime(re.sub(r".0*$", "", str(row["date"].values[0])), "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                ticker_price = float(row["price"].values[0])

                if ticker_date is None:
                    ticker_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

                return (ticker_date, ticker_price)

            except Exception:
                pass

        trycnt, maxretry = (1, 5)
        while trycnt <= maxretry:
            try:
                # GET /api/v3/brokerage/products
                try:
                    df = self.auth_api("GET", "api/v3/brokerage/products/" + market + "/ticker")
                except Exception:
                    return pd.DataFrame()

                if len(df) == 0:
                    return pd.DataFrame()

                return (
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    float(df["price"]),
                )
            except Exception:
                trycnt += 1
                if trycnt >= maxretry:
                    if self.app:
                        RichText.notify(f"Coinbase Ticker Error - attempted {trycnt} times.", self.app, "warning")
                    return (datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), 0.0)
                time.sleep(15)

    # wallet:transactions:read
    def get_fees(self) -> pd.DataFrame:
        """Retrieves fee tiers"""

        try:
            df = self.auth_api("GET", "api/v3/brokerage/transaction_summary")

            if len(df) == 0:
                return pd.DataFrame()

            # return standard columns
            df.drop(columns=["pricing_tier", "usd_from", "usd_to"], inplace=True)
            df["taker_fee_rate"] = df["taker_fee_rate"].astype(float)
            df["maker_fee_rate"] = df["maker_fee_rate"].astype(float)
            df["usd_volume"] = None
            df["market"] = ""

            # reset the dataframe index to start from 0
            return df.reset_index(drop=True)

        except Exception:
            return pd.DataFrame()

    # wallet:transactions:read
    def get_maker_fee(self) -> float:
        """Retrieves maker fee"""

        fees = self.get_fees()

        if len(fees) == 0 or "maker_fee_rate" not in fees:
            if self.app:
                RichText.notify(f"error: 'maker_fee_rate' not in fees (using {DEFAULT_MAKER_FEE_RATE} as a fallback)", self.app, "error")
            return DEFAULT_MAKER_FEE_RATE

        return float(fees["maker_fee_rate"].to_string(index=False).strip())

    # wallet:transactions:read
    def get_taker_fee(self) -> float:
        """Retrieves taker fee"""

        fees = self.get_fees()

        if len(fees) == 0 or "taker_fee_rate" not in fees:
            if self.app:
                RichText.notify(f"error: 'taker_fee_rate' not in fees (using {DEFAULT_TAKER_FEE_RATE} as a fallback)", self.app, "error")
            return DEFAULT_TAKER_FEE_RATE

        return float(fees["taker_fee_rate"].to_string(index=False).strip())

    # wallet:orders:read
    def get_orders(self, market: str = "", action: str = "", status: str = "all") -> pd.DataFrame:
        """Retrieves your list of orders with optional filtering"""

        # if market provided
        if market != "":
            # validates the market is syntactically correct
            if not self._is_market_valid(market):
                raise ValueError("Coinbase market is invalid.")

        # if action provided
        if action != "":
            # validates action is either a buy or sell
            if action not in ["buy", "sell"]:
                raise ValueError("Invalid order action.")

        # validates status is either open, pending, done, active, or all
        if status not in ["open", "pending", "done", "active", "all"]:
            raise ValueError("Invalid order status.")

        # GET /api/v3/brokerage/orders/historical/batch
        try:
            payload = {}
            if market != "":
                payload["product_id"] = market
            if action != "":
                payload["order_side"] = action.upper()
            if status != "all":
                if status == "done":
                    payload["order_status"] = "FILLED"
                else:
                    payload["order_status"] = status.upper()

            df = self.auth_api("GET", "api/v3/brokerage/orders/historical/batch", payload)
        except Exception:
            return pd.DataFrame()

        # reverse dataframe
        df = df.iloc[::-1]

        # reset the dataframe index to start from 0
        return df.reset_index(drop=True)

    def get_time(self) -> datetime:
        """Retrieves the exchange time"""

        try:
            resp = self.auth_api("GET", "time")
            if "epoch" in resp:
                epoch = int(resp["epoch"])
                return datetime.fromtimestamp(epoch)
            else:
                if self.app:
                    RichText.notify(resp, self.app, "error")
                return None
        except Exception as e:
            if self.app:
                RichText.notify(f"Error: {e}", self.app, "error")
            return None

    # wallet:buys:create
    def market_buy(self, market: str = "", quote_quantity: float = 0) -> pd.DataFrame:
        """Executes a market buy providing a crypto amount"""

        if not self._is_market_valid(market):
            raise ValueError("Coinbase market is invalid.")

        if not isinstance(quote_quantity, int) and not isinstance(quote_quantity, float):
            raise TypeError("The crypto amount is not numeric.")

        try:
            order = {
                "client_order_id": str(np.random.randint(2**63)),
                "product_id": market,
                "side": "BUY",
                "order_configuration": {
                    "market_market_ioc": {
                        "quote_size": str(self.market_quote_increment(market, quote_quantity)),
                    }
                },
            }

            if self.app is not None and self.app.debug is True:
                RichText.notify(str(order), self.app, "debug")

            # GET /api/v3/brokerage/accounts
            return self.auth_api("POST", "api/v3/brokerage/orders", order)

        except Exception:
            return pd.DataFrame()

    # wallet:buys:create
    def market_sell(self, market: str = "", base_quantity: float = 0) -> pd.DataFrame:
        """Executes a market sell providing a crypto amount"""

        if not self._is_market_valid(market):
            raise ValueError("Coinbase market is invalid.")

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError("The crypto amount is not numeric.")

        try:
            order = {
                "client_order_id": str(np.random.randint(2**63)),
                "product_id": market,
                "side": "SELL",
                "order_configuration": {
                    "market_market_ioc": {
                        "base_size": str(self.market_base_increment(market, base_quantity)),
                    }
                },
            }

            if self.app is not None and self.app.debug is True:
                RichText.notify(str(order), self.app, "debug")

            # GET /api/v3/brokerage/accounts
            return self.auth_api("POST", "api/v3/brokerage/orders", order)

        except Exception:
            return pd.DataFrame()

    def limit_sell(self, market: str = "", base_quantity: float = 0, future_price: float = 0) -> pd.DataFrame:
        """Initiates a limit sell order"""

        if not self._is_market_valid(market):
            raise ValueError("Coinbase market is invalid.")

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError("The crypto amount is not numeric.")

        if not isinstance(future_price, int) and not isinstance(future_price, float):
            raise TypeError("The future crypto self.price is not numeric.")

        try:
            order = {
                "product_id": market,
                "type": "limit",
                "side": "sell",
                "size": self.market_base_increment(market, base_quantity),
                "price": future_price,
            }

            if self.app is not None and self.app.debug is True:
                RichText.notify(str(order), self.app, "debug")

            model = AuthAPI(self._api_key, self._api_secret, self._api_passphrase, self._api_url)
            return model.auth_api("POST", "orders", order)

        except Exception:
            return pd.DataFrame()

    def cancel_orders(self, market: str = "") -> pd.DataFrame:
        """Cancels an order"""

        if not self._is_market_valid(market):
            raise ValueError("Coinbase market is invalid.")

        try:
            model = AuthAPI(self._api_key, self._api_secret, self._api_passphrase, self._api_url)
            return model.auth_api("DELETE", "orders")

        except Exception:
            return pd.DataFrame()

    # wallet:user:read
    def market_base_increment(self, market, amount) -> float:
        """Retrieves the market base increment"""

        product = self.auth_api("GET", "api/v3/brokerage/products/" + market)

        if "base_increment" not in product:
            return amount

        base_increment = str(product["base_increment"])

        if "." in str(base_increment):
            nb_digits = len(str(base_increment).split(".")[1])
        else:
            nb_digits = 0

        return floor(amount * 10**nb_digits) / 10**nb_digits

    # wallet:user:read
    def market_quote_increment(self, market, amount) -> float:
        """Retrieves the market quote increment"""

        product = self.auth_api("GET", "api/v3/brokerage/products/" + market)

        if "quote_increment" not in product:
            return amount

        quote_increment = str(product["quote_increment"])

        if "." in str(quote_increment):
            nb_digits = len(str(quote_increment).split(".")[1])
        else:
            nb_digits = 0

        return floor(amount * 10**nb_digits) / 10**nb_digits

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
            raise TypeError("Coinbase market required.")

        # validates granularity is an enum
        if not isinstance(granularity, Granularity):
            raise TypeError("Granularity Enum required.")

        # validates the ISO 8601 start date is a string (if provided)
        if not isinstance(iso8601start, str):
            raise TypeError("ISO8601 start integer as string required.")

        # validates the ISO 8601 end date is a string (if provided)
        if not isinstance(iso8601end, str):
            raise TypeError("ISO8601 end integer as string required.")

        if websocket is not None:
            if websocket.candles is not None:
                try:
                    return websocket.candles.loc[websocket.candles["market"] == market]
                except Exception:
                    pass

        payload = {}

        if iso8601start == "" and iso8601end == "":
            if granularity.to_integer == 60:
                payload = {
                    "start": int(time.mktime((datetime.now() - timedelta(minutes=300)).timetuple())),
                    "end": int(time.time()),
                    "granularity": "ONE_MINUTE",
                }
            elif granularity.to_integer == 300:
                payload = {
                    "start": int(time.mktime((datetime.now() - timedelta(minutes=1500)).timetuple())),
                    "end": int(time.time()),
                    "granularity": "FIVE_MINUTE",
                }
            elif granularity.to_integer == 900:
                payload = {
                    "start": int(time.mktime((datetime.now() - timedelta(minutes=4500)).timetuple())),
                    "end": int(time.time()),
                    "granularity": "FIFTEEN_MINUTE",
                }
            elif granularity.to_integer == 3600:
                payload = {
                    "start": int(time.mktime((datetime.now() - timedelta(hours=300)).timetuple())),
                    "end": int(time.time()),
                    "granularity": "ONE_HOUR",
                }
            elif granularity.to_integer == 21600:
                payload = {
                    "start": int(time.mktime((datetime.now() - timedelta(hours=1800)).timetuple())),
                    "end": int(time.time()),
                    "granularity": "SIX_HOUR",
                }
            elif granularity.to_integer == 86400:
                payload = {
                    "start": int(time.mktime((datetime.now() - timedelta(days=299)).timetuple())),
                    "end": int(time.time()),
                    "granularity": "ONE_DAY",
                }
            else:
                return pd.DataFrame()
        elif iso8601start != "" and iso8601end != "":
            try:
                dt_start = datetime.strptime(iso8601start, "%Y-%m-%dT%H:%M:%S")
                dt_end = datetime.strptime(iso8601end, "%Y-%m-%dT%H:%M:%S")

                payload = {
                    "start": int((dt_start - datetime(1970, 1, 1)).total_seconds()),
                    "end": int((dt_end - datetime(1970, 1, 1)).total_seconds()),
                }

                if granularity.to_integer == 60:
                    payload["granularity"] = "ONE_MINUTE"
                elif granularity.to_integer == 300:
                    payload["granularity"] = "FIVE_MINUTE"
                elif granularity.to_integer == 900:
                    payload["granularity"] = "FIFTEEN_MINUTE"
                elif granularity.to_integer == 3600:
                    payload["granularity"] = "ONE_HOUR"
                elif granularity.to_integer == 21600:
                    payload["granularity"] = "SIX_HOUR"
                elif granularity.to_integer == 86400:
                    payload["granularity"] = "ONE_DAY"
                else:
                    return pd.DataFrame()
            except Exception:
                return pd.DataFrame()
        elif iso8601start != "" and iso8601end == "":
            try:
                dt_start = datetime.strptime(iso8601start, "%Y-%m-%dT%H:%M:%S")

                if granularity.to_integer == 60:
                    payload = {
                        "start": int(time.mktime(dt_start.timetuple())),
                        "end": int(time.mktime((dt_start + timedelta(minutes=300)).timetuple())),
                        "granularity": "ONE_MINUTE",
                    }
                elif granularity.to_integer == 300:
                    payload = {
                        "start": int(time.mktime(dt_start.timetuple())),
                        "end": int(time.mktime((dt_start + timedelta(minutes=1500)).timetuple())),
                        "granularity": "FIVE_MINUTE",
                    }
                elif granularity.to_integer == 900:
                    payload = {
                        "start": int(time.mktime(dt_start.timetuple())),
                        "end": int(time.mktime((dt_start + timedelta(minutes=4500)).timetuple())),
                        "granularity": "FIFTEEN_MINUTE",
                    }
                elif granularity.to_integer == 3600:
                    payload = {
                        "start": int(time.mktime(dt_start.timetuple())),
                        "end": int(time.mktime((dt_start + timedelta(hours=300)).timetuple())),
                        "granularity": "ONE_HOUR",
                    }
                elif granularity.to_integer == 21600:
                    payload = {
                        "start": int(time.mktime(dt_start.timetuple())),
                        "end": int(time.mktime((dt_start + timedelta(hours=1800)).timetuple())),
                        "granularity": "SIX_HOUR",
                    }
                elif granularity.to_integer == 86400:
                    payload = {
                        "start": int(time.mktime(dt_start.timetuple())),
                        "end": int(time.mktime((dt_start + timedelta(days=299)).timetuple())),
                        "granularity": "ONE_DAY",
                    }
            except Exception:
                return pd.DataFrame()
        elif iso8601start == "" and iso8601end != "":
            try:
                dt_end = datetime.strptime(iso8601end, "%Y-%m-%dT%H:%M:%S")

                if granularity.to_integer == 60:
                    payload = {
                        "start": int(time.mktime((dt_end - timedelta(minutes=300)).timetuple())),
                        "end": int(time.mktime(dt_end.timetuple())),
                        "granularity": "ONE_MINUTE",
                    }
                elif granularity.to_integer == 300:
                    payload = {
                        "start": int(time.mktime((dt_end - timedelta(minutes=1500)).timetuple())),
                        "end": int(time.mktime(dt_end.timetuple())),
                        "granularity": "FIVE_MINUTE",
                    }
                elif granularity.to_integer == 900:
                    payload = {
                        "start": int(time.mktime((dt_end - timedelta(minutes=4500)).timetuple())),
                        "end": int(time.mktime(dt_end.timetuple())),
                        "granularity": "FIFTEEN_MINUTE",
                    }
                elif granularity.to_integer == 3600:
                    payload = {
                        "start": int(time.mktime((dt_end - timedelta(hours=300)).timetuple())),
                        "end": int(time.mktime(dt_end.timetuple())),
                        "granularity": "ONE_HOUR",
                    }
                elif granularity.to_integer == 21600:
                    payload = {
                        "start": int(time.mktime((dt_end - timedelta(hours=1800)).timetuple())),
                        "end": int(time.mktime(dt_end.timetuple())),
                        "granularity": "SIX_HOUR",
                    }
                elif granularity.to_integer == 86400:
                    payload = {
                        "start": int(time.mktime((dt_end - timedelta(days=299)).timetuple())),
                        "end": int(time.mktime(dt_end.timetuple())),
                        "granularity": "ONE_DAY",
                    }
            except Exception:
                return pd.DataFrame()
        else:
            return pd.DataFrame()

        try:
            df = self.auth_api("GET", f"api/v3/brokerage/products/{market}/candles", payload)

            if not df.empty and len(df.columns) == 6:
                df.columns = ["epoch", "low", "high", "open", "close", "volume"]
                # reverse the order of the response with earliest last
                df = df.iloc[::-1].reset_index()

            try:
                freq = FREQUENCY_EQUIVALENTS[SUPPORTED_GRANULARITY.index(granularity.to_integer)]
            except Exception:
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
                tsidx = pd.DatetimeIndex(pd.to_datetime(df["epoch"], unit="s"), dtype="datetime64[ns]")
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

            df["low"] = df["low"].astype(float)
            df["high"] = df["high"].astype(float)
            df["open"] = df["open"].astype(float)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)

            # create a full range of requested interval
            full_range = pd.date_range(start=df.index[0], end=df.index[-1], freq=freq)

            # re-index the dataframe using the full range
            df = df.reindex(full_range)

            # fill missing values and forward-fill the price columns and set volume to 0 for missing rows.
            df["open"].fillna(method="ffill", inplace=True)
            df["high"].fillna(method="ffill", inplace=True)
            df["low"].fillna(method="ffill", inplace=True)
            df["close"].fillna(method="ffill", inplace=True)
            df["volume"].fillna(0, inplace=True)
            df["market"] = market
            df["granularity"] = granularity.to_integer
            df["date"] = df.index

            # reset pandas dataframe index
            df.reset_index()

        except Exception:
            return pd.DataFrame()

        if len(df) == 0:
            return pd.DataFrame()

        return df

    def auth_api(self, method: str, uri: str, payload: str = "") -> pd.DataFrame:
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
                if method == "DELETE":
                    resp = requests.delete(self._api_url + uri, auth=self)
                elif method == "GET":
                    resp = requests.get(self._api_url + uri, params=payload, auth=self)
                elif method == "POST":
                    resp = requests.post(self._api_url + uri, json=payload, auth=self)

                trycnt += 1
                resp.raise_for_status()

                if resp.status_code == 200:
                    # api error handling
                    if "error_details" in resp.json():
                        return pd.DataFrame(resp.json()["error_response"], index=[0])

                    if isinstance(resp.json(), list):
                        df = pd.DataFrame.from_dict(resp.json())
                        return df
                    else:
                        try:
                            # failure error handling
                            if "success" in resp.json() and resp.json()["success"] is False:
                                return pd.DataFrame(resp.json()["error_response"], index=[0])

                            endpoint = uri.split("/")[-1].lower()

                            if endpoint == "batch":
                                endpoint = "orders"

                            if "has_next" in resp.json():
                                df = pd.DataFrame(resp.json()[endpoint])
                                if endpoint == "accounts":
                                    # json_normalize two columns
                                    df_merge = pd.DataFrame(df.available_balance.tolist())
                                    df["balance"] = df_merge["value"]
                                    df_merge = pd.DataFrame(df.hold.tolist())
                                    df["hold_tmp"] = df_merge["value"]
                                    df.drop(columns=["available_balance", "hold"], inplace=True)
                                    df.rename(columns={"hold_tmp": "hold"}, errors="raise", inplace=True)
                                elif endpoint == "orders":
                                    json_data = resp.json()[endpoint]

                                    orders = []
                                    for order in json_data:
                                        if "base_size" in order["order_configuration"]["market_market_ioc"]:
                                            size = float(order["order_configuration"]["market_market_ioc"]["base_size"])
                                        elif "quote_size" in order["order_configuration"]["market_market_ioc"]:
                                            size = float(order["order_configuration"]["market_market_ioc"]["quote_size"])
                                        else:
                                            size = 0

                                        if order["status"].lower() == "filled":
                                            order_status = "done"
                                        else:
                                            order_status = order["status"].lower()

                                        orders.append(
                                            [
                                                order["created_time"],
                                                order["product_id"],
                                                order["side"].lower(),
                                                order["order_type"].lower(),
                                                size,
                                                float(order["filled_size"]),
                                                float(order["total_fees"]),
                                                float(order["average_filled_price"]),
                                                order_status,
                                            ]
                                        )

                                    df = pd.DataFrame(orders, columns=["created_at", "market", "action", "type", "size", "filled", "fees", "price", "status"])
                                elif endpoint in resp.json():
                                    json_data = pd.DataFrame(resp.json()[endpoint])
                                    df = pd.DataFrame(json_data)
                                else:
                                    if endpoint == "account":
                                        json_data = resp.json()[list(resp.json().keys())[0]]
                                        if "available_balance" in json_data and isinstance(json_data["available_balance"], dict):
                                            json_data["balance"] = json_data["available_balance"]["value"]
                                        del json_data["available_balance"]
                                        if "hold" in json_data and isinstance(json_data["hold"], dict):
                                            tmp_value = json_data["hold"]["value"]
                                            del json_data["hold"]
                                            json_data["hold"] = tmp_value
                                        df = pd.DataFrame(json_data, index=[0])
                                    elif endpoint == "transaction_summary":
                                        json_data = resp.json()
                                        if "fee_tier" in json_data and isinstance(json_data["fee_tier"], dict):
                                            df = pd.DataFrame(json_data["fee_tier"], index=[0])
                                    elif endpoint == "orders":
                                        json_data = resp.json()
                                        if "success_response" in json_data and isinstance(json_data["success_response"], dict):
                                            df = pd.DataFrame(json_data["success_response"], index=[0])
                                            if "base_size" in json_data["order_configuration"]:
                                                print("test")
                                    else:
                                        if "error_response" in resp.json():
                                            df = pd.DataFrame(resp.json()["error_response"], index=[0])
                                        else:
                                            return resp.json()

                            else:
                                try:
                                    # handle non-standard responses!
                                    if endpoint == "ticker":
                                        json_data = resp.json()["trades"]
                                        df = pd.DataFrame(json_data[0], index=[0])
                                    elif uri.startswith("api/v3/brokerage/accounts"):
                                        endpoint = "account"
                                        json_data = resp.json()["account"]
                                        if "available_balance" in json_data and isinstance(json_data["available_balance"], dict):
                                            json_data["balance"] = json_data["available_balance"]["value"]
                                        del json_data["available_balance"]
                                        if "hold" in json_data and isinstance(json_data["hold"], dict):
                                            tmp_value = json_data["hold"]["value"]
                                            del json_data["hold"]
                                            json_data["hold"] = tmp_value
                                        df = pd.DataFrame(json_data, index=[0])
                                    elif uri.startswith("api/v3/brokerage/products") and not uri.endswith("/candles"):
                                        json_data = resp.json()
                                        df = pd.DataFrame(
                                            [
                                                [
                                                    json_data["product_id"],
                                                    json_data["price"],
                                                    json_data["price_percentage_change_24h"],
                                                    json_data["volume_24h"],
                                                    json_data["volume_percentage_change_24h"],
                                                    json_data["base_increment"],
                                                    json_data["quote_increment"],
                                                    json_data["quote_min_size"],
                                                    json_data["quote_max_size"],
                                                    json_data["base_min_size"],
                                                    json_data["base_max_size"],
                                                    json_data["base_name"],
                                                    json_data["quote_name"],
                                                    json_data["status"],
                                                    json_data["cancel_only"],
                                                    json_data["limit_only"],
                                                    json_data["post_only"],
                                                    json_data["trading_disabled"],
                                                    json_data["auction_mode"],
                                                    json_data["product_type"],
                                                    json_data["quote_currency_id"],
                                                    json_data["base_currency_id"],
                                                    json_data["mid_market_price"],
                                                    json_data["base_display_symbol"],
                                                    json_data["quote_display_symbol"],
                                                ]
                                            ],
                                            columns=[
                                                "product_id",
                                                "price",
                                                "price_percentage_change_24h",
                                                "volume_24h",
                                                "volume_percentage_change_24h",
                                                "base_increment",
                                                "quote_increment",
                                                "quote_min_size",
                                                "quote_max_size",
                                                "base_min_size",
                                                "base_max_size",
                                                "base_name",
                                                "quote_name",
                                                "status",
                                                "cancel_only",
                                                "limit_only",
                                                "post_only",
                                                "trading_disabled",
                                                "auction_mode",
                                                "product_type",
                                                "quote_currency_id",
                                                "base_currency_id",
                                                "mid_market_price",
                                                "base_display_symbol",
                                                "quote_display_symbol",
                                            ],
                                        )
                                    elif uri.startswith("api/v3/brokerage/transaction_summary"):
                                        json_data = resp.json()["fee_tier"]
                                        df = pd.DataFrame(json_data, index=[0])
                                    else:
                                        endpoint = uri.split("/")[-1].lower()
                                        json_data = resp.json()[endpoint]
                                        df = pd.DataFrame(json_data)
                                except Exception:
                                    df = pd.DataFrame()

                        except Exception:
                            df = pd.DataFrame()

                        return df
                else:
                    if "msg" in resp.json():
                        resp_message = resp.json()["msg"]
                    elif "message" in resp.json():
                        resp_message = resp.json()["message"]
                    else:
                        resp_message = ""

                    if resp.status_code == 401 and (resp_message == "request timestamp expired"):
                        msg = f"{method} ({resp.status_code}) {self._api_url}{uri} - {resp_message} (hint: check your system time is using NTP)"
                    else:
                        msg = f"CoinbasePro auth_api Error: {method.upper()} ({resp.status_code}) {self._api_url}{uri} - {resp_message}"

                    reason = "Invalid Response"

            except requests.ConnectionError as err:
                reason, msg = ("ConnectionError", err)
                print(str(err), resp.text)

            except requests.exceptions.HTTPError as err:
                reason, msg = ("HTTPError", err)
                print(str(err), resp.text)

            except requests.Timeout as err:
                reason, msg = ("TimeoutError", err)
                print(str(err), resp.text)

            except json.decoder.JSONDecodeError as err:
                reason, msg = ("JSONDecodeError", err)
                print(str(err), resp.text)

            except Exception as err:
                reason, msg = ("GeneralException", err)
                print(str(err), resp.json())

            if trycnt >= maxretry:
                if reason in ("ConnectionError", "HTTPError") and trycnt <= connretry:
                    if self.app:
                        RichText.notify(f"{reason}:  URI: {uri} trying again.  Attempt: {trycnt}", self.app, "error")
                    if trycnt > 5:
                        time.sleep(30)
                else:
                    if msg is None:
                        msg = f"Unknown CoinbasePro Private API Error: call to {uri} attempted {trycnt} times, resulted in error"
                    if reason is None:
                        reason = "Unknown Error"
                    return self.handle_api_error(msg, reason)
            else:
                if self.app:
                    RichText.notify(f"{str(msg)} - trying again.  Attempt: {trycnt}", self.app, "error")
                time.sleep(15)
        else:
            return self.handle_api_error(
                f"CoinbasePro API Error: call to {uri} attempted {trycnt} times without valid response", "CoinbasePro Private API Error"
            )

    def handle_api_error(self, err: str, reason: str, app: object = None) -> pd.DataFrame:
        """Handle API errors"""

        if app is not None and app.debug is True:
            if self.die_on_api_error:
                raise SystemExit(err)
            else:
                if self.app:
                    RichText.notify(err, self.app, "error")
                return pd.DataFrame()
        else:
            if self.die_on_api_error:
                raise SystemExit(f"{reason}: {self._api_url}")
            else:
                if self.app:
                    RichText.notify(f"{reason}: {self._api_url}", self.app, "info")
                return pd.DataFrame()


class WebSocket(AuthAPIBase):
    def __init__(
        self,
        markets=None,
        # granularity=None,
        granularity: Granularity = Granularity.ONE_HOUR,
        api_url="https://api.coinbase.com",
        ws_url="wss://ws-feed.pro.coinbase.com",
        app: object = None,
    ) -> None:
        valid_urls = [
            "https://api.coinbase.com",
            "https://api.coinbase.com/",
        ]

        # validate Coinbase Pro API
        if api_url not in valid_urls:
            raise ValueError("Coinbase API URL is invalid")

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
        api_url="https://api.coinbase.com/",
        ws_url: str = "wss://ws-feed.pro.coinbase.com",
        app: object = None,
    ) -> None:
        if len(markets) == 0:
            raise ValueError("A list of one or more markets is required.")

        for market in markets:
            # validates the market is syntactically correct
            if not self._is_market_valid(market):
                raise ValueError("Coinbase market is invalid.")

        # validates granularity is an integer
        if not isinstance(granularity.to_integer, int):
            raise TypeError("Granularity integer required.")

        # validates the granularity is supported by Coinbase Pro
        if granularity.to_integer not in SUPPORTED_GRANULARITY:
            raise TypeError("Granularity options: " + ", ".join(map(str, SUPPORTED_GRANULARITY)))

        valid_urls = [
            "https://api.coinbase.com",
            "https://api.coinbase.com/",
        ]

        # validate Coinbase Pro API
        if api_url not in valid_urls:
            raise ValueError("Coinbase API URL is invalid")

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

        # app
        self.app = app

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
            self.time_elapsed = round((datetime.now() - self.start_time).total_seconds())

        if "time" in msg and "product_id" in msg and "price" in msg:
            # create dataframe from websocket message
            df = pd.DataFrame(
                columns=["date", "market", "price"],
                data=[
                    [
                        datetime.strptime(msg["time"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S"),
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
                resp = AuthAPI(self.app.api_key, self.app.api_secret, self.app.api_url, app=self.app).get_historical_data(
                    df["market"].values[0], self.granularity.to_integer
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
                candle_exists = ((self.candles["date"] == df["candle"].values[0]) & (self.candles["market"] == df["market"].values[0])).any()
                if not candle_exists:
                    # populate historical data via api if it does not exist
                    if len(self.candles[self.candles["market"] == df["market"].values[0]]) == 0:
                        resp = AuthAPI(self.app.api_key, self.app.api_secret, self.app.api_url, app=self.app).get_historical_data(
                            df["market"].values[0], self.granularity.to_integer
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

                    try:
                        df_new_candle.index = df_new_candle["date"]
                        self.candles = pd.concat([self.candles, df_new_candle])
                        df_new_candle = None
                    except Exception as err:
                        print(err)
                        pass
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
                    self.candles.at[candle.index.values[0], "volume"] = float(candle["volume"].values[0]) + float(msg["size"])

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

            # set correct column types
            self.candles["open"] = self.candles["open"].astype("float64")
            self.candles["high"] = self.candles["high"].astype("float64")
            self.candles["close"] = self.candles["close"].astype("float64")
            self.candles["low"] = self.candles["low"].astype("float64")
            self.candles["volume"] = self.candles["volume"].astype("float64")

            # keep last 300 candles per market
            self.candles = self.candles.groupby("market").tail(300)

        self.message_count += 1


"""
# Using Coinbase Pro Websocket API instead of Coinbase as it doesn't work properly!

class WebSocket(AuthAPIBase):
    def __init__(
        self,
        markets=None,
        granularity: Granularity = Granularity.ONE_HOUR,
        api_url="https://api.coinbase.com",
        ws_url="wss://advanced-trade-ws.coinbase.com",
        app: object = None,
    ) -> None:
        valid_urls = [
            "https://api.coinbase.com",
            "https://api.coinbase.com/",
        ]

        # validate Coinbase API
        if api_url not in valid_urls:
            raise ValueError("Coinbase API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        valid_ws_urls = [
            "wss://advanced-trade-ws.coinbase.com",
            "wss://advanced-trade-ws.coinbase.com/",
        ]

        # validate Coinbase Websocket URL
        if ws_url not in valid_ws_urls:
            raise ValueError("Coinbase WebSocket URL is invalid")

        if ws_url[-1] != "/":
            ws_url = ws_url + "/"

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

        # sign message
        channel = "market_trades"
        timestamp = str(int(time.time()))
        product_ids = self.markets
        product_ids_str = ",".join(product_ids)
        message = f"{timestamp}{channel}{product_ids_str}"
        signature = hmac.new(self.app.api_secret.encode("utf-8"), message.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()

        self.ws = create_connection(self._ws_url)
        self.ws.send(
            json.dumps(
                {
                    "type": "subscribe",
                    "product_ids": product_ids,
                    "channel": channel,
                    "api_key": self.app.api_key,
                    "timestamp": timestamp,
                    "signature": signature,
                }
            )
        )

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

                    if "type" in msg and msg["type"] == "error":
                        self.on_error(f'{msg["message"]} - {msg["reason"]}')

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
        api_url="https://api.coinbase.com/",
        ws_url: str = "wss://advanced-trade-ws.coinbase.com",
        app: object = None,
    ) -> None:
        if len(markets) == 0:
            raise ValueError("A list of one or more markets is required.")

        for market in markets:
            # validates the market is syntactically correct
            if not self._is_market_valid(market):
                raise ValueError("Coinbase market is invalid.")

        # validates granularity is an integer
        if not isinstance(granularity.to_integer, int):
            raise TypeError("Granularity integer required.")

        # validates the granularity is supported by Coinbase
        if granularity.to_integer not in SUPPORTED_GRANULARITY:
            raise TypeError("Granularity options: " + ", ".join(map(str, SUPPORTED_GRANULARITY)))

        valid_urls = [
            "https://api.coinbase.com",
            "https://api.coinbase.com/",
        ]

        # validate Coinbase API
        if api_url not in valid_urls:
            raise ValueError("Coinbase API URL is invalid")

        if api_url[-1] != "/":
            api_url = api_url + "/"

        valid_ws_urls = [
            "wss://advanced-trade-ws.coinbase.com",
            "wss://advanced-trade-ws.coinbase.com/",
        ]

        # validate Coinbase Websocket URL
        if ws_url not in valid_ws_urls:
            raise ValueError("Coinbase WebSocket URL is invalid")

        if ws_url[-1] != "/":
            ws_url = ws_url + "/"

        # app
        self.app = app

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
            self.time_elapsed = round((datetime.now() - self.start_time).total_seconds())

        if (
            "channel" in msg
            and "timestamp" in msg
            and msg["channel"] == "market_trades"
            and "events" in msg
            and len(msg["events"]) > 0
            and "trades" in msg["events"][0]
            and len(msg["events"][0]["trades"]) > 0
            and "product_id" in msg["events"][0]["trades"][0]
            and "price" in msg["events"][0]["trades"][0]
            and "size" in msg["events"][0]["trades"][0]
        ):
            datetime_ns = pd.to_datetime(msg["timestamp"])

            # create dataframe from websocket message
            df = pd.DataFrame(
                columns=["date", "market", "price"],
                data=[
                    [
                        datetime_ns.strftime("%Y-%m-%d %H:%M:%S"),
                        msg["events"][0]["trades"][0]["product_id"],
                        msg["events"][0]["trades"][0]["price"],
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
                resp = AuthAPI(self.app.api_key, self.app.api_secret, self.app.api_url, app=self.app).get_historical_data(
                    df["market"].values[0], self.granularity.to_integer
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
                                msg["events"][0]["trades"][0]["size"],
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
                        resp = AuthAPI(self.app.api_key, self.app.api_secret, self.app.api_url, app=self.app).get_historical_data(
                            df["market"].values[0], self.granularity.to_integer
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

                    try:
                        df_new_candle.index = df_new_candle["date"]
                        self.candles = pd.concat([self.candles, df_new_candle])
                        df_new_candle = None
                    except Exception as err:
                        print(err)
                        pass
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
                    self.candles.at[candle.index.values[0], "volume"] = float(candle["volume"].values[0]) + float(msg["size"])

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
"""
