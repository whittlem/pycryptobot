import pandas as pd
import argparse
import json
import math
import random
import re
import sys
import urllib3
from datetime import datetime, timedelta
from typing import Union
from urllib3.exceptions import ReadTimeoutError
from models.Trading import TechnicalAnalysis
from models.exchange.binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import AuthAPI as CBAuthAPI, PublicAPI as CBPublicAPI
from models.chat import Telegram
from models.config import binanceConfigParser, binanceParseMarket, coinbaseProConfigParser, coinbaseProParseMarket, dummyConfigParser, dummyParseMarket, loggerConfigParser
from models.ConfigBuilder import ConfigBuilder
from models.helper.LogHelper import Logger

# disable insecure ssl warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def parse_arguments():
    # instantiate the arguments parser
    parser = argparse.ArgumentParser(description='Python Crypto Bot using the Coinbase Pro or Binanace API')

    # config builder
    parser.add_argument('--init', action="store_true", help="config.json configuration builder")

    # optional arguments
    parser.add_argument('--exchange', type=str, help="'coinbasepro', 'binance', 'dummy'")
    parser.add_argument('--granularity', type=str, help="coinbasepro: (60,300,900,3600,21600,86400), binance: (1m,5m,15m,1h,6h,1d)")
    parser.add_argument('--graphs', type=int, help='save graphs=1, do not save graphs=0')
    parser.add_argument('--live', type=int, help='live=1, test=0')
    parser.add_argument('--market', type=str, help='coinbasepro: BTC-GBP, binance: BTCGBP etc.')
    parser.add_argument('--sellatloss', type=int, help='toggle if bot should sell at a loss')
    parser.add_argument('--sellupperpcnt', type=float, help='optionally set sell upper percent limit')
    parser.add_argument('--selllowerpcnt', type=float, help='optionally set sell lower percent limit')
    parser.add_argument('--trailingstoploss', type=float, help='optionally set a trailing stop percent loss below last buy high')
    parser.add_argument('--sim', type=str, help='simulation modes: fast, fast-sample, slow-sample')
    parser.add_argument('--simstartdate', type=str, help="start date for sample simulation e.g '2021-01-15'")
    parser.add_argument('--simenddate', type=str, help="end date for sample simulation e.g '2021-01-15' or 'now'")
    parser.add_argument('--smartswitch', type=int, help='optionally smart switch between 1 hour and 15 minute intervals')
    parser.add_argument('--verbose', type=int, help='verbose output=1, minimal output=0')
    parser.add_argument('--config', type=str, help="Use the config file at the given location. e.g 'myconfig.json'")
    parser.add_argument('--logfile', type=str, help="Use the log file at the given location. e.g 'mymarket.log'")
    parser.add_argument('--buypercent', type=int, help="percentage of quote currency to buy")
    parser.add_argument('--sellpercent', type=int, help="percentage of base currency to sell")
    parser.add_argument('--lastaction', type=str, help="optionally set the last action (BUY, SELL)")
    parser.add_argument('--buymaxsize', type=float, help="maximum size on buy")

    # optional options
    parser.add_argument('--sellatresistance', action="store_true", help="sell at resistance or upper fibonacci band")
    parser.add_argument('--autorestart', action="store_true", help="Auto restart the bot in case of exception")

    # disable defaults
    parser.add_argument('--disablebullonly', action="store_true", help="disable only buying in bull market")
    parser.add_argument('--disablebuynearhigh', action="store_true", help="disable buy within 5 percent of high")
    parser.add_argument('--disablebuymacd', action="store_true", help="disable macd buy signal")
    parser.add_argument('--disablebuyobv', action="store_true", help="disable obv buy signal")
    parser.add_argument('--disablebuyelderray', action="store_true", help="disable elder ray buy signal")
    parser.add_argument('--disablefailsafefibonaccilow', action="store_true", help="disable failsafe sell on fibonacci lower band")
    parser.add_argument('--disablefailsafelowerpcnt', action="store_true", help="disable failsafe sell on 'selllowerpcnt'")
    parser.add_argument('--disableprofitbankupperpcnt', action="store_true", help="disable profit bank on 'sellupperpcnt'")
    parser.add_argument('--disableprofitbankreversal', action="store_true", help="disable profit bank on strong candlestick reversal")
    parser.add_argument('--disabletelegram', action="store_true", help="disable telegram messages")
    parser.add_argument('--disablelog', action="store_true", help="disable pycryptobot.log")
    parser.add_argument('--disabletracker', action="store_true", help="disable tracker.csv")

    # parse arguments

    # pylint: disable=unused-variable
    args, unknown = parser.parse_known_args()
    return vars(args)


def to_coinbase_pro_granularity(granularity: int) -> int:
    return granularity


def to_binance_granularity(granularity: int) -> str:
    return {60: '1m', 300: '5m', 900: '15m', 3600: '1h', 21600: '6h', 86400: '1d'}[granularity]


#  pylint: disable=unsubscriptable-object
def truncate(f: Union[int, float], n: Union[int, float]) -> str:
    """
    Format a given number ``f`` with a given precision ``n``.
    """

    if not isinstance(f, int) and not isinstance(f, float):
        return '0.0'

    if not isinstance(n, int) and not isinstance(n, float):
        return '0.0'

    if (f < 0.001) and n >= 4:
        return f'{f:.4f}'

    # `{n}` inside the actual format honors the precision
    return f'{math.floor(f * 10 ** n) / 10 ** n:.{n}f}'


class PyCryptoBot():
    def __init__(self, exchange='coinbasepro', filename='config.json'):
        args = parse_arguments()

        self.api_key = ''
        self.api_secret = ''
        self.api_passphrase = ''
        self.api_url = ''

        if args['config'] is not None:
            filename = args['config']
        if args['exchange'] is not None:
            if args['exchange'] not in ['coinbasepro', 'binance', 'dummy']:
                raise TypeError('Invalid exchange: coinbasepro, binance')
            else:
                self.exchange = args['exchange']
        else:
            self.exchange = exchange

        self.market = 'BTC-GBP'
        self.base_currency = 'BTC'
        self.quote_currency = 'GBP'
        self.granularity = 3600
        self.is_live = 0
        self.is_verbose = 0
        self.save_graphs = 0
        self.is_sim = 0
        self.simstartdate = None
        self.simenddate = None
        self.sim_speed = 'fast'
        self.sell_upper_pcnt = None
        self.sell_lower_pcnt = None
        self.trailing_stop_loss = None
        self.sell_at_loss = 1
        self.smart_switch = 1
        self.telegram = False
        self.buypercent = 100
        self.sellpercent = 100
        self.last_action = None
        self._chat_client = None
        self.buymaxsize = None

        self.configbuilder = False

        self.sellatresistance = False
        self.autorestart = False

        self.disablebullonly = False
        self.disablebuynearhigh = False
        self.disablebuymacd = False
        self.disablebuyobv = False
        self.disablebuyelderray = False
        self.disablefailsafefibonaccilow = False
        self.disablefailsafelowerpcnt = False
        self.disableprofitbankupperpcnt = False
        self.disableprofitbankreversal = False
        self.disabletelegram = False
        self.disablelog = False
        self.disabletracker = False

        self.filelog = True
        self.logfile = args['logfile'] if args['logfile'] else 'pycryptobot.log'
        self.fileloglevel = 'DEBUG'
        self.consolelog = True
        self.consoleloglevel = 'INFO'

        self.ema1226_1h_cache = None
        self.ema1226_6h_cache = None
        self.sma50200_1h_cache = None

        if args['init']:
            # config builder
            cb = ConfigBuilder()
            cb.init()
            sys.exit()

        try:
            with open(filename) as config_file:
                config = json.load(config_file)

                if exchange not in config and 'binance' in config:
                    self.exchange = 'binance'

                if self.exchange == 'coinbasepro' and 'coinbasepro' in config:
                    coinbaseProConfigParser(self, config['coinbasepro'], args)

                elif self.exchange == 'binance' and 'binance' in config:
                    binanceConfigParser(self, config['binance'], args)

                elif self.exchange == 'dummy' and 'dummy' in config:
                    dummyConfigParser(self, config['dummy'], args)

                if not self.disabletelegram and 'telegram' in config and 'token' in config['telegram'] and 'client_id' in config['telegram']:
                    telegram = config['telegram']
                    self._chat_client = Telegram(telegram['token'], telegram['client_id'])
                    self.telegram = True

                if 'logger' in config:
                    loggerConfigParser(self, config['logger'])
                
                if self.disablelog:
                    self.filelog = 0
                    self.fileloglevel = 'NOTSET'
                    self.logfile == "pycryptobot.log"

                Logger.configure(filelog=self.filelog, logfile=self.logfile, fileloglevel=self.fileloglevel, consolelog=self.consolelog, consoleloglevel=self.consoleloglevel)     

        except json.decoder.JSONDecodeError as err:
            sys.tracebacklimit = 0
            raise ValueError('Invalid config.json: ' + str(err))

        except IOError as err:
            sys.tracebacklimit = 0
            raise ValueError('Invalid config.json: ' + str(err))

        except ValueError as err:
            sys.tracebacklimit = 0
            raise ValueError('Invalid config.json: ' + str(err))

    def _isCurrencyValid(self, currency):
        if self.exchange == 'coinbasepro' or self.exchange == 'binance':
            p = re.compile(r"^[1-9A-Z]{2,5}$")
            return p.match(currency)

        return False

    def _isMarketValid(self, market):
        if self.exchange == 'coinbasepro':
            p = re.compile(r"^[1-9A-Z]{2,5}\-[1-9A-Z]{2,5}$")
            return p.match(market)
        elif self.exchange == 'binance':
            p = re.compile(r"^[A-Z0-9]{6,12}$")
            return p.match(market)

        return False

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

    def getVersionFromREADME(self) -> str:
        try:
            count = 0
            with open('README.md', 'r', encoding='utf8') as reader:
                line = reader.readline()
                while count < 5:
                    line = reader.readline()

                    if '# Python Crypto Bot' in line:
                        line = line.replace('# Python Crypto Bot ', '')
                        line = line.replace(' (pycryptobot)', '')
                        return line.strip()

                    count = count + 1

            return 'v0.0.0'
        except Exception:
            return 'v0.0.0'

    def printGranularity(self) -> str:
        if self.exchange == 'binance':
            return to_binance_granularity(self.granularity)
        if self.exchange == 'coinbasepro':
            return str(self.granularity)
        if self.exchange == 'dummy':
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

    def getHistoricalData(self, market, granularity: int, iso8601start='', iso8601end=''):
        if self.exchange == 'coinbasepro':
            api = CBPublicAPI()

            if iso8601start != '' and iso8601end == '':
                return api.getHistoricalData(market, to_coinbase_pro_granularity(granularity), iso8601start)
            elif iso8601start != '' and iso8601end != '':
                return api.getHistoricalData(market, to_coinbase_pro_granularity(granularity), iso8601start, iso8601end)
            else:
                return api.getHistoricalData(market, to_coinbase_pro_granularity(granularity))

        elif self.exchange == 'binance':
            api = BPublicAPI()

            if iso8601start != '' and iso8601end != '':
                return api.getHistoricalData(
                    market,
                    to_binance_granularity(granularity),
                    str(datetime.strptime(iso8601start, '%Y-%m-%dT%H:%M:%S.%f').strftime('%d %b, %Y')),
                    str(datetime.strptime(iso8601end, '%Y-%m-%dT%H:%M:%S.%f').strftime('%d %b, %Y'))
                )
            else:
                return api.getHistoricalData(market, to_binance_granularity(granularity))
        else:
            return pd.DataFrame()

    def getHistoricalDataChained(self, market, granularity: int, max_interations: int=1) -> pd.DataFrame:
        df1 = self.getHistoricalData(market, self.getGranularity())

        if max_interations == 1:
            return df1

        def getPreviousDateRange(df: pd.DataFrame=None) -> tuple:
            end_date = df['date'].min() - timedelta(seconds=(granularity / 60))
            new_start = df['date'].min() - timedelta(hours=300)
            return (str(new_start).replace(' ', 'T'), str(end_date).replace(' ', 'T'))

        iterations = 0
        result_df = pd.DataFrame()
        while iterations < (max_interations - 1):
            start_date, end_date = getPreviousDateRange(df1)
            df2 = self.getHistoricalData(market, granularity, start_date, end_date)
            result_df = pd.concat([df2, df1]).drop_duplicates()
            df1 = result_df
            iterations = iterations + 1

        if 'date'in result_df:
            result_df.sort_values(by=['date'], ascending=True, inplace=True)
        
        return result_df

    def getSmartSwitch(self):
        return self.smart_switch

    def is1hEMA1226Bull(self):
        try:
            if self.isSimulation() and isinstance(self.ema1226_1h_cache, pd.DataFrame):
                df_data = self.ema1226_1h_cache
            elif self.exchange == 'coinbasepro':
                api = CBPublicAPI()
                df_data = api.getHistoricalData(self.market, 3600)
                self.ema1226_1h_cache = df_data
            elif self.exchange == 'binance':
                api = BPublicAPI()
                df_data = api.getHistoricalData(self.market, '1h')
                self.ema1226_1h_cache = df_data
            else:
                return False

            ta = TechnicalAnalysis(df_data)

            if 'ema12' not in df_data:
                ta.addEMA(12)

            if 'ema26' not in df_data:
                ta.addEMA(26)
            
            df_last = ta.getDataFrame().copy().iloc[-1,:]
            df_last['bull'] = df_last['ema12'] > df_last['ema26']
            return bool(df_last['bull'])
        except Exception:
            return False

    def is1hSMA50200Bull(self):
        try:
            if self.isSimulation() and isinstance(self.sma50200_1h_cache, pd.DataFrame):
                df_data = self.sma50200_1h_cache
            if self.exchange == 'coinbasepro':
                api = CBPublicAPI()
                df_data = api.getHistoricalData(self.market, 3600)
                self.sma50200_1h_cache = df_data
            elif self.exchange == 'binance':
                api = BPublicAPI()
                df_data = api.getHistoricalData(self.market, '1h')
                self.sma50200_1h_cache = df_data
            else:
                return False

            ta = TechnicalAnalysis(df_data)
            
            if 'sma50' not in df_data:
                ta.addSMA(50)
            
            if 'sma200' not in df_data:
                ta.addSMA(200)

            df_last = ta.getDataFrame().copy().iloc[-1,:]
            df_last['bull'] = df_last['sma50'] > df_last['sma200']
            return bool(df_last['bull'])
        except Exception:
            return False

    def isCryptoRecession(self):
        try:
            if self.exchange == 'coinbasepro':
                api = CBPublicAPI()
                df_data = api.getHistoricalData(self.market, 86400)
            elif self.exchange == 'binance':
                api = BPublicAPI()
                df_data = api.getHistoricalData(self.market, '1d')
            else:
                return False  # if there is an API issue, default to False to avoid hard sells

            if len(df_data) <= 200:
                return False  # if there is insufficient data, default to False to avoid hard sells

            ta = TechnicalAnalysis(df_data)
            ta.addSMA(50)
            ta.addSMA(200)
            df_last = ta.getDataFrame().copy().iloc[-1, :]
            df_last['crypto_recession'] = df_last['sma50'] < df_last['sma200']

            return bool(df_last['crypto_recession'])
        except Exception:
            return False

    def is6hEMA1226Bull(self):
        try:
            if isinstance(self.ema1226_6h_cache, pd.DataFrame):
                df_data = self.ema1226_6h_cache
            elif self.exchange == 'coinbasepro':
                api = CBPublicAPI()
                df_data = api.getHistoricalData(self.market, 21600)
                self.ema1226_6h_cache = df_data
            elif self.exchange == 'binance':
                api = BPublicAPI()
                df_data = api.getHistoricalData
                self.ema1226_6h_cache = df_data(self.market, '6h')
            else:
                return False

            ta = TechnicalAnalysis(df_data)

            if 'ema12' not in df_data:
                ta.addEMA(12)

            if 'ema26' not in df_data:
                ta.addEMA(26)

            df_last = ta.getDataFrame().copy().iloc[-1, :]
            df_last['bull'] = df_last['ema12'] > df_last['ema26']
            return bool(df_last['bull'])
        except Exception:
            return False

    def is6hSMA50200Bull(self):
        try:
            if self.exchange == 'coinbasepro':
                api = CBPublicAPI()
                df_data = api.getHistoricalData(self.market, 21600)
            elif self.exchange == 'binance':
                api = BPublicAPI()
                df_data = api.getHistoricalData(self.market, '6h')
            else:
                return False

            ta = TechnicalAnalysis(df_data)
            ta.addSMA(50)
            ta.addSMA(200)
            df_last = ta.getDataFrame().copy().iloc[-1, :]
            df_last['bull'] = df_last['sma50'] > df_last['sma200']
            return bool(df_last['bull'])
        except Exception:
            return False

    def getTicker(self, market):
        if self.exchange == 'coinbasepro':
            api = CBPublicAPI()
            return api.getTicker(market)
        elif self.exchange == 'binance':
            api = BPublicAPI()
            return api.getTicker(market)
        else:
            return None

    def getTime(self):
        if self.exchange == 'coinbasepro':
            return CBPublicAPI().getTime()
        elif self.exchange == 'binance':
            try:
                return BPublicAPI().getTime()
            except ReadTimeoutError:
                return ''
        else:
            return ''

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

    def trailingStopLoss(self):
        return self.trailing_stop_loss

    def allowSellAtLoss(self) -> bool:
        return self.sell_at_loss == 1

    def showConfigBuilder(self) -> bool:
        return self.configbuilder

    def sellAtResistance(self) -> bool:
        return self.sellatresistance

    def autoRestart(self) -> bool:
        return self.autorestart

    def getLastAction(self):
        return self.last_action

    def disableBullOnly(self) -> bool:
        return self.disablebullonly

    def disableBuyNearHigh(self) -> bool:
        return self.disablebuynearhigh

    def disableBuyMACD(self) -> bool:
        return self.disablebuymacd

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


    def compare(self, val1, val2, label='', precision=2):
        if val1 > val2:
            if label == '':
                return truncate(val1, precision) + ' > ' + truncate(val2, precision)
            else:
                return label + ': ' + truncate(val1, precision) + ' > ' + truncate(val2, precision)
        if val1 < val2:
            if label == '':
                return truncate(val1, precision) + ' < ' + truncate(val2, precision)
            else:
                return label + ': ' + truncate(val1, precision) + ' < ' + truncate(val2, precision)
        else:
            if label == '':
                return truncate(val1, precision) + ' = ' + truncate(val2, precision)
            else:
                return label + ': ' + truncate(val1, precision) + ' = ' + truncate(val2, precision)

    def getLastBuy(self) -> dict:
        """Retrieves the last exchange buy order and returns a dictionary"""

        try:
            if self.exchange == 'coinbasepro':
                api = CBAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIPassphrase(), self.getAPIURL())
                orders = api.getOrders(self.getMarket(), '', 'done')

                if len(orders) == 0:
                    return None

                last_order = orders.tail(1)
                if last_order['action'].values[0] != 'buy':
                    return None

                return {
                    'side' : 'buy',
                    'market' : self.getMarket(),
                    'size' : float(last_order['size']),
                    'filled' : float(last_order['filled']),
                    'price' : float(last_order['price']),
                    'fee' : float(last_order['fees']),
                    'date' : str(pd.DatetimeIndex(pd.to_datetime(last_order['created_at']).dt.strftime('%Y-%m-%dT%H:%M:%S.%Z'))[0])
                }
            elif self.exchange == 'binance':
                api = BAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIURL())
                orders = api.getOrders(self.getMarket())

                if len(orders) == 0:
                    return None

                last_order = orders.tail(1)
                if last_order['action'].values[0] != 'buy':
                    return None

                return {
                    'side' : 'buy',
                    'market' : self.getMarket(),
                    'size' : float(last_order['size']),
                    'filled' : float(last_order['filled']),
                    'price' : float(last_order['price']),
                    'fees' : float(last_order['size'] * 0.001),
                    'date' : str(pd.DatetimeIndex(pd.to_datetime(last_order['created_at']).dt.strftime('%Y-%m-%dT%H:%M:%S.%Z'))[0])
                }
            else:
                return None
        except Exception:
            return None

    def getTakerFee(self):
        if self.isSimulation() is True and self.exchange == 'coinbasepro':
            return 0.005 # default lowest fee tier
        elif self.isSimulation() is True and self.exchange == 'binance':
            return 0.001 # default lowest fee tier
        elif self.exchange == 'coinbasepro':
            api = CBAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIPassphrase(), self.getAPIURL())
            return api.getTakerFee()
        elif self.exchange == 'binance':
            api = BAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIURL())
            return api.getTakerFee()
        else:
            return 0.005

    def getMakerFee(self):
        if self.exchange == 'coinbasepro':
            api = CBAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIPassphrase(), self.getAPIURL())
            return api.getMakerFee()
        elif self.exchange == 'binance':
            api = BAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIURL())
            # return api.getMakerFee()
            return 0.005
        else:
            return 0.005

    def marketBuy(self, market, quote_currency, buy_percent=100):
        if self.is_live == 1:
            if isinstance(buy_percent, int):
                if buy_percent > 0 and buy_percent < 100:
                    quote_currency = (buy_percent / 100) * quote_currency

            if self.exchange == 'coinbasepro':
                api = CBAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIPassphrase(), self.getAPIURL())
                return api.marketBuy(market, float(truncate(quote_currency, 2)))
            elif self.exchange == 'binance':
                api = BAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIURL())
                return api.marketBuy(market, quote_currency)
            else:
                return None

    def marketSell(self, market, base_currency, sell_percent=100):
        if self.is_live == 1:
            if isinstance(sell_percent, int):
                if sell_percent > 0 and sell_percent < 100:
                    base_currency = (sell_percent / 100) * base_currency
                if self.exchange == 'coinbasepro':
                    api = CBAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIPassphrase(), self.getAPIURL())
                    return api.marketSell(market, base_currency)
                elif self.exchange == 'binance':
                    api = BAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIURL())
                    return api.marketSell(market, base_currency)
            else:
                return None

    def setMarket(self, market):
        if self.exchange == 'binance':
            self.market, self.base_currency, self.quote_currency = binanceParseMarket(market)

        elif self.exchange == 'coinbasepro':
            self.market, self.base_currency, self.quote_currency = coinbaseProParseMarket(market)

        return (self.market, self.base_currency, self.quote_currency)

    def setLive(self, flag):
        if isinstance(flag, int) and flag in [0, 1]:
            self.is_live = flag

    def setNoSellAtLoss(self, flag):
        if isinstance(flag, int) and flag in [0, 1]:
            self.sell_at_loss = flag

    def startApp(self, account, last_action='', banner=True):
        if banner:
            Logger.info('--------------------------------------------------------------------------------')
            Logger.info('|                             Python Crypto Bot                                |')
            Logger.info('--------------------------------------------------------------------------------')
            txt = '              Release : ' + self.getVersionFromREADME()
            Logger.info('|  ' +  txt + (' ' * (75 - len(txt))) + ' | ')

            Logger.info('-----------------------------------------------------------------------------')

            if self.isVerbose():
                txt = '               Market : ' + self.getMarket()
                Logger.info('|  ' +  txt + (' ' * (75 - len(txt))) + ' | ')
                txt = '          Granularity : ' + str(self.getGranularity()) + ' seconds'
                Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')
                Logger.info('-----------------------------------------------------------------------------')

            if self.isLive():
                txt = '             Bot Mode : LIVE - live trades using your funds!'
            else:
                txt = '             Bot Mode : TEST - test trades using dummy funds :)'

            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '          Bot Started : ' + str(datetime.now())
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')
            Logger.info('================================================================================')

            if self.sellUpperPcnt() != None:
                txt = '           Sell Upper : ' + str(self.sellUpperPcnt()) + '%'
                Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            if self.sellLowerPcnt() != None:
                txt = '           Sell Lower : ' + str(self.sellLowerPcnt()) + '%'
                Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            if self.trailingStopLoss() != None:
                txt = '   Trailing Stop Loss : ' + str(self.trailingStopLoss()) + '%'
                Logger.info(' | ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '         Sell At Loss : ' + str(self.allowSellAtLoss()) + '  --sellatloss ' + str(self.allowSellAtLoss())
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '   Sell At Resistance : ' + str(self.sellAtResistance()) + '  --sellatresistance'
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '      Trade Bull Only : ' + str(not self.disableBullOnly()) + '  --disablebullonly'
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '        Buy Near High : ' + str(not self.disableBuyNearHigh()) + '  --disablebuynearhigh'
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '         Use Buy MACD : ' + str(not self.disableBuyMACD()) + '  --disablebuymacd'
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '          Use Buy OBV : ' + str(not self.disableBuyOBV()) + '  --disablebuyobv'
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '    Use Buy Elder-Ray : ' + str(not self.disableBuyElderRay()) + '  --disablebuyelderray'
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '   Sell Fibonacci Low : ' + str(
                not self.disableFailsafeFibonacciLow()) + '  --disablefailsafefibonaccilow'
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            if self.sellLowerPcnt() != None:
                txt = '      Sell Lower Pcnt : ' + str(
                    not self.disableFailsafeLowerPcnt()) + '  --disablefailsafelowerpcnt'
                Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            if self.sellUpperPcnt() != None:
                txt = '      Sell Upper Pcnt : ' + str(
                    not self.disableFailsafeLowerPcnt()) + '  --disableprofitbankupperpcnt'
                Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = ' Candlestick Reversal : ' + str(
                not self.disableProfitbankReversal()) + '  --disableprofitbankreversal'
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '             Telegram : ' + str(not self.disabletelegram) + '  --disabletelegram'
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '                  Log : ' + str(not self.disableLog()) + '  --disablelog'
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '              Tracker : ' + str(not self.disableTracker()) + '  --disabletracker'
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            txt = '     Auto restart Bot : ' + str(self.autoRestart()) + '  --autorestart'
            Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            if self.getBuyMaxSize():
                txt = '         Max Buy Size : ' + str(self.getBuyMaxSize()) + '  --buymaxsize <size>'
                Logger.info('|  ' + txt + (' ' * (75 - len(txt))) + ' | ')

            Logger.info('================================================================================')

        # run the first job immediately after starting
        if self.isSimulation():
            if self.simuluationSpeed() in ['fast-sample', 'slow-sample']:
                tradingData = pd.DataFrame()

                attempts = 0

                if self.simstartdate is not None:
                    date = self.simstartdate.split('-')
                    startDate = datetime(int(date[0]), int(date[1]), int(date[2]))
                    endDate = startDate + timedelta(minutes=(self.getGranularity()/60)*300)
                    while len(tradingData) != 300 and attempts < 10:
                        tradingData = self.getHistoricalData(self.getMarket(), self.getGranularity(),
                                                             startDate.isoformat(timespec='milliseconds'))
                        attempts += 1
                elif self.simenddate is not None:
                    if self.simenddate == 'now':
                        endDate = datetime.now()
                    else:
                        date = self.simenddate.split('-')
                        endDate = datetime(int(date[0]), int(date[1]), int(date[2]))
                    startDate = endDate - timedelta(minutes=(self.getGranularity()/60)*300)
                    while len(tradingData) != 300 and attempts < 10:
                        tradingData = self.getHistoricalData(self.getMarket(), self.getGranularity(),
                                                             startDate.isoformat(timespec='milliseconds'))
                        attempts += 1
                else:
                    while len(tradingData) != 300 and attempts < 10:
                        endDate = datetime.now() - timedelta(hours=random.randint(0, 8760 * 3))  # 3 years in hours
                        startDate = endDate - timedelta(minutes=(self.getGranularity()/60)*300)
                        tradingData = self.getHistoricalData(self.getMarket(), self.getGranularity(),
                                                             startDate.isoformat(timespec='milliseconds'))
                        attempts += 1
                    if len(tradingData) != 300:
                        raise Exception(
                            'Unable to retrieve 300 random sets of data between ' + str(startDate) + ' and ' + str(
                                endDate) + ' in ' + str(attempts) + ' attempts.')

                if banner:
                    startDate = str(startDate.isoformat())
                    endDate = str(endDate.isoformat())
                    txt = '   Sampling start : ' + str(startDate)
                    Logger.info(' | ' + txt + (' ' * (75 - len(txt))) + ' | ')
                    txt = '     Sampling end : ' + str(endDate)
                    Logger.info(' | ' + txt + (' ' * (75 - len(txt))) + ' | ')
                    if self.simstartdate != None:
                        txt = '    WARNING: Using less than 300 intervals'
                        Logger.info(' | ' + txt + (' ' * (75 - len(txt))) + ' | ')
                        txt = '    Interval size : ' + str(len(tradingData))
                        Logger.info(' | ' + txt + (' ' * (75 - len(txt))) + ' | ')
                    Logger.info('================================================================================')

            else:
                tradingData = self.getHistoricalData(self.getMarket(), self.getGranularity())

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
