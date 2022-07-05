import json
import math
import random
import re
from datetime import datetime, timedelta
from typing import Union

import pandas as pd
import urllib3
from urllib3.exceptions import ReadTimeoutError

from models.BotConfig import BotConfig
from models.Trading import TechnicalAnalysis
from models.config import binanceParseMarket, coinbaseProParseMarket, kucoinParseMarket
from models.exchange.Granularity import Granularity
from models.exchange.ExchangesEnum import Exchange
from models.exchange.binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import AuthAPI as CBAuthAPI, PublicAPI as CBPublicAPI
from models.exchange.kucoin import AuthAPI as KAuthAPI, PublicAPI as KPublicAPI
from models.helper.TextBoxHelper import TextBox

# disable insecure ssl warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

pd.set_option('display.float_format', '{:.8f}'.format)


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
    def __init__(self, config_file: str = None, exchange: Exchange = None):
        self.config_file = config_file or "config.json"
        self.exchange = exchange
        super(PyCryptoBot, self).__init__(
            filename=self.config_file, exchange=self.exchange
        )

    takerfee = 0.0

    extraCandlesFound = False

    trade_tracker = pd.DataFrame(
        columns=[
            "Datetime",
            "Market",
            "Action",
            "Price",
            "Base",
            "Quote",
            "Margin",
            "Profit",
            "Fee",
            "DF_High",
            "DF_Low",
        ]
    )

    def getConfig(self) -> dict:
        try:
            config = json.loads(open(self.config_file, "r", encoding="utf8").read())

            if self.exchange.value in config:
                if "config" in config[self.exchange.value]:
                    return config[self.exchange.value]["config"]
                else:
                    return {}
            else:
                return {}
        except IOError:
            return {}

    def _isCurrencyValid(self, currency):
        if (
            self.exchange == Exchange.COINBASEPRO
            or self.exchange == Exchange.BINANCE
            or self.exchange == Exchange.KUCOIN
        ):
            p = re.compile(r"^[0-9A-Z]{1,20}$")
            return p.match(currency)

        return False

    def _isMarketValid(self, market):
        if self.exchange == Exchange.COINBASEPRO or self.exchange == Exchange.KUCOIN:
            p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
            return p.match(market)
        elif self.exchange == Exchange.BINANCE:
            p = re.compile(r"^[A-Z0-9]{4,25}$")
            if p.match(market):
                return True
            p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
            if p.match(market):
                return True
            return False

        return False

    def getRecvWindow(self):
        return self.recv_window

    def getLogFile(self):
        return self.logfile

    def getTradesFile(self):
        return self.tradesfile

    def getExchange(self) -> Exchange:
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
        if self.exchange == Exchange.BINANCE:
            formatCheck = self.market.split("-") if self.market.find("-") != -1 else ""
            if not formatCheck == "":
                self.base_currency = formatCheck[0]
                self.quote_currency = formatCheck[1]
            self.market = self.base_currency + self.quote_currency

        # Logger.info(self.market)
        return self.market

    def getGranularity(self) -> Granularity:
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
        if self.exchange == Exchange.KUCOIN:
            return self.granularity.to_medium
        if self.exchange == Exchange.BINANCE:
            return self.granularity.to_short
        if self.exchange == Exchange.COINBASEPRO:
            return str(self.granularity.to_integer)
        if self.exchange == Exchange.DUMMY:
            return str(self.granularity.to_integer)
        raise TypeError(f'Unknown exchange "{self.exchange.name}"')

    def getBuyPercent(self):
        try:
            return int(self.buypercent)
        except Exception:  # pylint: disable=broad-except
            return 100

    def getSellPercent(self):
        try:
            return int(self.sellpercent)
        except Exception:  # pylint: disable=broad-except
            return 100

    def getBuyMaxSize(self):
        try:
            return float(self.buymaxsize)
        except Exception:  # pylint: disable=broad-except
            return None

    def getBuyMinSize(self):
        try:
            return float(self.buyminsize)
        except Exception:  # pylint: disable=broad-except
            return None

    def buyLastSellSize(self) -> bool:
        return self.buylastsellsize

    def getTrailingBuyPcnt(self):
        try:
            return float(self.trailingbuypcnt)
        except Exception:  # pylint: disable=broad-except
            return 0

    def trailingImmediateBuy(self) -> bool:
        return self.trailingimmediatebuy

    def getTrailingBuyImmediatePcnt(self):
        try:
            return float(self.trailingbuyimmediatepcnt)
        except Exception:  # pylint: disable=broad-except
            return None

    def getTrailingSellPcnt(self):
        try:
            return float(self.trailingsellpcnt)
        except Exception:  # pylint: disable=broad-except
            return 0

    def trailingImmediateSell(self) -> bool:
        return self.trailingimmediatesell

    def getTrailingSellImmediatePcnt(self):
        try:
            return float(self.trailingsellimmediatepcnt)
        except Exception:  # pylint: disable=broad-except
            return None

    def getTrailingSellBailoutPcnt(self):
        try:
            return float(self.trailingsellbailoutpcnt)
        except Exception:  # pylint: disable=broad-except
            return None

    def sellTriggerOverride(self) -> bool:
        return self.sell_trigger_override

    def marketMultiBuyCheck(self) -> bool:
        return self.marketmultibuycheck

    def getBuyNearHighPcnt(self):
        try:
            return float(self.nobuynearhighpcnt)
        except Exception:  # pylint: disable=broad-except
            return None

    def getDateFromISO8601Str(self, date: str):
        # if date passed from datetime.now() remove milliseconds
        if date.find(".") != -1:
            dt = date.split(".")[0]
            date = dt

        date = date.replace("T", " ") if date.find("T") != -1 else date
        # add time in case only a date is passed in
        new_date_str = f"{date} 00:00:00" if len(date) == 10 else date
        return datetime.strptime(new_date_str, "%Y-%m-%d %H:%M:%S")

    def getHistoricalData(
        self,
        market,
        granularity: Granularity,
        websocket,
        iso8601start="",
        iso8601end="",
    ):
        if self.exchange == Exchange.BINANCE:
            api = BPublicAPI(api_url=self.getAPIURL())

        elif (
            self.exchange == Exchange.KUCOIN
        ):  # returns data from coinbase if not specified
            api = KPublicAPI(api_url=self.getAPIURL())

            # Kucoin only returns 100 rows if start not specified, make sure we get the right amount
            if not self.isSimulation() and iso8601start == "":
                start = datetime.now() -  timedelta(minutes=(granularity.to_integer / 60) * self.setTotalPeriods())
                iso8601start = str(start.isoformat()).split('.')[0]

        else:  # returns data from coinbase if not specified
            api = CBPublicAPI()

        if iso8601start != "" and iso8601end == "" and self.exchange != Exchange.BINANCE:
            return api.getHistoricalData(
                market,
                granularity,
                None,
                iso8601start,
            )
        elif iso8601start != "" and iso8601end != "":
            return api.getHistoricalData(
                market,
                granularity,
                None,
                iso8601start,
                iso8601end,
            )
        else:
            return api.getHistoricalData(market, granularity, websocket)

    def getSmartSwitchDataFrame(
        self,
        df: pd.DataFrame,
        market,
        granularity: Granularity,
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

                # logger.debug("Row Count (" + str(granularity) + "): " + str(df.shape[0]))
                # if df already has data get first and last record date
                df_first = self.getDateFromISO8601Str(str(df.head(1).index.format()[0]))
                df_last = self.getDateFromISO8601Str(str(df.tail(1).index.format()[0]))

            except Exception:  # pylint: disable=broad-except
                # if df = None create a new data frame
                result_df_cache = pd.DataFrame()

            if df_first is None and df_last is None:
                text_box = TextBox(80, 26)

                if not self.isSimulation() or (
                    self.isSimulation() and not self.simResultOnly()
                ):
                    text_box.singleLine()
                    if self.smart_switch:
                        text_box.center(
                            f"*** Getting smartswitch ({granularity.to_short}) market data ***"
                        )
                    else:
                        text_box.center(
                            f"*** Getting ({granularity.to_short}) market data ***"
                        )

                df_first = simend
                df_first -= timedelta(minutes=((granularity.to_integer / 60) * 200))
                df1 = self.getHistoricalData(
                    market,
                    granularity,
                    None,
                    str(df_first.isoformat()),
                    str(simend.isoformat()),
                )

                result_df_cache = df1
                originalSimStart = self.getDateFromISO8601Str(str(simstart))
                addingExtraCandles = False
                while df_first.isoformat(timespec="milliseconds") > simstart.isoformat(
                    timespec="milliseconds"
                ) or df_first.isoformat(
                    timespec="milliseconds"
                ) > originalSimStart.isoformat(
                    timespec="milliseconds"
                ):

                    end_date = df_first
                    df_first -= timedelta(minutes=(self.setTotalPeriods() * (granularity.to_integer / 60)))

                    if df_first.isoformat(timespec="milliseconds") < simstart.isoformat(
                        timespec="milliseconds"
                    ):
                        df_first = self.getDateFromISO8601Str(str(simstart))

                    df2 = self.getHistoricalData(
                        market,
                        granularity,
                        None,
                        str(df_first.isoformat()),
                        str(end_date.isoformat()),
                    )

                    # check to see if there are an extra 300 candles available to be used, if not just use the original starting point
                    if self.setTotalPeriods() >= 300 and addingExtraCandles == True and len(df2) <= 0:
                        self.extraCandlesFound = False
                        simstart = originalSimStart
                    else:
                        result_df_cache = pd.concat(
                            [df2.copy(), df1.copy()]
                        ).drop_duplicates()
                        df1 = result_df_cache

                    # create df with 300 candles or adjusted total periods before the required startdate to match live
                    if df_first.isoformat(
                        timespec="milliseconds"
                    ) == simstart.isoformat(timespec="milliseconds"):
                        if addingExtraCandles == False:
                            simstart -= timedelta(
                                minutes=(self.setTotalPeriods() * (granularity.to_integer / 60))
                            )
                        addingExtraCandles = True
                        self.extraCandlesFound = True

                if not self.isSimulation() or (
                    self.isSimulation() and not self.simResultOnly()
                ):
                    text_box.doubleLine()

            if len(result_df_cache) > 0 and "morning_star" not in result_df_cache:
                result_df_cache.sort_values(by=["date"], ascending=True, inplace=True)

            if self.smart_switch == False:
                if self.extraCandlesFound == False:
                    text_box = TextBox(80, 26)
                    text_box.singleLine()
                    text_box.center(
                        f"{str(self.exchange.value)} is not returning data for the requested start date."
                    )
                    text_box.center(
                        f"Switching to earliest start date: {str(result_df_cache.head(1).index.format()[0])}"
                    )
                    text_box.singleLine()
                    self.simstartdate = str(result_df_cache.head(1).index.format()[0])

            return result_df_cache.copy()

    def getSmartSwitchHistoricalDataChained(
        self,
        market,
        granularity: Granularity,
        start: str = "",
        end: str = "",
    ) -> pd.DataFrame:

        if self.isSimulation():
            if self.getSellSmartSwitch() == 1:
                self.ema1226_5m_cache = self.getSmartSwitchDataFrame(
                    self.ema1226_5m_cache, market, Granularity.FIVE_MINUTES, start, end
                )
            self.ema1226_15m_cache = self.getSmartSwitchDataFrame(
                self.ema1226_15m_cache, market, Granularity.FIFTEEN_MINUTES, start, end
            )
            self.ema1226_1h_cache = self.getSmartSwitchDataFrame(
                self.ema1226_1h_cache, market, Granularity.ONE_HOUR, start, end
            )
            self.ema1226_6h_cache = self.getSmartSwitchDataFrame(
                self.ema1226_6h_cache, market, Granularity.SIX_HOURS, start, end
            )

            if len(self.ema1226_15m_cache) == 0:
                raise Exception(
                    f"No data return for selected date range {start} - {end}"
                )

            if not self.extraCandlesFound:
                if granularity == Granularity.FIVE_MINUTES:
                    if (
                        self.getDateFromISO8601Str(
                            str(self.ema1226_5m_cache.index.format()[0])
                        ).isoformat()
                        != self.getDateFromISO8601Str(start).isoformat()
                    ):
                        text_box = TextBox(80, 26)
                        text_box.singleLine()
                        text_box.center(
                            f"{str(self.exchange.value)}is not returning data for the requested start date."
                        )
                        text_box.center(
                            f"Switching to earliest start date: {str(self.ema1226_5m_cache.head(1).index.format()[0])}"
                        )
                        text_box.singleLine()
                        self.simstartdate = str(
                            self.ema1226_5m_cache.head(1).index.format()[0]
                        )
                elif granularity == Granularity.FIFTEEN_MINUTES:
                    if (
                        self.getDateFromISO8601Str(
                            str(self.ema1226_15m_cache.index.format()[0])
                        ).isoformat()
                        != self.getDateFromISO8601Str(start).isoformat()
                    ):
                        text_box = TextBox(80, 26)
                        text_box.singleLine()
                        text_box.center(
                            f"{str(self.exchange.value)}is not returning data for the requested start date."
                        )
                        text_box.center(
                            f"Switching to earliest start date: {str(self.ema1226_15m_cache.head(1).index.format()[0])}"
                        )
                        text_box.singleLine()
                        self.simstartdate = str(
                            self.ema1226_15m_cache.head(1).index.format()[0]
                        )
                else:
                    if (
                        self.getDateFromISO8601Str(
                            str(self.ema1226_1h_cache.index.format()[0])
                        ).isoformat()
                        != self.getDateFromISO8601Str(start).isoformat()
                    ):
                        text_box = TextBox(80, 26)
                        text_box.singleLine()
                        text_box.center(
                            f"{str(self.exchange.value)} is not returning data for the requested start date."
                        )
                        text_box.center(
                            f"Switching to earliest start date: {str(self.ema1226_1h_cache.head(1).index.format()[0])}"
                        )
                        text_box.singleLine()
                        self.simstartdate = str(
                            self.ema1226_1h_cache.head(1).index.format()[0]
                        )

            if granularity == Granularity.FIFTEEN_MINUTES:
                return self.ema1226_15m_cache
            elif granularity == Granularity.FIVE_MINUTES:
                return self.ema1226_5m_cache
            else:
                return self.ema1226_1h_cache

    def getHistoricalDataChained(
        self, market, granularity: Granularity, max_iterations: int = 1
    ) -> pd.DataFrame:
        df1 = self.getHistoricalData(market, granularity, None)

        if max_iterations == 1:
            return df1

        def getPreviousDateRange(df: pd.DataFrame = None) -> tuple:
            end_date = df["date"].min() - timedelta(
                seconds=(granularity.to_integer / 60)
            )
            new_start = df["date"].min() - timedelta(hours=self.setTotalPeriods())
            return (str(new_start).replace(" ", "T"), str(end_date).replace(" ", "T"))

        iterations = 0
        result_df = pd.DataFrame()
        while iterations < (max_iterations - 1):
            start_date, end_date = getPreviousDateRange(df1)
            df2 = self.getHistoricalData(
                market, granularity, None, start_date, end_date
            )
            result_df = pd.concat([df2, df1]).drop_duplicates()
            df1 = result_df
            iterations = iterations + 1

        if "date" in result_df:
            result_df.sort_values(by=["date"], ascending=True, inplace=True)

        return result_df

    def getSmartSwitch(self):
        return self.smart_switch

    def getSellSmartSwitch(self):
        return self.sell_smart_switch

    def getAdditionalDf(
        self,
        short_granularity,
        websocket
    ) -> pd.DataFrame:

        granularity = Granularity.convert_to_enum(short_granularity)

        idx, next_idx = (None, 0)
        for i in range(len(self.df_data)):
            if isinstance(self.df_data[i], list) and self.df_data[i][0] == short_granularity:
                idx = i
            elif isinstance(self.df_data[i], list):
                next_idx = i + 1
            else:
                break

        # idx list:
        # 0 = short_granularity (1h, 6h, 1d, 5m, 15m, etc.)
        # 1 = granularity (ONE_HOUR, SIX_HOURS, FIFTEEN_MINUTES, etc.)
        # 2 = df row (for last candle date)
        # 3 = DataFrame
        if idx is None:
            idx = next_idx
            self.df_data[idx] = [short_granularity, granularity, -1, pd.DataFrame()]


        df = self.df_data[idx][3]
        row = self.df_data[idx][2]
        try:
            if (
                len(df) == 0 # empty dataframe
                or (len(df) > 0
                    and ( # if exists, only refresh at candleclose
                        datetime.timestamp(
                            datetime.utcnow()
                        ) - granularity.to_integer >= datetime.timestamp(
                            df["date"].iloc[row]
                        )
                    )
                )
            ):
                df = self.getHistoricalData(
                    self.getMarket(), granularity, websocket
                )
                row = -1
            else:
                # if ticker hasn't run yet or hasn't updated, return the original df
                if websocket is not None and self.ticker_date is None:
                    return df
                elif ( # if calling API multiple times, per iteration, ticker may not be updated yet
                    self.ticker_date is None
                    or datetime.timestamp(
                            datetime.utcnow()
                        ) - 60 <= datetime.timestamp(
                            df["date"].iloc[row]
                        )
                ):
                    return df
                elif row == -2: # update the new row added for ticker if it is there
                    df.iloc[-1, df.columns.get_loc('low')] = self.ticker_price if self.ticker_price < df["low"].iloc[-1] else df["low"].iloc[-1]
                    df.iloc[-1, df.columns.get_loc('high')] = self.ticker_price if self.ticker_price > df["high"].iloc[-1] else df["high"].iloc[-1]
                    df.iloc[-1, df.columns.get_loc('close')] = self.ticker_price
                    df.iloc[-1, df.columns.get_loc('date')] = datetime.strptime(self.ticker_date, "%Y-%m-%d %H:%M:%S")
                    tsidx = pd.DatetimeIndex(df["date"])
                    df.set_index(tsidx, inplace=True)
                    df.index.name = "ts"
                else: # else we are adding a new row for the ticker data
                    new_row = pd.DataFrame(
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
                                datetime.strptime(self.ticker_date, "%Y-%m-%d %H:%M:%S"),
                                df["market"].iloc[-1],
                                df["granularity"].iloc[-1],
                                (self.ticker_price if self.ticker_price < df["close"].iloc[-1] else df["close"].iloc[-1]),
                                (self.ticker_price if self.ticker_price > df["close"].iloc[-1] else df["close"].iloc[-1]),
                                df["close"].iloc[-1],
                                self.ticker_price,
                                df["volume"].iloc[-1]
                            ]
                        ]
                    )
                    df = pd.concat([df, new_row], ignore_index = True)

                    tsidx = pd.DatetimeIndex(df["date"])
                    df.set_index(tsidx, inplace=True)
                    df.index.name = "ts"
                    row = -2

            self.df_data[idx][3] = df
            self.df_data[idx][2] = row
            return df
        except Exception as err:
            raise Exception(f"Additional DF Error: {err}")

    def is1hEMA1226Bull(self, iso8601end: str = "", websocket=None):
        try:
            if self.isSimulation() and isinstance(self.ema1226_1h_cache, pd.DataFrame):
                df_data = self.ema1226_1h_cache.loc[
                    self.ema1226_1h_cache["date"] <= iso8601end
                ].copy()
            elif self.getExchange() != Exchange.DUMMY:
                df_data = self.getAdditionalDf("1h", websocket).copy()
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
        except Exception as err:
            return False

    def is1hSMA50200Bull(self, iso8601end: str = "", websocket=None):
        # if periods adjusted and less than 200
        if self.setTotalPeriods() < 200:
            return False

        try:
            if self.isSimulation() and isinstance(self.sma50200_1h_cache, pd.DataFrame):
                df_data = self.sma50200_1h_cache.loc[
                    self.sma50200_1h_cache["date"] <= iso8601end
                ].copy()
            elif self.getExchange() != Exchange.DUMMY:
                df_data = self.getAdditionalDf("1h", websocket).copy()
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

    def isCryptoRecession(self, websocket=None):
        # if periods adjusted and less than 200
        if self.setTotalPeriods() < 200:
            return False

        try:
            if self.getExchange() != Exchange.DUMMY:
                df_data = self.getAdditionalDf("1d", websocket).copy()
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

    def is6hEMA1226Bull(self, iso8601end: str = "", websocket=None):
        try:
            if self.isSimulation() and isinstance(self.ema1226_6h_cache, pd.DataFrame):
                df_data = self.ema1226_6h_cache[
                    (self.ema1226_6h_cache["date"] <= iso8601end)
                ].copy()
            elif self.getExchange() != Exchange.DUMMY:
                df_data = self.getAdditionalDf("6h", websocket).copy()
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
        except Exception as err:
            return False

    def is6hSMA50200Bull(self, websocket):
        # if periods adjusted and less than 200
        if self.setTotalPeriods() < 200:
            return False

        try:
            if self.getExchange() != Exchange.DUMMY:
                df_data = self.getAdditionalDf("6h", websocket).copy()
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

    def getTicker(self, market, websocket):
        if self.exchange == Exchange.BINANCE:
            api = BPublicAPI(api_url=self.getAPIURL())
            return api.getTicker(market, websocket)

        elif self.exchange == Exchange.KUCOIN:
            api = KPublicAPI(api_url=self.getAPIURL())
            return api.getTicker(market, websocket)
        else:  # returns data from coinbase if not specified
            api = CBPublicAPI()
            return api.getTicker(market, websocket)

    def getTime(self):
        if self.exchange == Exchange.COINBASEPRO:
            return CBPublicAPI().getTime()
        elif self.exchange == Exchange.KUCOIN:
            return KPublicAPI().getTime()
        elif self.exchange == Exchange.BINANCE:
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

    def noBuyNearHighPcnt(self) -> float:
        return self.nobuynearhighpcnt

    def trailingStopLossTrigger(self):
        return self.trailing_stop_loss_trigger

    def dynamicTSL(self) -> bool:
        return self.dynamic_tsl

    def TSLMultiplier(self):
        return self.tsl_multiplier

    def TSLTriggerMultiplier(self):
        return self.tsl_trigger_multiplier

    def TSLMaxPcnt(self) -> float:
        return self.tsl_max_pcnt

    def preventLoss(self):
        return self.preventloss

    def preventLossTrigger(self) -> float:
        return self.preventlosstrigger

    def preventLossMargin(self):
        return self.preventlossmargin

    def allowSellAtLoss(self) -> bool:
        return self.sell_at_loss == 1

    def simResultOnly(self) -> bool:
        return self.simresultonly

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

    def enableInsufficientFundsLogging(self) -> bool:
        return self.enableinsufficientfundslogging

    def enableTelegramBotControl(self) -> bool:
        return self.enabletelegrambotcontrol

    def enableImmediateBuy(self) -> bool:
        return self.enableimmediatebuy

    def telegramTradesOnly(self) -> bool:
        return self.telegramtradesonly

    def disableTelegramErrorMsgs(self) -> bool:
        return self.disabletelegramerrormsgs

    def enableML(self) -> bool:
        return self.enableml

    def enablePandasTA(self) -> bool:
        return self.enable_pandas_ta

    def enableCustomStrategy(self) -> bool:
        return self.enable_custom_strategy

    def enableWebsocket(self) -> bool:
        return self.websocket

    def enabledLogBuySellInJson(self) -> bool:
        return self.logbuysellinjson

    def setGranularity(self, granularity: Granularity):
        self.granularity = granularity

    def useKucoinCache(self) -> bool:
        return self.usekucoincache

    def setTotalPeriods(self) -> float:
        return self.adjust_total_periods

    def manualTradesOnly(self) -> bool:
        return self.manual_trades_only

    def compare(self, val1, val2, label="", precision=2):
        if val1 > val2:
            if label == "":
                return f"{truncate(val1, precision)} > {truncate(val2, precision)}"
            else:
                return f"{label}: {truncate(val1, precision)} > {truncate(val2, precision)}"
        if val1 < val2:
            if label == "":
                return f"{truncate(val1, precision)} < {truncate(val2, precision)}"
            else:
                return f"{label}: {truncate(val1, precision)} < {truncate(val2, precision)}"
        else:
            if label == "":
                return f"{truncate(val1, precision)} = {truncate(val2, precision)}"
            else:
                return f"{label}: {truncate(val1, precision)} = {truncate(val2, precision)}"

    def getLastBuy(self) -> dict:
        """Retrieves the last exchange buy order and returns a dictionary"""

        try:
            if self.exchange == Exchange.COINBASEPRO:
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
            elif self.exchange == Exchange.KUCOIN:
                api = KAuthAPI(
                    self.getAPIKey(),
                    self.getAPISecret(),
                    self.getAPIPassphrase(),
                    self.getAPIURL(),
                    use_cache=self.useKucoinCache(),
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
            elif self.exchange == Exchange.BINANCE:
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
        if self.isSimulation() is True and self.exchange == Exchange.COINBASEPRO:
            return 0.005  # default lowest fee tier
        elif self.isSimulation() is True and self.exchange == Exchange.BINANCE:
            return 0.001  # default lowest fee tier
        elif self.isSimulation() is True and self.exchange == Exchange.KUCOIN:
            return 0.0015  # default lowest fee tier
        elif self.takerfee > 0.0:
            return self.takerfee
        elif self.exchange == Exchange.COINBASEPRO:
            api = CBAuthAPI(
                self.getAPIKey(),
                self.getAPISecret(),
                self.getAPIPassphrase(),
                self.getAPIURL(),
            )
            self.takerfee = api.getTakerFee()
            return self.takerfee
        elif self.exchange == Exchange.BINANCE:
            api = BAuthAPI(
                self.getAPIKey(),
                self.getAPISecret(),
                self.getAPIURL(),
                recv_window=self.recv_window,
            )
            self.takerfee = api.getTakerFee()
            return self.takerfee
        elif self.exchange == Exchange.KUCOIN:
            api = KAuthAPI(
                self.getAPIKey(),
                self.getAPISecret(),
                self.getAPIPassphrase(),
                self.getAPIURL(),
                use_cache=self.useKucoinCache(),
            )
            self.takerfee = api.getTakerFee()
            return self.takerfee
        else:
            return 0.005

    def getMakerFee(self):
        if self.exchange == Exchange.COINBASEPRO:
            api = CBAuthAPI(
                self.getAPIKey(),
                self.getAPISecret(),
                self.getAPIPassphrase(),
                self.getAPIURL(),
            )
            return api.getMakerFee()
        elif self.exchange == Exchange.BINANCE:
            api = BAuthAPI(
                self.getAPIKey(),
                self.getAPISecret(),
                self.getAPIURL(),
                recv_window=self.recv_window,
            )
            return api.getMakerFee()
        elif self.exchange == Exchange.KUCOIN:
            api = KAuthAPI(
                self.getAPIKey(),
                self.getAPISecret(),
                self.getAPIPassphrase(),
                self.getAPIURL(),
                use_cache=self.useKucoinCache(),
            )
            return api.getMakerFee()
        else:
            return 0.005

    def marketBuy(self, market, quote_currency, buy_percent=100):
        if self.is_live == 1:
            if isinstance(buy_percent, int):
                if buy_percent > 0 and buy_percent < 100:
                    quote_currency = (buy_percent / 100) * quote_currency

            if self.exchange == Exchange.COINBASEPRO:
                api = CBAuthAPI(
                    self.getAPIKey(),
                    self.getAPISecret(),
                    self.getAPIPassphrase(),
                    self.getAPIURL(),
                )
                return api.marketBuy(market, float(truncate(quote_currency, 8)))
            elif self.exchange == Exchange.KUCOIN:
                api = KAuthAPI(
                    self.getAPIKey(),
                    self.getAPISecret(),
                    self.getAPIPassphrase(),
                    self.getAPIURL(),
                    use_cache=self.useKucoinCache(),
                )
                return api.marketBuy(market, float(quote_currency))
            elif self.exchange == Exchange.BINANCE:
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
                if self.exchange == Exchange.COINBASEPRO:
                    api = CBAuthAPI(
                        self.getAPIKey(),
                        self.getAPISecret(),
                        self.getAPIPassphrase(),
                        self.getAPIURL(),
                    )
                    return api.marketSell(market, base_currency)
                elif self.exchange == Exchange.BINANCE:
                    api = BAuthAPI(
                        self.getAPIKey(),
                        self.getAPISecret(),
                        self.getAPIURL(),
                        recv_window=self.recv_window,
                    )
                    return api.marketSell(market, base_currency, use_fees=self.use_sell_fee)
                elif self.exchange == Exchange.KUCOIN:
                    api = KAuthAPI(
                        self.getAPIKey(),
                        self.getAPISecret(),
                        self.getAPIPassphrase(),
                        self.getAPIURL(),
                        use_cache=self.useKucoinCache(),
                    )
                    return api.marketSell(market, base_currency)
            else:
                return None

    def setMarket(self, market):
        if self.exchange == Exchange.BINANCE:
            self.market, self.base_currency, self.quote_currency = binanceParseMarket(
                market
            )

        elif self.exchange == Exchange.COINBASEPRO:
            (
                self.market,
                self.base_currency,
                self.quote_currency,
            ) = coinbaseProParseMarket(market)

        elif self.exchange == Exchange.KUCOIN:
            (self.market, self.base_currency, self.quote_currency) = kucoinParseMarket(
                market
            )

        return (self.market, self.base_currency, self.quote_currency)

    def setLive(self, flag):
        if isinstance(flag, int) and flag in [0, 1]:
            self.is_live = flag

    def setNoSellAtLoss(self, flag):
        if isinstance(flag, int) and flag in [0, 1]:
            self.sell_at_loss = flag

    def setUseKucoinCache(self, flag):
        if isinstance(flag, int) and flag in [0, 1]:
            self.usekucoincache = flag

    def startApp(self, app, account, last_action="", banner=True):
        if (
            banner
            and not self.isSimulation()
            or (self.isSimulation() and not self.simResultOnly())
        ):
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
                        minutes=(self.getGranularity().to_integer / 60) * self.setTotalPeriods()
                    )

                elif self.simenddate is not None and self.simstartdate is None:
                    if self.simenddate == "now":
                        endDate = self.getDateFromISO8601Str(str(datetime.now()))
                    else:
                        endDate = self.getDateFromISO8601Str(self.simenddate)

                    startDate = endDate - timedelta(
                        minutes=(self.getGranularity().to_integer / 60) * self.setTotalPeriods()
                    )

                else:
                    endDate = self.getDateFromISO8601Str(
                        str(pd.Series(datetime.now()).dt.round(freq="H")[0])
                    )
                    if self.getExchange() == Exchange.COINBASEPRO:
                        endDate -= timedelta(
                            hours=random.randint(0, 8760 * 3)
                        )  # 3 years in hours
                    else:
                        endDate -= timedelta(hours=random.randint(0, 8760 * 1))

                    startDate = self.getDateFromISO8601Str(str(endDate))
                    startDate -= timedelta(
                        minutes=(self.getGranularity().to_integer / 60) * self.setTotalPeriods()
                    )

                while len(tradingData) < self.setTotalPeriods() and attempts < 10:
                    if endDate.isoformat() > datetime.now().isoformat():
                        endDate = datetime.now()
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
                            endDate.isoformat(),
                        )

                    attempts += 1

                if self.extraCandlesFound:
                    self.simstartdate = str(startDate)
                    self.simenddate = str(endDate)

                self.extraCandlesFound = True

                if len(tradingData) < self.setTotalPeriods():
                    raise Exception(
                        f"Unable to retrieve {str(self.setTotalPeriods())} random sets of data between "
                        + str(startDate)
                        + " and "
                        + str(endDate)
                        + " in 10 attempts."
                    )

                if banner:
                    text_box = TextBox(80, 26)
                    startDate = str(startDate.isoformat())
                    endDate = str(endDate.isoformat())
                    text_box.line("Sampling start", str(startDate))
                    text_box.line("Sampling end", str(endDate))
                    if self.simstartdate != None and len(tradingData) < self.setTotalPeriods():
                        text_box.center(f"WARNING: Using less than {str(self.setTotalPeriods())} intervals")
                        text_box.line("Interval size", str(len(tradingData)))
                    text_box.doubleLine()

            else:
                tradingData = pd.DataFrame()

                startDate = self.getDateFromISO8601Str(str(datetime.now()))
                startDate -= timedelta(
                    minutes=(self.getGranularity().to_integer / 60) * 2
                )
                endDate = startDate
                startDate = pd.Series(startDate).dt.round(freq="H")[0]
                endDate = pd.Series(endDate).dt.round(freq="H")[0]
                startDate -= timedelta(
                    minutes=(self.getGranularity().to_integer / 60) * self.setTotalPeriods()
                )

                if endDate.isoformat() > datetime.now().isoformat():
                    endDate = datetime.now()

                if self.smart_switch == 1:
                    tradingData = self.getSmartSwitchHistoricalDataChained(
                        self.getMarket(),
                        self.getGranularity(),
                        str(startDate),
                        str(endDate),
                    )
                else:
                    tradingData = self.getSmartSwitchDataFrame(
                        tradingData,
                        self.getMarket(),
                        self.getGranularity(),
                        self.getDateFromISO8601Str(str(startDate)).isoformat(),
                        endDate.isoformat(),
                    )

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
        text_box = TextBox(80, 26)
        text_box.singleLine()
        text_box.center("Python Crypto Bot")
        text_box.singleLine()
        text_box.line("Release", self.getVersionFromREADME())
        text_box.singleLine()

        if self.isVerbose():
            text_box.line("Market", self.getMarket())
            text_box.line("Granularity", str(self.getGranularity()) + " seconds")
            text_box.singleLine()

        if self.isLive():
            text_box.line("Bot Mode", "LIVE - live trades using your funds!")
        else:
            text_box.line("Bot Mode", "TEST - test trades using dummy funds :)")

        text_box.line("Bot Started", str(datetime.now()))
        text_box.line("Exchange", str(self.exchange.value))
        text_box.doubleLine()

        if self.sellUpperPcnt() != None:
            text_box.line(
                "Sell Upper", str(self.sellUpperPcnt()) + "%  --sellupperpcnt  <pcnt>"
            )

        if self.sellLowerPcnt() != None:
            text_box.line(
                "Sell Lower", str(self.sellLowerPcnt()) + "%  --selllowerpcnt  <pcnt>"
            )

        if self.noSellMaxPercent() != None:
            text_box.line(
                "No Sell Max",
                str(self.noSellMaxPercent()) + "%  --nosellmaxpcnt  <pcnt>",
            )

        if self.noSellMinPercent() != None:
            text_box.line(
                "No Sell Min",
                str(self.noSellMinPercent()) + "%  --nosellminpcnt  <pcnt>",
            )

        if self.trailingStopLoss() != None:
            text_box.line(
                "Trailing Stop Loss",
                str(self.trailingStopLoss()) + "%  --trailingstoploss  <pcnt>",
            )

        if self.trailingStopLossTrigger() != None:
            text_box.line(
                "Trailing Stop Loss Trg",
                str(self.trailingStopLossTrigger()) + "%  --trailingstoplosstrigger",
            )

        if self.dynamicTSL():
            text_box.line(
                "Dynamic Trailing Stop Loss",
                str(self.dynamicTSL()) + "  --dynamictsl",
            )
        if self.TSLMultiplier() != None:
            text_box.line(
                "Trailing Stop Loss Multiplier",
                str(self.TSLMultiplier()) + "%  --tslmultiplier  <pcnt>",
            )

        if self.TSLTriggerMultiplier() != None:
            text_box.line(
                "Stop Loss Trigger Multiplier",
                str(self.TSLTriggerMultiplier()) + "%  --tsltriggermultiplier  <pcnt>",
            )

        if self.TSLMaxPcnt() != None:
            text_box.line(
                "Stop Loss Maximum Percent",
                str(self.TSLMaxPcnt()) + "%  --tslmaxpcnt  <pcnt>",
            )

        if self.preventLoss():
            text_box.line(
                "Prevent Loss",
                str(self.preventLoss()) + "  --preventloss",
            )

        if self.preventLossTrigger() != None:
            text_box.line(
                "Prevent Loss Trigger",
                str(self.preventLossTrigger()) + "%  --preventlosstrigger",
            )

        if self.preventLossMargin() != None:
            text_box.line(
                "Prevent Loss Margin",
                str(self.preventLossMargin()) + "%  --preventlossmargin",
            )

        text_box.line("Sell At Loss", str(self.allowSellAtLoss()) + "  --sellatloss ")
        text_box.line(
            "Sell At Resistance", str(self.sellAtResistance()) + "  --sellatresistance"
        )
        text_box.line(
            "Trade Bull Only", str(not self.disableBullOnly()) + "  --disablebullonly"
        )
        text_box.line(
            "Allow Buy Near High",
            str(not self.disableBuyNearHigh()) + "  --disablebuynearhigh",
        )
        if self.disableBuyNearHigh():
            text_box.line(
                "No Buy Near High Pcnt",
                str(self.noBuyNearHighPcnt()) + "%  --nobuynearhighpcnt <pcnt>",
            )
        text_box.line(
            "Use Buy MACD", str(not self.disableBuyMACD()) + "  --disablebuymacd"
        )
        text_box.line(
            "Use Buy EMA", str(not self.disableBuyEMA()) + "  --disablebuyema"
        )
        text_box.line(
            "Use Buy OBV", str(not self.disableBuyOBV()) + "  --disablebuyobv"
        )
        text_box.line(
            "Use Buy Elder-Ray",
            str(not self.disableBuyElderRay()) + "  --disablebuyelderray",
        )
        text_box.line(
            "Sell Fibonacci Low",
            str(not self.disableFailsafeFibonacciLow())
            + "  --disablefailsafefibonaccilow",
        )

        if self.sellLowerPcnt() != None:
            text_box.line(
                "Sell Lower Pcnt",
                str(not self.disableFailsafeLowerPcnt())
                + "  --disablefailsafelowerpcnt",
            )

        if self.sellUpperPcnt() != None:
            text_box.line(
                "Sell Upper Pcnt",
                str(not self.disableFailsafeLowerPcnt())
                + "  --disableprofitbankupperpcnt",
            )

        text_box.line(
            "Candlestick Reversal",
            str(not self.disableProfitbankReversal()) + "  --disableprofitbankreversal",
        )
        text_box.line("Telegram", str(not self.disabletelegram) + "  --disabletelegram")

        if not self.disabletelegram:
            text_box.line(
                "Telegram trades only",
                str(self.telegramTradesOnly()) + " --telegramtradesonly",
            )

        if not self.disabletelegram:
            text_box.line(
                "Telegram error msgs",
                str(not self.disableTelegramErrorMsgs())
                + " --disabletelegramerrormsgs",
            )

        text_box.line("Enable Pandas-ta", str(self.enablePandasTA()) + "  --enable_pandas_ta")
        text_box.line("EnableCustom Strategy", str(self.enableCustomStrategy()) + "  --enable_custom_strategy")
        text_box.line("Log", str(not self.disableLog()) + "  --disablelog")
        text_box.line("Tracker", str(not self.disableTracker()) + "  --disabletracker")
        text_box.line("Auto restart Bot", str(self.autoRestart()) + "  --autorestart")
        text_box.line("Web Socket", str(self.websocket) + "  --websocket")
        text_box.line(
            "Insufficient Funds Logging",
            str(self.enableinsufficientfundslogging)
            + "  --enableinsufficientfundslogging",
        )
        text_box.line(
            "Log Buy and Sell orders in JSON",
            str(self.logbuysellinjson) + "  --logbuysellinjson",
        )

        if self.getBuyMaxSize():
            text_box.line(
                "Max Buy Size", str(self.getBuyMaxSize()) + "  --buymaxsize <size>"
            )


        if self.getBuyMinSize():
            text_box.line(
                "Min Buy Size", str(self.getBuyMinSize()) + "  --buyminsize <size>")

        if self.buyLastSellSize():
            text_box.line(
                "Buy Last Sell Size",
                str(self.buyLastSellSize()) + "  --buylastsellsize",
            )

        if self.getTrailingBuyPcnt():
            text_box.line(
                "Trailing Buy Percent", str(self.getTrailingBuyPcnt()) + "  --trailingbuypcnt <size>"
            )

        if self.trailingImmediateBuy():
            text_box.line(
                "Immediate buy for trailingbuypcnt",
                str(self.trailingImmediateBuy()) + "  --trailingImmediateBuy",
            )

        if self.getTrailingBuyImmediatePcnt():
            text_box.line(
                "Trailing Buy Immediate Percent", str(self.getTrailingBuyImmediatePcnt()) + "  --trailingbuyimmediatepcnt <size>"
            )

        if self.getTrailingSellPcnt():
            text_box.line(
                "Trailing Sell Percent", str(self.getTrailingSellPcnt()) + "  --trailingsellpcnt <size>"
            )

        if self.trailingImmediateSell():
            text_box.line(
                "Immediate sell for trailingsellpcnt",
                str(self.trailingImmediateSell()) + "  --trailingimmediatesell",
            )

        if self.getTrailingSellImmediatePcnt():
            text_box.line(
                "Trailing Sell Immediate Percent", str(self.getTrailingSellImmediatePcnt()) + "  --trailingsellimmediatepcnt <size>"
            )

        if self.getTrailingSellBailoutPcnt():
            text_box.line(
                "Trailing Sell Bailout Percent", str(self.getTrailingSellBailoutPcnt()) + "  --trailingsellbailoutpcnt <size>"
            )

        if self.sellTriggerOverride():
            text_box.line(
                "Override SellTrigger if STRONG buy",
                str(self.sellTriggerOverride()) + "  --trailingImmediateSell",
            )

        if self.marketMultiBuyCheck():
            text_box.line(
                "Check for Market Multiple Buys",
                str(self.marketMultiBuyCheck()) + "  --marketmultibuycheck",
            )

        if self.setTotalPeriods() != None:
            text_box.line(
                "Adjust Total Periods for Market ",
                str(self.setTotalPeriods()) + " --adjust_total_periods  <size>",
            )

        if self.manualTradesOnly():
            text_box.line(
                "Manual Trading Only (HODL)",
                str(self.manualTradesOnly()) + "  --manual_trades_only",
            )

        if self.disablebuyema and self.disablebuymacd and self.enableCustomStrategy() is False:
            text_box.center(
                "WARNING : EMA and MACD indicators disabled, no buy events will happen"
            )

        text_box.doubleLine()
