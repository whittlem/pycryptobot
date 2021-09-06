import pandas as pd
import math
import random
import re
import urllib3
from datetime import datetime, timedelta
from typing import Union
from urllib3.exceptions import ReadTimeoutError
from models.Trading import TechnicalAnalysis
from models.exchange.binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import AuthAPI as CBAuthAPI, PublicAPI as CBPublicAPI
from models.config import binanceParseMarket, coinbaseProParseMarket
from models.helper.LogHelper import Logger
from models.helper.TextBoxHelper import TextBox
from models.BotConfig import BotConfig

# disable insecure ssl warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def to_coinbase_pro_granularity(granularity: int) -> int:
    return granularity


def to_binance_granularity(granularity: int) -> str:
    return {60: "1m", 300: "5m", 900: "15m", 3600: "1h", 21600: "6h", 86400: "1d"}[
        granularity
    ]


#  pylint: disable=unsubscriptable-object
def truncate(f: Union[int, float], n: Union[int, float]) -> str:
    """
    Format a given number ``f`` with a given precision ``n``.
    """

    if not isinstance(f, int) and not isinstance(f, float):
        return "0.0"

    if not isinstance(n, int) and not isinstance(n, float):
        return "0.0"

    if (f < 0.0001) and n >= 5:
        return f"{f:.5f}"

    # `{n}` inside the actual format honors the precision
    return f"{math.floor(f * 10 ** n) / 10 ** n:.{n}f}"


class PyCryptoBot(BotConfig):
    def __init__(self, config_file: str = None, exchange: str = None):
        self.config_file = config_file or "config.json"
        self.exchange = exchange
        super(PyCryptoBot, self).__init__(
            filename=self.config_file, exchange=self.exchange
        )

    extraCandlesFound = False

    trade_tracker = pd.DataFrame(columns=['Datetime', "Market", 'Action', "Price", 'Base', 'Quote', "Margin", "Profit", "Fee", "DF_High", "DF_Low"])

    def _isCurrencyValid(self, currency):
        if self.exchange == "coinbasepro" or self.exchange == "binance":
            p = re.compile(r"^[1-9A-Z]{2,5}$")
            return p.match(currency)

        return False

    def _isMarketValid(self, market):
        if self.exchange == "coinbasepro":
            p = re.compile(r"^[1-9A-Z]{2,5}\-[1-9A-Z]{2,5}$")
            return p.match(market)
        elif self.exchange == "binance":
            p = re.compile(r"^[A-Z0-9]{6,12}$")
            return p.match(market)

        return False

    def getRecvWindow(self):
        return self.recv_window

    def getLogFile(self):
        return self.logfile

    def getExchange(self):
        return self.exchange

    def getChatClient(self):
        return self._chat_client

    def getAPIKey(self):
        return self.api_key

    def getAPISecret(self):
        return self.api_secret

    def getAPIPassphrase(self):
        return self.api_passphrase

    def getAPIURL(self):
        return self.api_url

    def getBaseCurrency(self):
        return self.base_currency

    def getQuoteCurrency(self):
        return self.quote_currency

    def getMarket(self):
        return self.market

    def getGranularity(self) -> int:
        return self.granularity

    def getInterval(
        self, df: pd.DataFrame = pd.DataFrame(), iterations: int = 0
    ) -> pd.DataFrame:
        if len(df) == 0:
            return df

        if self.isSimulation() and iterations > 0:
            # with a simulation iterate through data
            return df.iloc[iterations - 1 : iterations]
        else:
            # most recent entry
            return df.tail(1)

    def printGranularity(self) -> str:
        if self.exchange == "binance":
            return to_binance_granularity(self.granularity)
        if self.exchange == "coinbasepro":
            return str(self.granularity)
        if self.exchange == "dummy":
            return str(self.granularity)
        raise TypeError('Unknown exchange "' + self.exchange + '"')

    def getBuyPercent(self):
        try:
            return int(self.buypercent)
        except Exception:
            return 100

    def getSellPercent(self):
        try:
            return int(self.sellpercent)
        except Exception:
            return 100

    def getBuyMaxSize(self):
        try:
            return float(self.buymaxsize)
        except Exception:
            return None

    def getBuyNearHighPcnt(self):
        try:
            return float(self.buynearhighpcnt)
        except Exception:
            return None

    def getDateFromISO8601Str(self, date: str):

        # If date passed from datetime.now() remove milliseconds
        if date.find(".") != -1:
            dt = date.split(".")[0]
            date = dt

        date = date.replace("T", " ") if date.find("T") != -1 else date
        # Add time in case only a date is passed in
        new_date_str = f"{date} 00:00:00" if len(date) == 10 else date

        return datetime.strptime(new_date_str, "%Y-%m-%d %H:%M:%S")

    def getHistoricalData(
        self, market, granularity: int, iso8601start="", iso8601end=""
    ):
        if self.exchange == "binance":
            api = BPublicAPI(api_url=self.getAPIURL())

            if iso8601start != "" and iso8601end != "":
                return api.getHistoricalData(
                    market,
                    to_binance_granularity(granularity),
                    iso8601start,
                    iso8601end,
                )
            else:
                return api.getHistoricalData(
                    market, to_binance_granularity(granularity)
                )
        else:  # returns data from coinbase if not specified
            api = CBPublicAPI()

            if iso8601start != "" and iso8601end == "":
                return api.getHistoricalData(
                    market, to_coinbase_pro_granularity(granularity), iso8601start
                )
            elif iso8601start != "" and iso8601end != "":
                return api.getHistoricalData(
                    market,
                    to_coinbase_pro_granularity(granularity),
                    iso8601start,
                    iso8601end,
                )
            else:
                return api.getHistoricalData(
                    market, to_coinbase_pro_granularity(granularity)
                )

    def getSmartSwitchDataFrame(
        self,
        df: pd.DataFrame,
        market,
        granularity: int,
        simstart: str = "",
        simend: str = "",
    ) -> pd.DataFrame:

        if self.isSimulation():
            result_df_cache = df

            simstart = self.getDateFromISO8601Str(simstart)
            simend = self.getDateFromISO8601Str(simend)

            try:
                df_first = None
                df_last = None

                # Logger.debug("Row Count (" + str(granularity) + "): " + str(df.shape[0]))
                # if df already has data get first and last record date
                df_first = self.getDateFromISO8601Str(str(df.head(1).index.format()[0]))
                df_last = self.getDateFromISO8601Str(str(df.tail(1).index.format()[0]))

            except Exception:
                # if df = None create a new data frame
                result_df_cache = pd.DataFrame()

            if df_first is None and df_last is None:
                textBox = TextBox(80, 26)
                textBox.singleLine()
                if self.smart_switch:
                    textBox.center("*** Getting smartswitch (" + str(granularity) + ") market data ***")
                else:
                    textBox.center("*** Getting (" + str(granularity) + ") market data ***")

                df_first = simend
                df_first -= timedelta(minutes=(200 * (granularity / 60)))
                df1 = self.getHistoricalData(
                    market,
                    granularity,
                    str(df_first.isoformat()),
                    str(simend.isoformat()),
                )

                result_df_cache = df1
                originalSimStart = self.getDateFromISO8601Str(str(simstart))
                addingExtraCandles = False
                while df_first.isoformat(timespec="milliseconds") > simstart.isoformat(timespec="milliseconds") or df_first.isoformat(timespec="milliseconds") > originalSimStart.isoformat(timespec="milliseconds"):
                    end_date = df_first
                    df_first -= timedelta(minutes=(300 * (granularity / 60)))

                    if df_first.isoformat(timespec="milliseconds") < simstart.isoformat(
                        timespec="milliseconds"
                    ):
                        df_first = self.getDateFromISO8601Str(str(simstart))

                    df2 = self.getHistoricalData(
                        market,
                        granularity,
                        str(df_first.isoformat()),
                        str(end_date.isoformat()),
                    )

                    #check to see if there are an extra 300 candles availble to be used, if not just use the original starting point
                    if (addingExtraCandles == True and df2.size != 2400):
                        self.extraCandlesFound = False
                        simstart = originalSimStart
                    else:
                        result_df_cache = pd.concat(
                        [df2.copy(), df1.copy()]
                        ).drop_duplicates()
                        df1 = result_df_cache
                    
                    #create df with 300 candles before the required startdate to match live
                    if df_first.isoformat(timespec="milliseconds") == simstart.isoformat(timespec="milliseconds"):
                        if addingExtraCandles == False:
                            simstart -= timedelta(minutes=(300 * (granularity / 60)))
                        addingExtraCandles = True
                        self.extraCandlesFound = True

                textBox.doubleLine()

            if len(result_df_cache) > 0 and "morning_star" not in result_df_cache:

                result_df_cache.sort_values(by=["date"], ascending=True, inplace=True)

            if self.smart_switch == False:
                if self.extraCandlesFound == False:
                    textBox = TextBox(80, 26)
                    textBox.singleLine()
                    textBox.center(str(self.exchange) + " is not returning data for the requested start date.")
                    textBox.center("Switching to earliest start date: " + str(result_df_cache.head(1).index.format()[0]))
                    textBox.singleLine()
                    self.simstartdate = str(result_df_cache.head(1).index.format()[0])

            return result_df_cache.copy()

    def getSmartSwitchHistoricalDataChained(
        self,
        market,
        granularity: int,
        start: str = "",
        end: str = "",
    ) -> pd.DataFrame:
        if self.isSimulation():
            self.ema1226_15m_cache = self.getSmartSwitchDataFrame(
                self.ema1226_15m_cache, market, 900, start, end
            )
            self.ema1226_1h_cache = self.getSmartSwitchDataFrame(
                self.ema1226_1h_cache, market, 3600, start, end
            )
            self.ema1226_6h_cache = self.getSmartSwitchDataFrame(
                self.ema1226_6h_cache, market, 21600, start, end
            )

            if self.extraCandlesFound == False:
                if granularity == 900:
                    if self.getDateFromISO8601Str(str(self.ema1226_15m_cache.index.format()[0])).isoformat() != self.getDateFromISO8601Str(start).isoformat():
                        textBox = TextBox(80, 26)
                        textBox.singleLine()
                        textBox.center(str(self.exchange) + " is not returning data for the requested start date.")
                        textBox.center("Switching to earliest start date: " + str(self.ema1226_15m_cache.head(1).index.format()[0]))
                        textBox.singleLine()
                        self.simstartdate = str(self.ema1226_15m_cache.head(1).index.format()[0])
                else:
                    if self.getDateFromISO8601Str(str(self.ema1226_1h_cache.index.format()[0])).isoformat() != self.getDateFromISO8601Str(start).isoformat():
                        textBox = TextBox(80, 26)
                        textBox.singleLine()
                        textBox.center(str(self.exchange) + " is not returning data for the requested start date.")
                        textBox.center("Switching to earliest start date: " + str(self.ema1226_1h_cache.head(1).index.format()[0]))
                        textBox.singleLine()
                        self.simstartdate = str(self.ema1226_1h_cache.head(1).index.format()[0])                    

            if granularity == 900:
                return self.ema1226_15m_cache
            else:
                return self.ema1226_1h_cache

    def getHistoricalDataChained(
        self, market, granularity: int, max_interations: int = 1
    ) -> pd.DataFrame:
        df1 = self.getHistoricalData(market, granularity)

        if max_interations == 1:
            return df1

        def getPreviousDateRange(df: pd.DataFrame = None) -> tuple:
            end_date = df["date"].min() - timedelta(seconds=(granularity / 60))
            new_start = df["date"].min() - timedelta(hours=300)
            return (str(new_start).replace(" ", "T"), str(end_date).replace(" ", "T"))

        iterations = 0
        result_df = pd.DataFrame()
        while iterations < (max_interations - 1):
            start_date, end_date = getPreviousDateRange(df1)
            df2 = self.getHistoricalData(market, granularity, start_date, end_date)
            result_df = pd.concat([df2, df1]).drop_duplicates()
            df1 = result_df
            iterations = iterations + 1

        if "date" in result_df:
            result_df.sort_values(by=["date"], ascending=True, inplace=True)

        return result_df

    def getSmartSwitch(self):
        return self.smart_switch

    def is1hEMA1226Bull(self, iso8601end: str = ""):
        try:
            if self.isSimulation() and isinstance(self.ema1226_1h_cache, pd.DataFrame):
                df_data = self.ema1226_1h_cache.loc[
                    self.ema1226_1h_cache["date"] <= iso8601end
                ].copy()
            elif self.exchange == "coinbasepro":
                api = CBPublicAPI()
                df_data = api.getHistoricalData(self.market, 3600)
                self.ema1226_1h_cache = df_data
            elif self.exchange == "binance":
                api = BPublicAPI(api_url=self.getAPIURL())
                df_data = api.getHistoricalData(self.market, "1h")
                self.ema1226_1h_cache = df_data
            else:
                return False

            ta = TechnicalAnalysis(df_data)

            if "ema12" not in df_data:
                ta.addEMA(12)

            if "ema26" not in df_data:
                ta.addEMA(26)

            df_last = ta.getDataFrame().copy().iloc[-1, :]
            df_last["bull"] = df_last["ema12"] > df_last["ema26"]

            return bool(df_last["bull"])
        except Exception:
            return False

    def is1hSMA50200Bull(self, iso8601end: str = ""):
        try:
            if self.isSimulation() and isinstance(self.sma50200_1h_cache, pd.DataFrame):
                df_data = self.sma50200_1h_cache.loc[
                    self.sma50200_1h_cache["date"] <= iso8601end
                ].copy()
            elif self.exchange == "coinbasepro":
                api = CBPublicAPI()
                df_data = api.getHistoricalData(self.market, 3600)
                self.sma50200_1h_cache = df_data
            elif self.exchange == "binance":
                api = BPublicAPI(api_url=self.getAPIURL())
                df_data = api.getHistoricalData(self.market, "1h")
                self.sma50200_1h_cache = df_data
            else:
                return False

            ta = TechnicalAnalysis(df_data)

            if "sma50" not in df_data:
                ta.addSMA(50)

            if "sma200" not in df_data:
                ta.addSMA(200)

            df_last = ta.getDataFrame().copy().iloc[-1, :]
            df_last["bull"] = df_last["sma50"] > df_last["sma200"]

            return bool(df_last["bull"])
        except Exception:
            return False

    def isCryptoRecession(self):
        try:
            if self.exchange == "coinbasepro":
                api = CBPublicAPI()
                df_data = api.getHistoricalData(self.market, 86400)
            elif self.exchange == "binance":
                api = BPublicAPI(api_url=self.getAPIURL())
                df_data = api.getHistoricalData(self.market, "1d")
            else:
                return False  # if there is an API issue, default to False to avoid hard sells

            if len(df_data) <= 200:
                return False  # if there is insufficient data, default to False to avoid hard sells

            ta = TechnicalAnalysis(df_data)
            ta.addSMA(50)
            ta.addSMA(200)
            df_last = ta.getDataFrame().copy().iloc[-1, :]
            df_last["crypto_recession"] = df_last["sma50"] < df_last["sma200"]

            return bool(df_last["crypto_recession"])
        except Exception:
            return False

    def is6hEMA1226Bull(self, iso8601end: str = ""):
        try:
            if self.isSimulation() and isinstance(self.ema1226_6h_cache, pd.DataFrame):
                df_data = self.ema1226_6h_cache[
                    (self.ema1226_6h_cache["date"] <= iso8601end)
                ].copy()
            elif self.exchange == "coinbasepro":
                api = CBPublicAPI()
                df_data = api.getHistoricalData(self.market, 21600)
                self.ema1226_6h_cache = df_data
            elif self.exchange == "binance":
                api = BPublicAPI(api_url=self.getAPIURL())
                df_data = api.getHistoricalData(self.market, "6h")
                self.ema1226_6h_cache = df_data
            else:
                return False

            ta = TechnicalAnalysis(df_data)

            if "ema12" not in df_data:
                ta.addEMA(12)

            if "ema26" not in df_data:
                ta.addEMA(26)

            df_last = ta.getDataFrame().copy().iloc[-1, :]
            df_last["bull"] = df_last["ema12"] > df_last["ema26"]

            return bool(df_last["bull"])
        except Exception:
            return False

    def is6hSMA50200Bull(self):
        try:
            if self.exchange == "coinbasepro":
                api = CBPublicAPI()
                df_data = api.getHistoricalData(self.market, 21600)
            elif self.exchange == "binance":
                api = BPublicAPI(api_url=self.getAPIURL())
                df_data = api.getHistoricalData(self.market, "6h")
            else:
                return False

            ta = TechnicalAnalysis(df_data)
            ta.addSMA(50)
            ta.addSMA(200)
            df_last = ta.getDataFrame().copy().iloc[-1, :]
            df_last["bull"] = df_last["sma50"] > df_last["sma200"]
            return bool(df_last["bull"])
        except Exception:
            return False

    def getTicker(self, market):
        if self.exchange == "binance":
            api = BPublicAPI(api_url=self.getAPIURL())
            return api.getTicker(market)
        else:  # returns data from coinbase if not specified
            api = CBPublicAPI()
            return api.getTicker(market)

    def getTime(self):
        if self.exchange == "coinbasepro":
            return CBPublicAPI().getTime()
        elif self.exchange == "binance":
            try:
                return BPublicAPI().getTime()
            except ReadTimeoutError:
                return ""
        else:
            return ""

    def isLive(self) -> bool:
        return self.is_live == 1

    def isVerbose(self) -> bool:
        return self.is_verbose == 1

    def shouldSaveGraphs(self) -> bool:
        return self.save_graphs == 1

    def isSimulation(self) -> bool:
        return self.is_sim == 1

    def simuluationSpeed(self):
        return self.sim_speed

    def sellUpperPcnt(self):
        return self.sell_upper_pcnt

    def sellLowerPcnt(self):
        return self.sell_lower_pcnt

    def noSellMinPercent(self):
        return self.nosellminpcnt

    def noSellMaxPercent(self):
        return self.nosellmaxpcnt

    def trailingStopLoss(self):
        return self.trailing_stop_loss

    def buyNearHighPcnt(self) -> float:
        return self.buynearhighpcnt

    def trailingStopLossTrigger(self):
        return self.trailing_stop_loss_trigger

    def allowSellAtLoss(self) -> bool:
        return self.sell_at_loss == 1

    def showConfigBuilder(self) -> bool:
        return self.configbuilder

    def sellAtResistance(self) -> bool:
        return self.sellatresistance

    def autoRestart(self) -> bool:
        return self.autorestart

    def getStats(self) -> bool:
        return self.stats

    def getLastAction(self):
        return self.last_action

    def disableBullOnly(self) -> bool:
        return self.disablebullonly

    def disableBuyNearHigh(self) -> bool:
        return self.disablebuynearhigh

    def disableBuyMACD(self) -> bool:
        return self.disablebuymacd

    def disableBuyEMA(self) -> bool:
        return self.disablebuyema

    def disableBuyOBV(self) -> bool:
        return self.disablebuyobv

    def disableBuyElderRay(self) -> bool:
        return self.disablebuyelderray

    def disableFailsafeFibonacciLow(self) -> bool:
        return self.disablefailsafefibonaccilow

    def disableFailsafeLowerPcnt(self) -> bool:
        return self.disablefailsafelowerpcnt

    def disableProfitbankUpperPcnt(self) -> bool:
        return self.disableprofitbankupperpcnt

    def disableProfitbankReversal(self) -> bool:
        return self.disableprofitbankreversal

    def disableLog(self) -> bool:
        return self.disablelog

    def disableTracker(self) -> bool:
        return self.disabletracker

    def setGranularity(self, granularity: int):
        if granularity in [60, 300, 900, 3600, 21600, 86400]:
            self.granularity = granularity

    def compare(self, val1, val2, label="", precision=2):
        if val1 > val2:
            if label == "":
                return truncate(val1, precision) + " > " + truncate(val2, precision)
            else:
                return (
                    label
                    + ": "
                    + truncate(val1, precision)
                    + " > "
                    + truncate(val2, precision)
                )
        if val1 < val2:
            if label == "":
                return truncate(val1, precision) + " < " + truncate(val2, precision)
            else:
                return (
                    label
                    + ": "
                    + truncate(val1, precision)
                    + " < "
                    + truncate(val2, precision)
                )
        else:
            if label == "":
                return truncate(val1, precision) + " = " + truncate(val2, precision)
            else:
                return (
                    label
                    + ": "
                    + truncate(val1, precision)
                    + " = "
                    + truncate(val2, precision)
                )

    def getLastBuy(self) -> dict:
        """Retrieves the last exchange buy order and returns a dictionary"""

        try:
            if self.exchange == "coinbasepro":
                api = CBAuthAPI(
                    self.getAPIKey(),
                    self.getAPISecret(),
                    self.getAPIPassphrase(),
                    self.getAPIURL(),
                )
                orders = api.getOrders(self.getMarket(), "", "done")

                if len(orders) == 0:
                    return None

                last_order = orders.tail(1)
                if last_order["action"].values[0] != "buy":
                    return None

                return {
                    "side": "buy",
                    "market": self.getMarket(),
                    "size": float(last_order["size"]),
                    "filled": float(last_order["filled"]),
                    "price": float(last_order["price"]),
                    "fee": float(last_order["fees"]),
                    "date": str(
                        pd.DatetimeIndex(
                            pd.to_datetime(last_order["created_at"]).dt.strftime(
                                "%Y-%m-%dT%H:%M:%S.%Z"
                            )
                        )[0]
                    ),
                }
            elif self.exchange == "binance":
                api = BAuthAPI(
                    self.getAPIKey(),
                    self.getAPISecret(),
                    self.getAPIURL(),
                    recv_window=self.recv_window,
                )
                orders = api.getOrders(self.getMarket())

                if len(orders) == 0:
                    return None

                last_order = orders.tail(1)
                if last_order["action"].values[0] != "buy":
                    return None

                return {
                    "side": "buy",
                    "market": self.getMarket(),
                    "size": float(last_order["size"]),
                    "filled": float(last_order["filled"]),
                    "price": float(last_order["price"]),
                    "fees": float(last_order["size"] * 0.001),
                    "date": str(
                        pd.DatetimeIndex(
                            pd.to_datetime(last_order["created_at"]).dt.strftime(
                                "%Y-%m-%dT%H:%M:%S.%Z"
                            )
                        )[0]
                    ),
                }
            else:
                return None
        except Exception:
            return None

    def getTakerFee(self):
        if self.isSimulation() is True and self.exchange == "coinbasepro":
            return 0.005  # default lowest fee tier
        elif self.isSimulation() is True and self.exchange == "binance":
            return 0.001  # default lowest fee tier
        elif self.exchange == "coinbasepro":
            api = CBAuthAPI(
                self.getAPIKey(),
                self.getAPISecret(),
                self.getAPIPassphrase(),
                self.getAPIURL(),
            )
            return api.getTakerFee()
        elif self.exchange == "binance":
            api = BAuthAPI(
                self.getAPIKey(),
                self.getAPISecret(),
                self.getAPIURL(),
                recv_window=self.recv_window,
            )
            return api.getTakerFee()
        else:
            return 0.005

    def getMakerFee(self):
        if self.exchange == "coinbasepro":
            api = CBAuthAPI(
                self.getAPIKey(),
                self.getAPISecret(),
                self.getAPIPassphrase(),
                self.getAPIURL(),
            )
            return api.getMakerFee()
        elif self.exchange == "binance":
            api = BAuthAPI(
                self.getAPIKey(),
                self.getAPISecret(),
                self.getAPIURL(),
                recv_window=self.recv_window,
            )
            return api.getMakerFee()
        else:
            return 0.005

    def marketBuy(self, market, quote_currency, buy_percent=100):
        if self.is_live == 1:
            if isinstance(buy_percent, int):
                if buy_percent > 0 and buy_percent < 100:
                    quote_currency = (buy_percent / 100) * quote_currency

            if self.exchange == "coinbasepro":
                api = CBAuthAPI(
                    self.getAPIKey(),
                    self.getAPISecret(),
                    self.getAPIPassphrase(),
                    self.getAPIURL(),
                )
                return api.marketBuy(market, float(truncate(quote_currency, 2)))
            elif self.exchange == "binance":
                api = BAuthAPI(
                    self.getAPIKey(),
                    self.getAPISecret(),
                    self.getAPIURL(),
                    recv_window=self.recv_window,
                )
                return api.marketBuy(market, quote_currency)
            else:
                return None

    def marketSell(self, market, base_currency, sell_percent=100):
        if self.is_live == 1:
            if isinstance(sell_percent, int):
                if sell_percent > 0 and sell_percent < 100:
                    base_currency = (sell_percent / 100) * base_currency
                if self.exchange == "coinbasepro":
                    api = CBAuthAPI(
                        self.getAPIKey(),
                        self.getAPISecret(),
                        self.getAPIPassphrase(),
                        self.getAPIURL(),
                    )
                    return api.marketSell(market, base_currency)
                elif self.exchange == "binance":
                    api = BAuthAPI(
                        self.getAPIKey(),
                        self.getAPISecret(),
                        self.getAPIURL(),
                        recv_window=self.recv_window,
                    )
                    return api.marketSell(market, base_currency)
            else:
                return None

    def setMarket(self, market):
        if self.exchange == "binance":
            self.market, self.base_currency, self.quote_currency = binanceParseMarket(
                market
            )

        elif self.exchange == "coinbasepro":
            (
                self.market,
                self.base_currency,
                self.quote_currency,
            ) = coinbaseProParseMarket(market)

        return (self.market, self.base_currency, self.quote_currency)

    def setLive(self, flag):
        if isinstance(flag, int) and flag in [0, 1]:
            self.is_live = flag

    def setNoSellAtLoss(self, flag):
        if isinstance(flag, int) and flag in [0, 1]:
            self.sell_at_loss = flag

    def startApp(self, account, last_action="", banner=True):
        if banner:
            self._generate_banner()

        self.appStarted = True
        # run the first job immediately after starting
        if self.isSimulation():
            if self.simuluationSpeed() in ["fast-sample", "slow-sample"]:
                tradingData = pd.DataFrame()

                attempts = 0

                if self.simstartdate is not None and self.simenddate is not None:

                    startDate = self.getDateFromISO8601Str(self.simstartdate)

                    if self.simenddate == "now":
                        endDate = self.getDateFromISO8601Str(str(datetime.now()))
                    else:
                        endDate = self.getDateFromISO8601Str(self.simenddate)

                elif self.simstartdate is not None and self.simenddate is None:
                    # date = self.simstartdate.split('-')
                    startDate = self.getDateFromISO8601Str(self.simstartdate)
                    endDate = startDate + timedelta(
                        minutes=(self.getGranularity() / 60) * 300
                    )

                elif self.simenddate is not None and self.simstartdate is None:
                    if self.simenddate == "now":
                        endDate = self.getDateFromISO8601Str(str(datetime.now()))
                    else:
                        endDate = self.getDateFromISO8601Str(self.simenddate)

                    startDate = endDate - timedelta(
                        minutes=(self.getGranularity() / 60) * 300
                    )

                else:
                    endDate = datetime.now()
                    endDate = self.getDateFromISO8601Str(str(endDate))
                    if self.getExchange() == "coinbasepro":
                        endDate -= timedelta(
                            hours=random.randint(0, 8760 * 3)
                        )  # 3 years in hours
                    else:
                        endDate -= timedelta(hours=random.randint(0, 8760 * 1))

                    startDate = self.getDateFromISO8601Str(str(endDate))
                    startDate -= timedelta(minutes=(self.getGranularity() / 60) * 300)

                while len(tradingData) < 300 and attempts < 10:
                    if self.smart_switch == 1:
                        tradingData = self.getSmartSwitchHistoricalDataChained(
                            self.market,
                            self.getGranularity(),
                            str(startDate),
                            str(endDate),
                        )

                    else:
                        tradingData = self.getSmartSwitchDataFrame(
                            tradingData, 
                            self.market, 
                            self.getGranularity(), 
                            startDate.isoformat(), 
                            endDate.isoformat())

                    attempts += 1

                if self.extraCandlesFound:
                    self.simstartdate = str(startDate)
                    self.simenddate = str(endDate)

                self.extraCandlesFound = True

                if len(tradingData) < 300:
                    raise Exception(
                        "Unable to retrieve 300 random sets of data between "
                        + str(startDate)
                        + " and "
                        + str(endDate)
                        + " in 10 attempts."
                    )

                if banner:
                    textBox = TextBox(80, 26)
                    startDate = str(startDate.isoformat())
                    endDate = str(endDate.isoformat())
                    textBox.line("Sampling start", str(startDate))
                    textBox.line("Sampling end", str(endDate))
                    if self.simstartdate != None and len(tradingData) < 300:
                        textBox.center("WARNING: Using less than 300 intervals")
                        textBox.line("Interval size", str(len(tradingData)))
                    textBox.doubleLine()

            else:
                tradingData = pd.DataFrame()

                startDate = self.getDateFromISO8601Str(str(datetime.now()))
                endDate = startDate
                startDate = pd.Series(startDate).dt.round(freq = 'H')[0]
                endDate = pd.Series(endDate).dt.round(freq = 'H')[0]
                startDate -= timedelta(minutes=(self.getGranularity() / 60) * 300)

                tradingData = self.getSmartSwitchDataFrame(tradingData,
                    self.getMarket(), self.getGranularity(), self.getDateFromISO8601Str(str(startDate)).isoformat(), endDate.isoformat())
                if self.extraCandlesFound:
                    self.simstartdate = str(pd.Series(startDate).dt.round(freq = 'H')[0])
                    self.simenddate = str(pd.Series(endDate).dt.round(freq = 'H')[0])

                self.extraCandlesFound = True

            return tradingData

    def notifyTelegram(self, msg: str) -> None:
        """
        Send a given message to preconfigured Telegram. If the telegram isn't enabled, e.g. via `--disabletelegram`,
        this method does nothing and returns immediately.
        """

        if self.disabletelegram or not self.telegram:
            return

        assert self._chat_client is not None

        self._chat_client.send(msg)

    def _generate_banner(self) -> None:
        textBox = TextBox(80, 26)
        textBox.singleLine()
        textBox.center("Python Crypto Bot")
        textBox.singleLine()
        textBox.line("Release", self.getVersionFromREADME())
        textBox.singleLine()

        if self.isVerbose():
            textBox.line("Market", self.getMarket())
            textBox.line("Granularity", str(self.getGranularity()) + " seconds")
            textBox.singleLine()

        if self.isLive():
            textBox.line("Bot Mode", "LIVE - live trades using your funds!")
        else:
            textBox.line("Bot Mode", "TEST - test trades using dummy funds :)")

        textBox.line("Bot Started", str(datetime.now()))
        textBox.line("Exchange", str(self.exchange))
        textBox.doubleLine()

        if self.sellUpperPcnt() != None:
            textBox.line("Sell Upper", str(self.sellUpperPcnt()) + "%  --sellupperpcnt  <pcnt>")

        if self.sellLowerPcnt() != None:
            textBox.line("Sell Lower", str(self.sellLowerPcnt()) + "%  --selllowerpcnt  <pcnt>")

        if self.noSellMaxPercent() != None:
            textBox.line("No Sell Max", str(self.noSellMaxPercent()) + "%  --nosellmaxpcnt  <pcnt>")

        if self.noSellMinPercent() != None:
            textBox.line("No Sell Min", str(self.noSellMinPercent()) + "%  --nosellminpcnt  <pcnt>")

        if self.trailingStopLoss() != None:
            textBox.line("Trailing Stop Loss", str(self.trailingStopLoss()) + "%  --trailingstoploss  <pcnt>")

        if self.trailingStopLossTrigger() != None:
            textBox.line(
                "Trailing Stop Loss Trg", str(self.trailingStopLossTrigger()) + "%  --trailingstoplosstrigger"
            )

        textBox.line(
            "Sell At Loss",
            str(self.allowSellAtLoss())
            + "  --sellatloss "
        )
        textBox.line(
            "Sell At Resistance", str(self.sellAtResistance()) + "  --sellatresistance"
        )
        textBox.line(
            "Trade Bull Only", str(not self.disableBullOnly()) + "  --disablebullonly"
        )
        textBox.line(
            "Buy Near High",
            str(not self.disableBuyNearHigh()) + "  --disablebuynearhigh",
        )
        if self.disableBuyNearHigh():
            textBox.line(
                "Buy Near High Pcnt",
                str(self.buyNearHighPcnt()) + "% --buynearhighpcnt <pcnt>",
            )
        textBox.line(
            "Use Buy MACD", str(not self.disableBuyMACD()) + "  --disablebuymacd"
        )
        textBox.line("Use Buy EMA", str(not self.disableBuyEMA()) + "  --disablebuyema")
        textBox.line("Use Buy OBV", str(not self.disableBuyOBV()) + "  --disablebuyobv")
        textBox.line(
            "Use Buy Elder-Ray",
            str(not self.disableBuyElderRay()) + "  --disablebuyelderray",
        )
        textBox.line(
            "Sell Fibonacci Low",
            str(not self.disableFailsafeFibonacciLow())
            + "  --disablefailsafefibonaccilow",
        )

        if self.sellLowerPcnt() != None:
            textBox.line(
                "Sell Lower Pcnt",
                str(not self.disableFailsafeLowerPcnt())
                + "  --disablefailsafelowerpcnt",
            )

        if self.sellUpperPcnt() != None:
            textBox.line(
                "Sell Upper Pcnt",
                str(not self.disableFailsafeLowerPcnt())
                + "  --disableprofitbankupperpcnt",
            )

        textBox.line(
            "Candlestick Reversal",
            str(not self.disableProfitbankReversal()) + "  --disableprofitbankreversal",
        )
        textBox.line("Telegram", str(not self.disabletelegram) + "  --disabletelegram")
        textBox.line("Log", str(not self.disableLog()) + "  --disablelog")
        textBox.line("Tracker", str(not self.disableTracker()) + "  --disabletracker")
        textBox.line("Auto restart Bot", str(self.autoRestart()) + "  --autorestart")

        if self.getBuyMaxSize():
            textBox.line(
                "Max Buy Size", str(self.getBuyMaxSize()) + "  --buymaxsize <size>"
            )

        if self.disablebuyema and self.disablebuymacd:
            textBox.center(
                "WARNING : EMA and MACD indicators disabled, no buy events will happen"
            )

        textBox.doubleLine()
