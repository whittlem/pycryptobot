import pandas as pd
import argparse
import json
import logging
import math
import random
import re
import sys
import urllib3
from datetime import datetime, timedelta
from urllib3.exceptions import ReadTimeoutError
from models.Trading import TechnicalAnalysis
from models.exchange.binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import AuthAPI as CBAuthAPI, PublicAPI as CBPublicAPI
from models.Github import Github
from models.chat import Telegram
from models.config import binanceConfigParser, binanceParseMarket, coinbaseProConfigParser, coinbaseProParseMarket

# disable insecure ssl warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# reduce informational logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# instantiate the arguments parser
parser = argparse.ArgumentParser(description='Python Crypto Bot using the Coinbase Pro or Binanace API')

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
parser.add_argument('--smartswitch', type=int, help='optionally smart switch between 1 hour and 15 minute intervals')
parser.add_argument('--verbose', type=int, help='verbose output=1, minimal output=0')
parser.add_argument('--config', type=str, help="Use the config file at the given location. e.g 'myconfig.json'")
parser.add_argument('--logfile', type=str, help="Use the log file at the given location. e.g 'mymarket.log'")
parser.add_argument('--buypercent', type=int, help="percentage of quote currency to buy")
parser.add_argument('--sellpercent', type=int, help="percentage of base currency to sell")
parser.add_argument('--lastaction', type=str, help="optionally set the last action (BUY, SELL)")

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
#args = parser.parse_args()
args = vars(parser.parse_args())

class PyCryptoBot():
    def __init__(self, exchange='coinbasepro', filename='config.json'):
        self.api_key = ''
        self.api_secret = ''
        self.api_passphrase = ''
        self.api_url = ''

        if args['config'] is not None:
            filename = args['config']
        if args['exchange'] is not None:
            if args['exchange'] not in [ 'coinbasepro', 'binance', 'dummy' ]:
                raise TypeError('Invalid exchange: coinbasepro, binance')
            else:
                self.exchange = args['exchange']
        else:
            self.exchange = exchange

        self.market = 'BTC-GBP'
        self.base_currency = 'BTC'
        self.quote_currency = 'GBP'
        self.granularity = None
        self.is_live = 0
        self.is_verbose = 0
        self.save_graphs = 0
        self.is_sim = 0
        self.simstartdate = None
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

        self.logfile = args['logfile'] if args['logfile'] else "pycryptobot.log"

        try:
            with open(filename) as config_file:
                config = json.load(config_file)

                if exchange not in config and 'binance' in config:
                    self.exchange = 'binance'

                if self.exchange == 'coinbasepro' and 'coinbasepro' in config:
                    coinbaseProConfigParser(self, config['coinbasepro'], args)

                elif self.exchange == 'binance' and 'binance' in config:
                    binanceConfigParser(self, config['binance'], args)

                if not self.disabletelegram and 'telegram' in config and 'token' in config['telegram'] and 'client_id' in config['telegram']:
                    telegram = config['telegram']

                    self._chat_client = Telegram(telegram['token'], telegram['client_id'])
                    self.telegram = True

        except json.decoder.JSONDecodeError as err:
            sys.tracebacklimit = 0
            print ('Invalid config.json: ' + str(err) + "\n")
            sys.exit()

        except IOError as err:
            sys.tracebacklimit = 0
            print ('Invalid config.json: ' + str(err) + "\n")
            sys.exit()

        except ValueError as err:
            sys.tracebacklimit = 0
            print ('Invalid config.json: ' + str(err) + "\n")
            sys.exit()

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

    def getGranularity(self):
        if self.exchange == 'binance':
            return str(self.granularity)
        elif self.exchange == 'coinbasepro':
            return int(self.granularity)

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

    def getHistoricalData(self, market, granularity, iso8601start='', iso8601end=''):
        if self.exchange == 'coinbasepro':
            api = CBPublicAPI()
            return api.getHistoricalData(market, granularity, iso8601start, iso8601end)
        elif self.exchange == 'binance':
            api = BPublicAPI()

            if iso8601start != '' and iso8601end != '':
                return api.getHistoricalData(market, granularity, str(datetime.strptime(iso8601start, '%Y-%m-%dT%H:%M:%S.%f').strftime('%d %b, %Y')), str(datetime.strptime(iso8601end, '%Y-%m-%dT%H:%M:%S.%f').strftime('%d %b, %Y')))
            else:
                return api.getHistoricalData(market, granularity)
        else:
            return pd.DataFrame()

    def getSmartSwitch(self):
        return self.smart_switch

    def is1hEMA1226Bull(self):
        try:
            if self.exchange == 'coinbasepro':
                api = CBPublicAPI()
                df_data = api.getHistoricalData(self.market, 3600)
            elif self.exchange == 'binance':
                api = BPublicAPI()
                df_data = api.getHistoricalData(self.market, '1h')
            else:
                return False

            ta = TechnicalAnalysis(df_data)
            ta.addEMA(12)
            ta.addEMA(26)
            df_last = ta.getDataFrame().copy().iloc[-1,:]
            df_last['bull'] = df_last['ema12'] > df_last['ema26']
            return bool(df_last['bull'])
        except Exception:
            return False

    def is1hSMA50200Bull(self):
        try:
            if self.exchange == 'coinbasepro':
                api = CBPublicAPI()
                df_data = api.getHistoricalData(self.market, 3600)
            elif self.exchange == 'binance':
                api = BPublicAPI()
                df_data = api.getHistoricalData(self.market, '1h')
            else:
                return False

            ta = TechnicalAnalysis(df_data)
            ta.addSMA(50)
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
                return False # if there is an API issue, default to False to avoid hard sells

            if len(df_data) <= 200:
                return False # if there is unsufficient data, default to False to avoid hard sells

            ta = TechnicalAnalysis(df_data)
            ta.addSMA(50)
            ta.addSMA(200)
            df_last = ta.getDataFrame().copy().iloc[-1,:]
            df_last['crypto_recession'] = df_last['sma50'] < df_last['sma200']

            return bool(df_last['crypto_recession'])
        except Exception:
            return False

    def is6hEMA1226Bull(self):
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
            ta.addEMA(12)
            ta.addEMA(26)
            df_last = ta.getDataFrame().copy().iloc[-1,:]
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
            df_last = ta.getDataFrame().copy().iloc[-1,:]
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

    def isLive(self):
        return self.is_live

    def isVerbose(self):
        return self.is_verbose

    def shouldSaveGraphs(self):
        return self.save_graphs

    def isSimulation(self):
        return self.is_sim

    def isTelegramEnabled(self):
        return self.telegram

    def simuluationSpeed(self):
        return self.sim_speed

    def sellUpperPcnt(self):
        return self.sell_upper_pcnt

    def sellLowerPcnt(self):
        return self.sell_lower_pcnt

    def trailingStopLoss(self):
        return self.trailing_stop_loss

    def allowSellAtLoss(self):
        return self.sell_at_loss

    def sellAtResistance(self):
        return self.sellatresistance

    def autoRestart(self):
        return self.autorestart

    def getLastAction(self):
        return self.last_action

    def disableBullOnly(self):
        return self.disablebullonly

    def disableBuyNearHigh(self):
        return self.disablebuynearhigh

    def disableBuyMACD(self):
        return self.disablebuymacd

    def disableBuyOBV(self):
        return self.disablebuyobv

    def disableBuyElderRay(self):
        return self.disablebuyelderray

    def disableFailsafeFibonacciLow(self):
        return self.disablefailsafefibonaccilow

    def disableFailsafeLowerPcnt(self):
        return self.disablefailsafelowerpcnt
    
    def disableProfitbankUpperPcnt(self):
        return self.disableprofitbankupperpcnt

    def disableProfitbankReversal(self):
        return self.disableprofitbankreversal

    def disableTelegram(self):
        return self.disabletelegram

    def disableLog(self):
        return self.disablelog

    def disableTracker(self):
        return self.disabletracker

    def setGranularity(self, granularity):
        if self.exchange == 'binance' and isinstance(granularity, str) and granularity in [ '1m', '5m', '15m', '1h', '6h', '1d' ]:
            self.granularity = granularity
        elif self.exchange == 'coinbasepro' and isinstance(granularity, int) and granularity in [ 60, 300, 900, 3600, 21600, 86400 ]:
            self.granularity = granularity

    def truncate(self, f, n):
        if not isinstance(f, int) and not isinstance(f, float):
            return 0.0

        if not isinstance(n, int) and not isinstance(n, float):
            return 0.0

        if (f < 0.001) and n >= 4:
            return '{:.4f}'.format(f)

        return math.floor(f * 10 ** n) / 10 ** n

    def compare(self, val1, val2, label='', precision=2):
        if val1 > val2:
            if label == '':
                return str(self.truncate(val1, precision)) + ' > ' + str(self.truncate(val2, precision))
            else:
                return label + ': ' + str(self.truncate(val1, precision)) + ' > ' + str(self.truncate(val2, precision))
        if val1 < val2:
            if label == '':
                return str(self.truncate(val1, precision)) + ' < ' + str(self.truncate(val2, precision))
            else:
                return label + ': ' + str(self.truncate(val1, precision)) + ' < ' + str(self.truncate(val2, precision))
        else:
            if label == '':
                return str(self.truncate(val1, precision)) + ' = ' + str(self.truncate(val2, precision))
            else:
                return label + ': ' + str(self.truncate(val1, precision)) + ' = ' + str(self.truncate(val2, precision))

    def getTakerFee(self):
        if self.exchange == 'coinbasepro':
            api = CBAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIPassphrase(), self.getAPIURL())
            return api.getTakerFee()
        elif self.exchange == 'binance':
            api = BAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIURL())
            return api.getTakerFee(self.getMarket())
        else:
            return 0.005

    def getMakerFee(self):
        if self.exchange == 'coinbasepro':
            api = CBAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIPassphrase(), self.getAPIURL())
            return api.getMakerFee()
        elif self.exchange == 'binance':
            api = BAuthAPI(self.getAPIKey(), self.getAPISecret(), self.getAPIURL())
            #return api.getMakerFee()
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
                return api.marketBuy(market, self.truncate(quote_currency, 2))
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
        github = Github()

        if banner:
            print('--------------------------------------------------------------------------------')
            print('|                             Python Crypto Bot                                |')
            print('--------------------------------------------------------------------------------')
            txt = '              Release : ' + github.getLatestReleaseName()
            print('|', txt, (' ' * (75 - len(txt))), '|')

            print('--------------------------------------------------------------------------------')

            if self.isVerbose() == 1:
                txt = '               Market : ' + self.getMarket()
                print('|', txt, (' ' * (75 - len(txt))), '|')
                if self.exchange == 'coinbasepro':
                    txt = '          Granularity : ' + str(self.getGranularity()) + ' seconds'
                elif self.exchange == 'binance':
                    txt = '          Granularity : ' + str(self.getGranularity())
                print('|', txt, (' ' * (75 - len(txt))), '|')
                print('--------------------------------------------------------------------------------')

            if self.isLive() == 1:
                txt = '             Bot Mode : LIVE - live trades using your funds!'
            else:
                txt = '             Bot Mode : TEST - test trades using dummy funds :)'

            print('|', txt, (' ' * (75 - len(txt))), '|')

            txt = '          Bot Started : ' + str(datetime.now())
            print('|', txt, (' ' * (75 - len(txt))), '|')
            print('================================================================================')

            if self.sellUpperPcnt() != None:
                txt = '       Sell Upper : ' + str(self.sellUpperPcnt()) + '%'
                print('|', txt, (' ' * (75 - len(txt))), '|')

            if self.sellLowerPcnt() != None:
                txt = '       Sell Lower : ' + str(self.sellLowerPcnt()) + '%'
                print('|', txt, (' ' * (75 - len(txt))), '|')

            txt = '         Sell At Loss : ' + str(bool(self.allowSellAtLoss())) + '  --sellatloss ' + str(self.allowSellAtLoss())
            print('|', txt, (' ' * (75 - len(txt))), '|')

            txt = '   Sell At Resistance : ' + str(self.sellAtResistance()) + '  --sellatresistance'
            print('|', txt, (' ' * (75 - len(txt))), '|')   

            txt = '      Trade Bull Only : ' + str(not self.disableBullOnly()) + '  --disablebullonly'
            print('|', txt, (' ' * (75 - len(txt))), '|')

            txt = '        Buy Near High : ' + str(not self.disableBuyNearHigh()) + '  --disablebuynearhigh'
            print('|', txt, (' ' * (75 - len(txt))), '|')

            txt = '         Use Buy MACD : ' + str(not self.disableBuyMACD()) + '  --disablebuymacd'
            print('|', txt, (' ' * (75 - len(txt))), '|')

            txt = '          Use Buy OBV : ' + str(not self.disableBuyOBV()) + '  --disablebuyobv'
            print('|', txt, (' ' * (75 - len(txt))), '|')

            txt = '    Use Buy Elder-Ray : ' + str(not self.disableBuyElderRay()) + '  --disablebuyelderray'
            print('|', txt, (' ' * (75 - len(txt))), '|')             

            txt = '   Sell Fibonacci Low : ' + str(not self.disableFailsafeFibonacciLow()) + '  --disablefailsafefibonaccilow'
            print('|', txt, (' ' * (75 - len(txt))), '|')   

            if self.sellLowerPcnt() != None:
                txt = '      Sell Lower Pcnt : ' + str(not self.disableFailsafeLowerPcnt()) + '  --disablefailsafelowerpcnt'
                print('|', txt, (' ' * (75 - len(txt))), '|')   

            if self.sellUpperPcnt() != None:
                txt = '      Sell Upper Pcnt : ' + str(not self.disableFailsafeLowerPcnt()) + '  --disableprofitbankupperpcnt'
                print('|', txt, (' ' * (75 - len(txt))), '|')   

            txt = ' Candlestick Reversal : ' + str(not self.disableProfitbankReversal()) + '  --disableprofitbankreversal'
            print('|', txt, (' ' * (75 - len(txt))), '|')   

            txt = '             Telegram : ' + str(not self.disableTelegram()) + '  --disabletelegram'
            print('|', txt, (' ' * (75 - len(txt))), '|')

            txt = '                  Log : ' + str(not self.disableLog()) + '  --disablelog'
            print('|', txt, (' ' * (75 - len(txt))), '|')     

            txt = '              Tracker : ' + str(not self.disableTracker()) + '  --disabletracker'
            print('|', txt, (' ' * (75 - len(txt))), '|') 

            txt = '     Auto restart Bot : ' + str(self.autoRestart()) + '  --autorestart'
            print('|', txt, (' ' * (75 - len(txt))), '|')

            print('================================================================================')

        # if live
        if self.isLive() == 1:
            if self.getExchange() == 'binance':
                if last_action == 'SELL'and account.getBalance(self.getQuoteCurrency()) < 0.001:
                    raise Exception('Insufficient available funds to place buy order: ' + str(account.getBalance(self.getQuoteCurrency())) + ' < 0.1 ' + self.getQuoteCurrency() + "\nNote: A manual limit order places a hold on available funds.")
                elif last_action == 'BUY'and account.getBalance(self.getBaseCurrency()) < 0.001:
                    raise Exception('Insufficient available funds to place sell order: ' + str(account.getBalance(self.getBaseCurrency())) + ' < 0.1 ' + self.getBaseCurrency() + "\nNote: A manual limit order places a hold on available funds.")

            elif self.getExchange() == 'coinbasepro':
                if last_action == 'SELL'and account.getBalance(self.getQuoteCurrency()) < 50:
                    raise Exception('Insufficient available funds to place buy order: ' + str(account.getBalance(self.getQuoteCurrency())) + ' < 50 ' + self.getQuoteCurrency() + "\nNote: A manual limit order places a hold on available funds.")
                elif last_action == 'BUY'and account.getBalance(self.getBaseCurrency()) < 0.001:
                    raise Exception('Insufficient available funds to place sell order: ' + str(account.getBalance(self.getBaseCurrency())) + ' < 0.1 ' + self.getBaseCurrency() + "\nNote: A manual limit order places a hold on available funds.")

        # run the first job immediately after starting
        if self.isSimulation() == 1:
            if self.simuluationSpeed() in [ 'fast-sample', 'slow-sample' ]:
                tradingData = pd.DataFrame()

                attempts = 0

                if self.simstartdate != None:
                    date = self.simstartdate.split('-')
                    startDate = datetime(int(date[0]),int(date[1]),int(date[2]))
                    endDate = startDate + timedelta(hours=300)
                    while len(tradingData) != 300 and attempts < 10:
                        tradingData = self.getHistoricalData(self.getMarket(), self.getGranularity(), startDate.isoformat(timespec='milliseconds'), endDate.isoformat(timespec='milliseconds'))
                        attempts += 1
                else:
                    while len(tradingData) != 300 and attempts < 10:
                        endDate = datetime.now() - timedelta(hours=random.randint(0,8760 * 3)) # 3 years in hours
                        startDate = endDate - timedelta(hours=300)
                        tradingData = self.getHistoricalData(self.getMarket(), self.getGranularity(), startDate.isoformat(timespec='milliseconds'), endDate.isoformat(timespec='milliseconds'))
                        attempts += 1
                    if len(tradingData) != 300:
                        raise Exception('Unable to retrieve 300 random sets of data between ' + str(startDate) + ' and ' + str(endDate) + ' in ' + str(attempts) + ' attempts.')

                if banner:
                    startDate = str(startDate.isoformat())
                    endDate = str(endDate.isoformat())
                    txt = '   Sampling start : ' + str(startDate)
                    print('|', txt, (' ' * (75 - len(txt))), '|')
                    txt = '     Sampling end : ' + str(endDate)
                    print('|', txt, (' ' * (75 - len(txt))), '|')
                    if self.simstartdate != None:
                        txt = '    WARNING: Using less than 300 intervals'
                        print('|', txt, (' ' * (75 - len(txt))), '|')
                        txt = '    Interval size : ' + str(len(tradingData))
                        print('|', txt, (' ' * (75 - len(txt))), '|')
                    print('================================================================================')

            else:
                tradingData = self.getHistoricalData(self.getMarket(), self.getGranularity())

            return tradingData