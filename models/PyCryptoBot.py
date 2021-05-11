import pandas as pd
import argparse, json, logging, math, random, re, sys, urllib3
from datetime import datetime, timedelta
from models.Trading import TechnicalAnalysis
from models.Binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI
from models.CoinbasePro import AuthAPI as CBAuthAPI, PublicAPI as CBPublicAPI
from models.Github import Github

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
parser.add_argument('--buypercent', type=str, help="percentage of quote currency to buy")
parser.add_argument('--sellpercent', type=str, help="percentage of base currency to sell")
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
args, unknown = parser.parse_known_args()

class PyCryptoBot():
    def __init__(self, exchange='coinbasepro', filename='config.json'):
        self.api_key = ''
        self.api_secret = ''
        self.api_passphrase = ''
        self.api_url = ''

        if args.config != None:
            filename = args.config
        if args.exchange != None:
            if args.exchange not in [ 'coinbasepro', 'binance', 'dummy' ]:
                raise TypeError('Invalid exchange: coinbasepro, binance')
            else:
                self.exchange = args.exchange
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

        self._telegram_token = None
        self._telegram_client_id = None

        self.logfile = args.logfile if args.logfile else "pycryptobot.log"

        try:
            with open(filename) as config_file:
                config = json.load(config_file)

                if 'telegram' in config and 'token' in config['telegram'] and 'client_id' in config['telegram']:
                    telegram = config['telegram']

                    p1 = re.compile(r"^\d{1,10}:[A-z0-9-_]{35,35}$")
                    p2 = re.compile(r"^\-*\d{7,10}$")

                    if not p1.match(telegram['token']):
                        print ('Error: Telegram token is invalid')
                    elif not p2.match(telegram['client_id']):
                        print ('Error: Telegram client_id is invalid')
                    else:
                        self.telegram = True
                        self._telegram_token = telegram['token']
                        self._telegram_client_id = telegram['client_id']

                if exchange not in config and 'binance' in config:
                    self.exchange = 'binance'

                if self.exchange == 'coinbasepro' and 'api_key' in config and 'api_secret' in config and ('api_pass' in config or 'api_passphrase' in config) and 'api_url' in config:
                    self.api_key = config['api_key']
                    self.api_secret = config['api_secret']

                    if 'api_pass' in config:
                        self.api_passphrase = config['api_pass']
                    elif 'api_passphrase' in config:
                        self.api_passphrase = config['api_passphrase']

                    self.api_url = config['api_url']

                    if 'config' in config:
                        config = config['config']

                        if 'base_currency' in config:
                            if not self._isCurrencyValid(config['base_currency']):
                                raise TypeError('Base currency is invalid.')
                            self.base_currency = config['base_currency']

                        if 'cryptoMarket' in config:
                            if not self._isCurrencyValid(config['cryptoMarket']):
                                raise TypeError('Base currency is invalid.')
                            self.base_currency = config['cryptoMarket']

                        if 'quote_currency' in config:
                            if not self._isCurrencyValid(config['quote_currency']):
                                raise TypeError('Quote currency is invalid.')
                            self.quote_currency = config['quote_currency']

                        if 'fiatMarket' in config:
                            if not self._isCurrencyValid(config['fiatMarket']):
                                raise TypeError('Quote currency is invalid.')
                            self.quote_currency = config['fiatMarket']

                        if 'market' in config:
                            if not self._isMarketValid(config['market']):
                                raise TypeError('Market is invalid.')

                            self.base_currency, self.quote_currency = config['market'].split('-',  2)
                            self.market = config['market']

                        if self.base_currency != '' and self.quote_currency != '':
                            self.market = self.base_currency + '-' + self.quote_currency

                        if 'live' in config:
                            if isinstance(config['live'], int):
                                if config['live'] in [ 0, 1 ]:
                                    self.is_live = config['live']

                        if 'verbose' in config:
                            if isinstance(config['verbose'], int):
                                if config['verbose'] in [ 0, 1 ]:
                                    self.is_verbose = config['verbose']

                        if 'graphs' in config:
                            if isinstance(config['graphs'], int):
                                if config['graphs'] in [ 0, 1 ]:
                                    self.save_graphs = config['graphs']

                        if 'sim' in config:
                            if isinstance(config['sim'], str):
                                if config['sim'] in [ 'slow', 'fast']:
                                    self.is_live = 0
                                    self.is_sim = 1
                                    self.sim_speed = config['sim']

                                if config['sim'] in ['slow-sample', 'fast-sample' ]:
                                    self.is_live = 0
                                    self.is_sim = 1
                                    self.sim_speed = config['sim']
                                    if 'simstartdate' in config:
                                        self.simstartdate = config['simstartdate']

                        if 'sellupperpcnt' in config:
                            if isinstance(config['sellupperpcnt'], (int, str)):
                                p = re.compile(r"^[0-9\.]{1,5}$")
                                if isinstance(config['sellupperpcnt'], str) and p.match(config['sellupperpcnt']):
                                    self.sell_upper_pcnt = float(config['sellupperpcnt'])
                                elif isinstance(config['sellupperpcnt'], int) and config['sellupperpcnt'] > 0 and config['sellupperpcnt'] <= 100:
                                    self.sell_upper_pcnt = float(config['sellupperpcnt'])

                        if 'selllowerpcnt' in config:
                            if isinstance(config['selllowerpcnt'], (int, str)):
                                p = re.compile(r"^\-[0-9\.]{1,5}$")
                                if isinstance(config['selllowerpcnt'], str) and p.match(config['selllowerpcnt']):
                                    self.sell_lower_pcnt = float(config['selllowerpcnt'])
                                elif isinstance(config['selllowerpcnt'], int) and config['selllowerpcnt'] >= -100 and config['selllowerpcnt'] < 0:
                                    self.sell_lower_pcnt = float(config['selllowerpcnt'])

                        if 'trailingstoploss' in config:
                            if isinstance(config['trailingstoploss'], (int, str)):
                                p = re.compile(r"^\-[0-9\.]{1,5}$")
                                if isinstance(config['trailingstoploss'], str) and p.match(config['trailingstoploss']):
                                    self.trailing_stop_loss = float(config['trailingstoploss'])
                                elif isinstance(config['trailingstoploss'], int) and config['trailingstoploss'] >= -100 and config['trailingstoploss'] < 0:
                                    self.trailing_stop_loss = float(config['trailingstoploss'])

                        if 'sellatloss' in config:
                            if isinstance(config['sellatloss'], int):
                                if config['sellatloss'] in [ 0, 1 ]:
                                    self.sell_at_loss = config['sellatloss']
                                    if self.sell_at_loss == 0:
                                        self.sell_lower_pcnt = None
                                        self.trailing_stop_loss = None

                        if 'sellatresistance' in config:
                            if isinstance(config['sellatresistance'], int):
                                if config['sellatresistance'] in [ 0, 1 ]:
                                    self.sellatresistance= bool(config['sellatresistance'])

                        if 'autorestart' in config:
                            if isinstance(config['autorestart'], int):
                                if config['autorestart'] in [ 0, 1 ]:
                                    self.autorestart= bool(config['autorestart'])

                        if 'disablebullonly' in config:
                            if isinstance(config['disablebullonly'], int):
                                if config['disablebullonly'] in [ 0, 1 ]:
                                    self.disablebullonly = bool(config['disablebullonly'])

                        if 'disablebuynearhigh' in config:
                            if isinstance(config['disablebuynearhigh'], int):
                                if config['disablebuynearhigh'] in [ 0, 1 ]:
                                    self.disablebuynearhigh = bool(config['disablebuynearhigh'])

                        if 'disablebuymacd' in config:
                            if isinstance(config['disablebuymacd'], int):
                                if config['disablebuymacd'] in [ 0, 1 ]:
                                    self.disablebuymacd = bool(config['disablebuymacd'])

                        if 'disablebuyobv' in config:
                            if isinstance(config['disablebuyobv'], int):
                                if config['disablebuyobv'] in [ 0, 1 ]:
                                    self.disablebuyobv = bool(config['disablebuyobv'])

                        if 'disablebuyelderray' in config:
                            if isinstance(config['disablebuyelderray'], int):
                                if config['disablebuyelderray'] in [ 0, 1 ]:
                                    self.disablebuyelderray = bool(config['disablebuyelderray'])

                        if 'disablefailsafefibonaccilow' in config:
                            if isinstance(config['disablefailsafefibonaccilow'], int):
                                if config['disablefailsafefibonaccilow'] in [ 0, 1 ]:
                                    self.disablefailsafefibonaccilow = bool(config['disablefailsafefibonaccilow'])

                        if 'disablefailsafelowerpcnt' in config:
                            if isinstance(config['disablefailsafelowerpcnt'], int):
                                if config['disablefailsafelowerpcnt'] in [ 0, 1 ]:
                                    self.disablefailsafelowerpcnt = bool(config['disablefailsafelowerpcnt'])

                        if 'disableprofitbankupperpcnt' in config:
                            if isinstance(config['disableprofitbankupperpcnt'], int):
                                if config['disableprofitbankupperpcnt'] in [ 0, 1 ]:
                                    self.disableprofitbankupperpcnt = bool(config['disableprofitbankupperpcnt'])

                        if 'disableprofitbankreversal' in config:
                            if isinstance(config['disableprofitbankreversal'], int):
                                if config['disableprofitbankreversal'] in [ 0, 1 ]:
                                    self.disableprofitbankreversal = bool(config['disableprofitbankreversal'])

                        if 'disabletelegram' in config:
                            if isinstance(config['disabletelegram'], int):
                                if config['disabletelegram'] in [ 0, 1 ]:
                                    self.disabletelegram = bool(config['disabletelegram'])

                        if 'disablelog' in config:
                            if isinstance(config['disablelog'], int):
                                if config['disablelog'] in [ 0, 1 ]:
                                    self.disablelog = bool(config['disablelog'])

                        if 'disabletracker' in config:
                            if isinstance(config['disabletracker'], int):
                                if config['disabletracker'] in [ 0, 1 ]:
                                    self.disabletracker = bool(config['disabletracker'])

                        # backward compatibility
                        if 'nosellatloss' in config:
                            if isinstance(config['nosellatloss'], int):
                                if config['nosellatloss'] in [ 0, 1 ]:
                                    self.sell_at_loss = int(not config['nosellatloss'])
                                    if self.sell_at_loss == 0:
                                        self.sell_lower_pcnt = None
                                        self.trailing_stop_loss = None

                        if 'smartswitch' in config:
                            if isinstance(config['smartswitch'], int):
                                if config['smartswitch'] in [ 0, 1 ]:
                                    self.smart_switch = config['smartswitch']
                                    if self.smart_switch == 1:
                                        self.smart_switch = 1
                                    else:
                                        self.smart_switch = 0

                        if 'granularity' in config:
                            if isinstance(config['granularity'], int):
                                if config['granularity'] in [ 60, 300, 900, 3600, 21600, 86400 ]:
                                    self.granularity = config['granularity']
                                    self.smart_switch = 0

                        if 'buypercent' in config:
                            if isinstance(config['buypercent'], int):
                                if config['buypercent'] > 0 and config['buypercent'] <= 100:
                                    self.buypercent = config['buypercent']

                        if 'sellpercent' in config:
                            if isinstance(config['sellpercent'], int):
                                if config['sellpercent'] > 0 and config['sellpercent'] <= 100:
                                    self.sellpercent = config['sellpercent']

                        if 'lastaction' in config:
                            if isinstance(config['lastaction'], str):
                                if config['lastaction'] in [ 'BUY', 'SELL' ]:
                                    self.last_action = bool(config['lastaction'])

                elif self.exchange == 'binance' and 'api_key' in config and 'api_secret' in config and 'api_url' in config:
                    self.api_key = config['api_key']
                    self.api_secret = config['api_secret']
                    self.api_url = config['api_url']
                    self.base_currency = 'BTC'
                    self.quote_currency = 'GBP'
                    self.granularity = '1h'

                    if 'binance' not in config:
                        raise Exception('config.json does not contain Binance API keys.')

                    elif 'config' in config['binance']:
                        config = config['binance']['config']

                        if 'base_currency' in config:
                            if not self._isCurrencyValid(config['base_currency']):
                                raise TypeError('Base currency is invalid.')
                            self.base_currency = config['base_currency']

                        if 'quote_currency' in config:
                            if not self._isCurrencyValid(config['base_currency']):
                                raise TypeError('Quote currency is invalid.')
                            self.quote_currency = config['quote_currency']

                        if self.base_currency != '' and self.quote_currency != '':
                            self.market = self.base_currency + self.quote_currency

                        if 'live' in config:
                            if isinstance(config['live'], int):
                                if config['live'] in [0, 1]:
                                    self.is_live = config['live']

                        if 'verbose' in config:
                            if isinstance(config['verbose'], int):
                                if config['verbose'] in [0, 1]:
                                    self.is_verbose = config['verbose']

                        if 'graphs' in config:
                            if isinstance(config['graphs'], int):
                                if config['graphs'] in [0, 1]:
                                    self.save_graphs = config['graphs']

                        if 'sim' in config:
                            if isinstance(config['sim'], str):
                                if config['sim'] in [ 'slow', 'fast']:
                                    self.is_live = 0
                                    self.is_sim = 1
                                    self.sim_speed = config['sim']

                                if config['sim'] in ['slow-sample', 'fast-sample' ]:
                                    self.is_live = 0
                                    self.is_sim = 1
                                    self.sim_speed = config['sim']
                                    if 'simstartdate' in config:
                                        self.simstartdate = config['simstartdate']

                        if 'sellupperpcnt' in config:
                            if isinstance(config['sellupperpcnt'], (int, str)):
                                p = re.compile(r"^[0-9\.]{1,5}$")
                                if isinstance(config['sellupperpcnt'], str) and p.match(config['sellupperpcnt']):
                                    self.sell_upper_pcnt = float(config['sellupperpcnt'])
                                elif isinstance(config['sellupperpcnt'], int) and config['sellupperpcnt'] > 0 and config['sellupperpcnt'] <= 100:
                                    self.sell_upper_pcnt = float(config['sellupperpcnt'])

                        if 'selllowerpcnt' in config:
                            if isinstance(config['selllowerpcnt'], (int, str)):
                                p = re.compile(r"^\-[0-9\.]{1,5}$")
                                if isinstance(config['selllowerpcnt'], str) and p.match(config['selllowerpcnt']):
                                    self.sell_lower_pcnt = float(config['selllowerpcnt'])
                                elif isinstance(config['selllowerpcnt'], int) and config['selllowerpcnt'] >= -100 and config['selllowerpcnt'] < 0:
                                    self.sell_lower_pcnt = float(config['selllowerpcnt'])

                        if 'trailingstoploss' in config:
                            if isinstance(config['trailingstoploss'], (int, str)):
                                p = re.compile(r"^\-[0-9\.]{1,5}$")
                                if isinstance(config['trailingstoploss'], str) and p.match(config['trailingstoploss']):
                                    self.trailing_stop_loss = float(config['trailingstoploss'])
                                elif isinstance(config['trailingstoploss'], int) and config['trailingstoploss'] >= -100 and config['trailingstoploss'] < 0:
                                    self.trailing_stop_loss = float(config['trailingstoploss'])

                        if 'sellatloss' in config:
                            if isinstance(config['sellatloss'], int):
                                if config['sellatloss'] in [ 0, 1 ]:
                                    self.sell_at_loss = config['sellatloss']
                                    if self.sell_at_loss == 0:
                                        self.sell_lower_pcnt = None
                                        self.trailing_stop_loss = None

                        if 'sellatresistance' in config:
                            if isinstance(config['sellatresistance'], int):
                                if config['sellatresistance'] in [ 0, 1 ]:
                                    self.sellatresistance= bool(config['sellatresistance'])

                        if 'autorestart' in config:
                            if isinstance(config['autorestart'], int):
                                if config['autorestart'] in [ 0, 1 ]:
                                    self.autorestart= bool(config['autorestart'])

                        if 'disablebullonly' in config:
                            if isinstance(config['disablebullonly'], int):
                                if config['disablebullonly'] in [ 0, 1 ]:
                                    self.disablebullonly = bool(config['disablebullonly'])

                        if 'disablebuynearhigh' in config:
                            if isinstance(config['disablebuynearhigh'], int):
                                if config['disablebuynearhigh'] in [ 0, 1 ]:
                                    self.disablebuynearhigh = bool(config['disablebuynearhigh'])

                        if 'disablebuymacd' in config:
                            if isinstance(config['disablebuymacd'], int):
                                if config['disablebuymacd'] in [ 0, 1 ]:
                                    self.disablebuymacd = bool(config['disablebuymacd'])

                        if 'disablebuyobv' in config:
                            if isinstance(config['disablebuyobv'], int):
                                if config['disablebuyobv'] in [ 0, 1 ]:
                                    self.disablebuyobv = bool(config['disablebuyobv'])

                        if 'disablebuyelderray' in config:
                            if isinstance(config['disablebuyelderray'], int):
                                if config['disablebuyelderray'] in [ 0, 1 ]:
                                    self.disablebuyelderray = bool(config['disablebuyelderray'])

                        if 'disablefailsafefibonaccilow' in config:
                            if isinstance(config['disablefailsafefibonaccilow'], int):
                                if config['disablefailsafefibonaccilow'] in [ 0, 1 ]:
                                    self.disablefailsafefibonaccilow = bool(config['disablefailsafefibonaccilow'])

                        if 'disablefailsafelowerpcnt' in config:
                            if isinstance(config['disablefailsafelowerpcnt'], int):
                                if config['disablefailsafelowerpcnt'] in [ 0, 1 ]:
                                    self.disablefailsafelowerpcnt = bool(config['disablefailsafelowerpcnt'])

                        if 'disableprofitbankupperpcnt' in config:
                            if isinstance(config['disableprofitbankupperpcnt'], int):
                                if config['disableprofitbankupperpcnt'] in [ 0, 1 ]:
                                    self.disableprofitbankupperpcnt = bool(config['disableprofitbankupperpcnt'])

                        if 'disableprofitbankreversal' in config:
                            if isinstance(config['disableprofitbankreversal'], int):
                                if config['disableprofitbankreversal'] in [ 0, 1 ]:
                                    self.disableprofitbankreversal = bool(config['disableprofitbankreversal'])

                        if 'disabletelegram' in config:
                            if isinstance(config['disabletelegram'], int):
                                if config['disabletelegram'] in [ 0, 1 ]:
                                    self.disabletelegram = bool(config['disabletelegram'])

                        if 'disablelog' in config:
                            if isinstance(config['disablelog'], int):
                                if config['disablelog'] in [ 0, 1 ]:
                                    self.disablelog = bool(config['disablelog'])

                        if 'disabletracker' in config:
                            if isinstance(config['disabletracker'], int):
                                if config['disabletracker'] in [ 0, 1 ]:
                                    self.disabletracker = bool(config['disabletracker'])

                        # backward compatibility
                        if 'nosellatloss' in config:
                            if isinstance(config['nosellatloss'], int):
                                if config['nosellatloss'] in [ 0, 1 ]:
                                    self.sell_at_loss = int(not config['nosellatloss'])
                                    if self.sell_at_loss == 0:
                                        self.sell_lower_pcnt = None
                                        self.trailing_stop_loss = None

                        if 'smartswitch' in config:
                            if isinstance(config['smartswitch'], int):
                                if config['smartswitch'] in [ 0, 1 ]:
                                    self.smart_switch = config['smartswitch']
                                    if self.smart_switch == 1:
                                        self.smart_switch = 1
                                    else:
                                        self.smart_switch = 0

                        if 'granularity' in config:
                            if isinstance(config['granularity'], str):
                                if config['granularity'] in [ '1m', '5m', '15m', '1h', '6h', '1d' ]:
                                    self.granularity = config['granularity']
                                    self.smart_switch = 0

                        if 'buypercent' in config:
                            if isinstance(config['buypercent'], int):
                                if config['buypercent'] > 0 and config['buypercent'] <= 100:
                                    self.buypercent = config['buypercent']

                        if 'sellpercent' in config:
                            if isinstance(config['sellpercent'], int):
                                if config['sellpercent'] > 0 and config['sellpercent'] <= 100:
                                    self.sellpercent = config['sellpercent']

                        if 'lastaction' in config:
                            if isinstance(config['lastaction'], str):
                                if config['lastaction'] in [ 'BUY', 'SELL' ]:
                                    self.last_action = bool(config['lastaction'])

                elif self.exchange == 'coinbasepro' and 'coinbasepro' in config:
                    if 'api_key' in config['coinbasepro'] and 'api_secret' in config['coinbasepro'] and 'api_passphrase' in config['coinbasepro'] and 'api_url' in config['coinbasepro']:
                        self.api_key = config['coinbasepro']['api_key']
                        self.api_secret = config['coinbasepro']['api_secret']
                        self.api_passphrase = config['coinbasepro']['api_passphrase']
                        self.api_url = config['coinbasepro']['api_url']

                        if 'coinbasepro' not in config:
                            raise Exception('config.json does not contain Coinbase Pro API keys.')

                        elif 'config' in config['coinbasepro']:
                            config = config['coinbasepro']['config']

                            if 'base_currency' in config:
                                if not self._isCurrencyValid(config['base_currency']):
                                    raise TypeError('Base currency is invalid.')
                                self.base_currency = config['base_currency']

                            if 'quote_currency' in config:
                                if not self._isCurrencyValid(config['quote_currency']):
                                    raise TypeError('Quote currency is invalid.')
                                self.quote_currency = config['quote_currency']

                            if 'market' in config:
                                if not self._isMarketValid(config['market']):
                                    raise TypeError('Market is invalid.')

                                self.base_currency, self.quote_currency = config['market'].split('-',  2)
                                self.market = config['market']

                            if self.base_currency != '' and self.quote_currency != '':
                                self.market = self.base_currency + '-' + self.quote_currency

                            if 'live' in config:
                                if isinstance(config['live'], int):
                                    if config['live'] in [0, 1]:
                                        self.is_live = config['live']

                            if 'verbose' in config:
                                if isinstance(config['verbose'], int):
                                    if config['verbose'] in [0, 1]:
                                        self.is_verbose = config['verbose']

                            if 'graphs' in config:
                                if isinstance(config['graphs'], int):
                                    if config['graphs'] in [0, 1]:
                                        self.save_graphs = config['graphs']

                            if 'sim' in config:
                                if isinstance(config['sim'], str):
                                    if config['sim'] in [ 'slow', 'fast']:
                                        self.is_live = 0
                                        self.is_sim = 1
                                        self.sim_speed = config['sim']

                                    if config['sim'] in ['slow-sample', 'fast-sample' ]:
                                        self.is_live = 0
                                        self.is_sim = 1
                                        self.sim_speed = config['sim']
                                        if 'simstartdate' in config:
                                            self.simstartdate = config['simstartdate']

                            if 'sellupperpcnt' in config:
                                if isinstance(config['sellupperpcnt'], (int, str)):
                                    p = re.compile(r"^[0-9\.]{1,5}$")
                                    if isinstance(config['sellupperpcnt'], str) and p.match(config['sellupperpcnt']):
                                        self.sell_upper_pcnt = float(config['sellupperpcnt'])
                                    elif isinstance(config['sellupperpcnt'], int) and config['sellupperpcnt'] > 0 and config['sellupperpcnt'] <= 100:
                                        self.sell_upper_pcnt = float(config['sellupperpcnt'])

                            if 'selllowerpcnt' in config:
                                if isinstance(config['selllowerpcnt'], (int, str)):
                                    p = re.compile(r"\-[0-9\.]{1,5}$")
                                    if isinstance(config['selllowerpcnt'], str) and p.match(config['selllowerpcnt']):
                                        self.sell_lower_pcnt = float(config['selllowerpcnt'])
                                    elif isinstance(config['selllowerpcnt'], int) and config['selllowerpcnt'] >= -100 and config['selllowerpcnt'] < 0:     
                                        self.sell_lower_pcnt = float(config['selllowerpcnt'])

                            if 'trailingstoploss' in config:
                                if isinstance(config['trailingstoploss'], (int, str)):
                                    p = re.compile(r"^\-[0-9\.]{1,5}$")
                                    if isinstance(config['trailingstoploss'], str) and p.match(config['trailingstoploss']):
                                        self.trailing_stop_loss = float(config['trailingstoploss'])
                                    elif isinstance(config['trailingstoploss'], int) and config['trailingstoploss'] >= -100 and config['trailingstoploss'] < 0:
                                        self.trailing_stop_loss = float(config['trailingstoploss'])

                            if 'sellatloss' in config:
                                if isinstance(config['sellatloss'], int):
                                    if config['sellatloss'] in [ 0, 1 ]:
                                        self.sell_at_loss = config['sellatloss']
                                        if self.sell_at_loss == 0:
                                            self.sell_lower_pcnt = None
                                            self.trailing_stop_loss = None

                            if 'sellatresistance' in config:
                                if isinstance(config['sellatresistance'], int):
                                    if config['sellatresistance'] in [ 0, 1 ]:
                                        self.sellatresistance= bool(config['sellatresistance'])

                            if 'autorestart' in config:
                                if isinstance(config['autorestart'], int):
                                    if config['autorestart'] in [ 0, 1 ]:
                                        self.autorestart= bool(config['autorestart'])

                            if 'disablebullonly' in config:
                                if isinstance(config['disablebullonly'], int):
                                    if config['disablebullonly'] in [ 0, 1 ]:
                                        self.disablebullonly = bool(config['disablebullonly'])

                            if 'disablebuynearhigh' in config:
                                if isinstance(config['disablebuynearhigh'], int):
                                    if config['disablebuynearhigh'] in [ 0, 1 ]:
                                        self.disablebuynearhigh = bool(config['disablebuynearhigh'])

                            if 'disablebuymacd' in config:
                                if isinstance(config['disablebuymacd'], int):
                                    if config['disablebuymacd'] in [ 0, 1 ]:
                                        self.disablebuymacd = bool(config['disablebuymacd'])

                            if 'disablebuyobv' in config:
                                if isinstance(config['disablebuyobv'], int):
                                    if config['disablebuyobv'] in [ 0, 1 ]:
                                        self.disablebuyobv = bool(config['disablebuyobv'])

                            if 'disablebuyelderray' in config:
                                if isinstance(config['disablebuyelderray'], int):
                                    if config['disablebuyelderray'] in [ 0, 1 ]:
                                        self.disablebuyelderray = bool(config['disablebuyelderray'])

                            if 'disablefailsafefibonaccilow' in config:
                                if isinstance(config['disablefailsafefibonaccilow'], int):
                                    if config['disablefailsafefibonaccilow'] in [ 0, 1 ]:
                                        self.disablefailsafefibonaccilow = bool(config['disablefailsafefibonaccilow'])

                            if 'disablefailsafelowerpcnt' in config:
                                if isinstance(config['disablefailsafelowerpcnt'], int):
                                    if config['disablefailsafelowerpcnt'] in [ 0, 1 ]:
                                        self.disablefailsafelowerpcnt = bool(config['disablefailsafelowerpcnt'])

                            if 'disableprofitbankupperpcnt' in config:
                                if isinstance(config['disableprofitbankupperpcnt'], int):
                                    if config['disableprofitbankupperpcnt'] in [ 0, 1 ]:
                                        self.disableprofitbankupperpcnt = bool(config['disableprofitbankupperpcnt'])

                            if 'disableprofitbankreversal' in config:
                                if isinstance(config['disableprofitbankreversal'], int):
                                    if config['disableprofitbankreversal'] in [ 0, 1 ]:
                                        self.disableprofitbankreversal = bool(config['disableprofitbankreversal'])

                            if 'disabletelegram' in config:
                                if isinstance(config['disabletelegram'], int):
                                    if config['disabletelegram'] in [ 0, 1 ]:
                                        self.disabletelegram = bool(config['disabletelegram'])

                            if 'disablelog' in config:
                                if isinstance(config['disablelog'], int):
                                    if config['disablelog'] in [ 0, 1 ]:
                                        self.disablelog = bool(config['disablelog'])

                            if 'disabletracker' in config:
                                if isinstance(config['disabletracker'], int):
                                    if config['disabletracker'] in [ 0, 1 ]:
                                        self.disabletracker = bool(config['disabletracker'])

                            # backward compatibility
                            if 'nosellatloss' in config:
                                if isinstance(config['nosellatloss'], int):
                                    if config['nosellatloss'] in [ 0, 1 ]:
                                        self.sell_at_loss = int(not config['nosellatloss'])
                                        if self.sell_at_loss == 0:
                                            self.sell_lower_pcnt = None
                                            self.trailing_stop_loss = None

                            if 'smartswitch' in config:
                                if isinstance(config['smartswitch'], int):
                                    if config['smartswitch'] in [ 0, 1 ]:
                                        self.smart_switch = config['smartswitch']
                                        if self.smart_switch == 1:
                                            self.smart_switch = 1
                                        else:
                                            self.smart_switch = 0

                            if 'granularity' in config:
                                if isinstance(config['granularity'], int):
                                    if config['granularity'] in [60, 300, 900, 3600, 21600, 86400]:
                                        self.granularity = config['granularity']
                                        self.smart_switch = 0

                            if 'buypercent' in config:
                                if isinstance(config['buypercent'], int):
                                    if config['buypercent'] > 0 and config['buypercent'] <= 100:
                                        self.buypercent = config['buypercent']

                            if 'sellpercent' in config:
                                if isinstance(config['sellpercent'], int):
                                    if config['sellpercent'] > 0 and config['sellpercent'] <= 100:
                                        self.sellpercent = config['sellpercent']

                            if 'lastaction' in config:
                                if isinstance(config['lastaction'], str):
                                    if config['lastaction'] in [ 'BUY', 'SELL' ]:
                                        self.last_action = bool(config['lastaction'])

                    else:
                        raise Exception('There is an error in your config.json')

                elif self.exchange == 'binance' and 'binance' in config:
                    if 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
                        self.api_key = config['binance']['api_key']
                        self.api_secret = config['binance']['api_secret']
                        self.api_url = config['binance']['api_url']
                        self.base_currency = 'BTC'
                        self.quote_currency = 'GBP'
                        self.granularity = '1h'

                        if 'config' in config['binance']:
                            config = config['binance']['config']

                            if 'base_currency' in config:
                                if not self._isCurrencyValid(config['base_currency']):
                                    raise TypeError('Base currency is invalid.')
                                self.base_currency = config['base_currency']

                            if 'quote_currency' in config:
                                if not self._isCurrencyValid(config['quote_currency']):
                                    raise TypeError('Quote currency is invalid.')
                                self.quote_currency = config['quote_currency']

                            if self.base_currency != '' and self.quote_currency != '':
                                self.market = self.base_currency + self.quote_currency

                            if 'live' in config:
                                if isinstance(config['live'], int):
                                    if config['live'] in [0, 1]:
                                        self.is_live = config['live']

                            if 'verbose' in config:
                                if isinstance(config['verbose'], int):
                                    if config['verbose'] in [0, 1]:
                                        self.is_verbose = config['verbose']

                            if 'graphs' in config:
                                if isinstance(config['graphs'], int):
                                    if config['graphs'] in [0, 1]:
                                        self.save_graphs = config['graphs']

                            if 'sim' in config:
                                if isinstance(config['sim'], str):
                                    if config['sim'] in [ 'slow', 'fast']:
                                        self.is_live = 0
                                        self.is_sim = 1
                                        self.sim_speed = config['sim']

                                    if config['sim'] in ['slow-sample', 'fast-sample' ]:
                                        self.is_live = 0
                                        self.is_sim = 1
                                        self.sim_speed = config['sim']
                                        if 'simstartdate' in config:
                                            self.simstartdate = config['simstartdate']

                            if 'sellupperpcnt' in config:
                                if isinstance(config['sellupperpcnt'], (int, str)):
                                    p = re.compile(r"^[0-9\.]{1,5}$")
                                    if isinstance(config['sellupperpcnt'], str) and p.match(config['sellupperpcnt']):
                                        self.sell_upper_pcnt = float(config['sellupperpcnt'])
                                    elif isinstance(config['sellupperpcnt'], int) and config['sellupperpcnt'] > 0 and config['sellupperpcnt'] <= 100:
                                        self.sell_upper_pcnt = float(config['sellupperpcnt'])

                            if 'selllowerpcnt' in config:
                                if isinstance(config['selllowerpcnt'], (int, str)):
                                    p = re.compile(r"^\-[0-9\.]{1,5}$")
                                    if isinstance(config['selllowerpcnt'], str) and p.match(config['selllowerpcnt']):
                                        self.sell_lower_pcnt = float(config['selllowerpcnt'])
                                    elif isinstance(config['selllowerpcnt'], int) and config['selllowerpcnt'] >= -100 and config['selllowerpcnt'] < 0:
                                        self.sell_lower_pcnt = float(config['selllowerpcnt'])

                            if 'trailingstoploss' in config:
                                if isinstance(config['trailingstoploss'], (int, str)):
                                    p = re.compile(r"^\-[0-9\.]{1,5}$")
                                    if isinstance(config['trailingstoploss'], str) and p.match(config['trailingstoploss']):
                                        self.trailing_stop_loss = float(config['trailingstoploss'])
                                    elif isinstance(config['trailingstoploss'], int) and config['trailingstoploss'] >= -100 and config['trailingstoploss'] < 0:
                                        self.trailing_stop_loss = float(config['trailingstoploss'])

                            if 'sellatloss' in config:
                                if isinstance(config['sellatloss'], int):
                                    if config['sellatloss'] in [ 0, 1 ]:
                                        self.sell_at_loss = config['sellatloss']
                                        if self.sell_at_loss == 0:
                                            self.sell_lower_pcnt = None

                            if 'sellatresistance' in config:
                                if isinstance(config['sellatresistance'], int):
                                    if config['sellatresistance'] in [ 0, 1 ]:
                                        self.sellatresistance= bool(config['sellatresistance'])

                            if 'autorestart' in config:
                                if isinstance(config['autorestart'], int):
                                    if config['autorestart'] in [ 0, 1 ]:
                                        self.autorestart= bool(config['autorestart'])

                            if 'disablebullonly' in config:
                                if isinstance(config['disablebullonly'], int):
                                    if config['disablebullonly'] in [ 0, 1 ]:
                                        self.disablebullonly = bool(config['disablebullonly'])

                            if 'disablebuynearhigh' in config:
                                if isinstance(config['disablebuynearhigh'], int):
                                    if config['disablebuynearhigh'] in [ 0, 1 ]:
                                        self.disablebuynearhigh = bool(config['disablebuynearhigh'])

                            if 'disablebuymacd' in config:
                                if isinstance(config['disablebuymacd'], int):
                                    if config['disablebuymacd'] in [ 0, 1 ]:
                                        self.disablebuymacd = bool(config['disablebuymacd'])

                            if 'disablebuyobv' in config:
                                if isinstance(config['disablebuyobv'], int):
                                    if config['disablebuyobv'] in [ 0, 1 ]:
                                        self.disablebuyobv = bool(config['disablebuyobv'])

                            if 'disablebuyelderray' in config:
                                if isinstance(config['disablebuyelderray'], int):
                                    if config['disablebuyelderray'] in [ 0, 1 ]:
                                        self.disablebuyelderray = bool(config['disablebuyelderray'])

                            if 'disablefailsafefibonaccilow' in config:
                                if isinstance(config['disablefailsafefibonaccilow'], int):
                                    if config['disablefailsafefibonaccilow'] in [ 0, 1 ]:
                                        self.disablefailsafefibonaccilow = bool(config['disablefailsafefibonaccilow'])

                            if 'disablefailsafelowerpcnt' in config:
                                if isinstance(config['disablefailsafelowerpcnt'], int):
                                    if config['disablefailsafelowerpcnt'] in [ 0, 1 ]:
                                        self.disablefailsafelowerpcnt = bool(config['disablefailsafelowerpcnt'])

                            if 'disableprofitbankupperpcnt' in config:
                                if isinstance(config['disableprofitbankupperpcnt'], int):
                                    if config['disableprofitbankupperpcnt'] in [ 0, 1 ]:
                                        self.disableprofitbankupperpcnt = bool(config['disableprofitbankupperpcnt'])

                            if 'disableprofitbankreversal' in config:
                                if isinstance(config['disableprofitbankreversal'], int):
                                    if config['disableprofitbankreversal'] in [ 0, 1 ]:
                                        self.disableprofitbankreversal = bool(config['disableprofitbankreversal'])

                            if 'disabletelegram' in config:
                                if isinstance(config['disabletelegram'], int):
                                    if config['disabletelegram'] in [ 0, 1 ]:
                                        self.disabletelegram = bool(config['disabletelegram'])

                            if 'disablelog' in config:
                                if isinstance(config['disablelog'], int):
                                    if config['disablelog'] in [ 0, 1 ]:
                                        self.disablelog = bool(config['disablelog'])

                            if 'disabletracker' in config:
                                if isinstance(config['disabletracker'], int):
                                    if config['disabletracker'] in [ 0, 1 ]:
                                        self.disabletracker = bool(config['disabletracker'])

                            # backward compatibility
                            if 'nosellatloss' in config:
                                if isinstance(config['nosellatloss'], int):
                                    if config['nosellatloss'] in [ 0, 1 ]:
                                        self.sell_at_loss = int(not config['nosellatloss'])
                                        if self.sell_at_loss == 0:
                                            self.sell_lower_pcnt = None
                                            self.trailing_stop_loss = None

                            if 'smartswitch' in config:
                                if isinstance(config['smartswitch'], int):
                                    if config['smartswitch'] in [ 0, 1 ]:
                                        self.smart_switch = config['smartswitch']
                                        if self.smart_switch == 1:
                                            self.smart_switch = 1
                                        else:
                                            self.smart_switch = 0

                            if 'granularity' in config:
                                if isinstance(config['granularity'], str):
                                    if config['granularity'] in ['1m', '5m', '15m', '1h', '6h', '1d']:
                                        self.granularity = config['granularity']
                                        self.smart_switch = 0

                            if 'buypercent' in config:
                                if isinstance(config['buypercent'], int):
                                    if config['buypercent'] > 0 and config['buypercent'] <= 100:
                                        self.buypercent = config['buypercent']

                            if 'sellpercent' in config:
                                if isinstance(config['sellpercent'], int):
                                    if config['sellpercent'] > 0 and config['sellpercent'] <= 100:
                                        self.sellpercent = config['sellpercent']

                            if 'lastaction' in config:
                                if isinstance(config['lastaction'], str):
                                    if config['lastaction'] in [ 'BUY', 'SELL' ]:
                                        self.last_action = bool(config['lastaction'])

                    else:
                        raise Exception('There is an error in your config.json')

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

        if args.market != None:
            if self.exchange == 'coinbasepro':
                if not self._isMarketValid(args.market):
                    raise ValueError('Coinbase Pro market required.')

                self.market = args.market
                self.base_currency, self.quote_currency = args.market.split('-',  2)
            elif self.exchange == 'binance':
                if not self._isMarketValid(args.market):
                    raise ValueError('Binance market required.')

                self.market = args.market
                if self.market.endswith('BTC'):
                    self.base_currency = self.market.replace('BTC', '')
                    self.quote_currency = 'BTC'
                elif self.market.endswith('BNB'):
                    self.base_currency = self.market.replace('BNB', '')
                    self.quote_currency = 'BNB'
                elif self.market.endswith('ETH'):
                    self.base_currency = self.market.replace('ETH', '')
                    self.quote_currency = 'ETH'
                elif self.market.endswith('USDT'):
                    self.base_currency = self.market.replace('USDT', '')
                    self.quote_currency = 'USDT'
                elif self.market.endswith('TUSD'):
                    self.base_currency = self.market.replace('TUSD', '')
                    self.quote_currency = 'TUSD'
                elif self.market.endswith('BUSD'):
                    self.base_currency = self.market.replace('BUSD', '')
                    self.quote_currency = 'BUSD'
                elif self.market.endswith('DAX'):
                    self.base_currency = self.market.replace('DAX', '')
                    self.quote_currency = 'DAX'
                elif self.market.endswith('NGN'):
                    self.base_currency = self.market.replace('NGN', '')
                    self.quote_currency = 'NGN'
                elif self.market.endswith('RUB'):
                    self.base_currency = self.market.replace('RUB', '')
                    self.quote_currency = 'RUB'
                elif self.market.endswith('TRY'):
                    self.base_currency = self.market.replace('TRY', '')
                    self.quote_currency = 'TRY'
                elif self.market.endswith('EUR'):
                    self.base_currency = self.market.replace('EUR', '')
                    self.quote_currency = 'EUR'
                elif self.market.endswith('GBP'):
                    self.base_currency = self.market.replace('GBP', '')
                    self.quote_currency = 'GBP'
                elif self.market.endswith('ZAR'):
                    self.base_currency = self.market.replace('ZAR', '')
                    self.quote_currency = 'ZAR'
                elif self.market.endswith('UAH'):
                    self.base_currency = self.market.replace('UAH', '')
                    self.quote_currency = 'UAH'
                elif self.market.endswith('DAI'):
                    self.base_currency = self.market.replace('DAI', '')
                    self.quote_currency = 'DAI'
                elif self.market.endswith('BIDR'):
                    self.base_currency = self.market.replace('BIDR', '')
                    self.quote_currency = 'BIDR'
                elif self.market.endswith('AUD'):
                    self.base_currency = self.market.replace('AUD', '')
                    self.quote_currency = 'AUD'
                elif self.market.endswith('US'):
                    self.base_currency = self.market.replace('US', '')
                    self.quote_currency = 'US'
                elif self.market.endswith('NGN'):
                    self.base_currency = self.market.replace('NGN', '')
                    self.quote_currency = 'NGN'
                elif self.market.endswith('BRL'):
                    self.base_currency = self.market.replace('BRL', '')
                    self.quote_currency = 'BRL'
                elif self.market.endswith('BVND'):
                    self.base_currency = self.market.replace('BVND', '')
                    self.quote_currency = 'BVND'
                elif self.market.endswith('VAI'):
                    self.base_currency = self.market.replace('VAI', '')
                    self.quote_currency = 'VAI'

                if len(self.market) != len(self.base_currency) + len(self.quote_currency):
                    raise ValueError('Binance market error.')

            else:
                if self.market == '' and self.base_currency == '' and self.quote_currency == '':
                    self.market = 'BTC-GBP'
                    self.base_currency = 'BTC'
                    self.quote_currency = 'GBP'

        if args.smartswitch != None:
            if not args.smartswitch in [ '0', '1' ]:
                self.smart_switch = args.smartswitch
                if self.smart_switch == 1:
                    self.smart_switch = 1
                else:
                    self.smart_switch = 0

        if args.granularity != None:
            if self.exchange == 'coinbasepro':
                if not isinstance(int(args.granularity), int):
                    raise TypeError('Invalid granularity.')

                if not int(args.granularity) in [ 60, 300, 900, 3600, 21600, 86400 ]:
                    raise TypeError('Granularity options: 60, 300, 900, 3600, 21600, 86400')
            elif self.exchange == 'binance':
                if not isinstance(args.granularity, str):
                    raise TypeError('Invalid granularity.')

                if not args.granularity in [ '1m', '5m', '15m', '1h', '6h', '1d' ]:
                    raise TypeError('Granularity options: 1m, 5m, 15m, 1h, 6h, 1d')

            self.granularity = args.granularity
            self.smart_switch = 0

        if args.buypercent != None:
            if not isinstance(int(args.buypercent), int):
                raise TypeError('Invalid buy percent.')

            if int(args.buypercent) < 1 or int(args.buypercent) > 100:
                raise ValueError('Invalid buy percent.')

            self.buypercent = args.buypercent

        if args.sellpercent != None:
            if not isinstance(int(args.sellpercent), int):
                raise TypeError('Invalid sell percent.')

            if int(args.sellpercent) < 1 or int(args.sellpercent) > 100:
                raise ValueError('Invalid sell percent.')

            self.sellpercent = args.sellpercent

        if self.smart_switch == 1 and self.granularity is None:
            if self.exchange == 'coinbasepro':
                self.granularity = 3600
            elif self.exchange == 'binance':
                self.granularity = '1h'

        if args.graphs != None:
            if not args.graphs in [ '0', '1' ]:
                self.save_graphs = args.graphs

        if args.verbose != None:
            if not args.verbose in [ '0', '1' ]:
                self.is_verbose = args.verbose

        if args.live != None:
            if not args.live in [ '0', '1' ]:
                self.is_live = args.live

        if args.sim != None:
            if args.sim == 'slow':
                self.is_sim = 1
                self.sim_speed = 'slow'
                self.is_live = 0
            elif args.sim == 'slow-sample':
                self.is_sim = 1
                self.sim_speed = 'slow-sample'
                self.is_live = 0
                if args.simstartdate != None:
                    self.simstartdate = args.simstartdate
            elif args.sim == 'fast':
                self.is_sim = 1
                self.sim_speed = 'fast'
                self.is_live = 0
            elif args.sim == 'fast-sample':
                self.is_sim = 1
                self.sim_speed = 'fast-sample'
                self.is_live = 0
                if args.simstartdate != None:
                    self.simstartdate = args.simstartdate
        
        if self.simstartdate != None:
            p = re.compile(r"^\d{4,4}-\d{2,2}-\d{2,2}$")
            if not p.match(self.simstartdate):
                self.simstartdate = None

        if args.sellupperpcnt != None:
            if isinstance(args.sellupperpcnt, (int, float)):
                if args.sellupperpcnt > 0 and args.sellupperpcnt <= 100:
                    self.sell_upper_pcnt = float(args.sellupperpcnt)

        if args.selllowerpcnt != None:
            if isinstance(args.selllowerpcnt, (int, float)):
                if args.selllowerpcnt >= -100 and args.selllowerpcnt < 0:
                    self.sell_lower_pcnt = float(args.selllowerpcnt)

        if args.trailingstoploss != None:
            if isinstance(args.trailingstoploss, (int, float)):
                if args.trailingstoploss >= -100 and args.trailingstoploss < 0:
                    self.trailing_stop_loss = float(args.trailingstoploss)

        if args.sellatloss != None:
            if not args.sellatloss in [ '0', '1' ]:
                self.sell_at_loss = args.sellatloss
                if self.sell_at_loss == 0:
                    self.sell_lower_pcnt = None
                    self.trailing_stop_loss = None

        if args.lastaction != None:
            if isinstance(args.lastaction, str):
                if args.lastaction in [ 'BUY', 'SELL' ]:
                    self.last_action = args.lastaction

        if args.sellatresistance is True:
            self.sellatresistance = True

        if args.autorestart is True:
            self.autorestart = True

        if args.disablebullonly is True:
            self.disablebullonly = True

        if args.disablebuynearhigh is True:
            self.disablebuynearhigh = True

        if args.disablebuymacd is True:
            self.disablebuymacd = True

        if args.disablebuyobv is True:
            self.disablebuyobv = True
    
        if args.disablebuyelderray is True:
            self.disablebuyelderray = True

        if args.disablefailsafefibonaccilow is True:
            self.disablefailsafefibonaccilow = True

        if args.disablefailsafelowerpcnt is True:
            self.disablefailsafelowerpcnt = True

        if args.disableprofitbankupperpcnt is True:
            self.disableprofitbankupperpcnt = True
               
        if args.disableprofitbankreversal is True:
            self.disableprofitbankreversal = True

        if args.disabletelegram is True:
            self.disabletelegram = True

        if args.disablelog is True:
            self.disablelog = True

        if args.disabletracker is True:
            self.disabletracker = True
        
        if self.exchange == 'binance':
            if len(self.api_url) > 1 and self.api_url[-1] != '/':
                self.api_url = self.api_url + '/'

            valid_urls = [
                'https://api.binance.com/',
                'https://testnet.binance.vision/api/'
            ]

            # validate Binance API
            if self.api_url not in valid_urls:
                raise ValueError('Binance API URL is invalid')

            # validates the api key is syntactically correct
            p = re.compile(r"^[A-z0-9]{64,64}$")
            if not p.match(self.api_key):
                raise TypeError('Binance API key is invalid')

            # validates the api secret is syntactically correct
            p = re.compile(r"^[A-z0-9]{64,64}$")
            if not p.match(self.api_secret):
                raise TypeError('Binance API secret is invalid')

        elif self.exchange == 'coinbasepro':
            if self.api_url[-1] != '/':
                self.api_url = self.api_url + '/'

            valid_urls = [
                'https://api.pro.coinbase.com/'
            ]

            # validate Coinbase Pro API
            if self.api_url not in valid_urls:
                raise ValueError('Coinbase Pro API URL is invalid')

            # validates the api key is syntactically correct
            p = re.compile(r"^[a-f0-9]{32,32}$")
            if not p.match(self.api_key):
                raise TypeError('Coinbase Pro API key is invalid')

            # validates the api secret is syntactically correct
            p = re.compile(r"^[A-z0-9+\/]+==$")
            if not p.match(self.api_secret):
                raise TypeError('Coinbase Pro API secret is invalid')

            # validates the api passphrase is syntactically correct
            p = re.compile(r"^[a-z0-9]{10,11}$")
            if not p.match(self.api_passphrase):
                raise TypeError('Coinbase Pro API passphrase is invalid')

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
            p = re.compile(r"^[A-Z]{6,12}$")
            return p.match(market)

        return False

    def getLogFile(self):
        return self.logfile

    def getExchange(self):
        return self.exchange

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
            return BPublicAPI().getTime()
        else:
            return ''

    def getTelegramToken(self):
        return self._telegram_token

    def getTelegramClientId(self):
        return self._telegram_client_id

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
            #return api.getTakerFee()
            return 0.005
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
            p = re.compile(r"^[A-Z]{6,12}$")
            if p.match(market):
                self.market = market

                if self.market.endswith('BTC'):
                    self.base_currency = self.market.replace('BTC', '')
                    self.quote_currency = 'BTC'
                elif self.market.endswith('BNB'):
                    self.base_currency = self.market.replace('BNB', '')
                    self.quote_currency = 'BNB'
                elif self.market.endswith('ETH'):
                    self.base_currency = self.market.replace('ETH', '')
                    self.quote_currency = 'ETH'
                elif self.market.endswith('USDT'):
                    self.base_currency = self.market.replace('USDT', '')
                    self.quote_currency = 'USDT'
                elif self.market.endswith('TUSD'):
                    self.base_currency = self.market.replace('TUSD', '')
                    self.quote_currency = 'TUSD'
                elif self.market.endswith('BUSD'):
                    self.base_currency = self.market.replace('BUSD', '')
                    self.quote_currency = 'BUSD'
                elif self.market.endswith('DAX'):
                    self.base_currency = self.market.replace('DAX', '')
                    self.quote_currency = 'DAX'
                elif self.market.endswith('NGN'):
                    self.base_currency = self.market.replace('NGN', '')
                    self.quote_currency = 'NGN'
                elif self.market.endswith('RUB'):
                    self.base_currency = self.market.replace('RUB', '')
                    self.quote_currency = 'RUB'
                elif self.market.endswith('TRY'):
                    self.base_currency = self.market.replace('TRY', '')
                    self.quote_currency = 'TRY'
                elif self.market.endswith('EUR'):
                    self.base_currency = self.market.replace('EUR', '')
                    self.quote_currency = 'EUR'
                elif self.market.endswith('GBP'):
                    self.base_currency = self.market.replace('GBP', '')
                    self.quote_currency = 'GBP'
                elif self.market.endswith('ZAR'):
                    self.base_currency = self.market.replace('ZAR', '')
                    self.quote_currency = 'ZAR'
                elif self.market.endswith('UAH'):
                    self.base_currency = self.market.replace('UAH', '')
                    self.quote_currency = 'UAH'
                elif self.market.endswith('DAI'):
                    self.base_currency = self.market.replace('DAI', '')
                    self.quote_currency = 'DAI'
                elif self.market.endswith('BIDR'):
                    self.base_currency = self.market.replace('BIDR', '')
                    self.quote_currency = 'BIDR'
                elif self.market.endswith('AUD'):
                    self.base_currency = self.market.replace('AUD', '')
                    self.quote_currency = 'AUD'
                elif self.market.endswith('US'):
                    self.base_currency = self.market.replace('US', '')
                    self.quote_currency = 'US'
                elif self.market.endswith('NGN'):
                    self.base_currency = self.market.replace('NGN', '')
                    self.quote_currency = 'NGN'
                elif self.market.endswith('BRL'):
                    self.base_currency = self.market.replace('BRL', '')
                    self.quote_currency = 'BRL'
                elif self.market.endswith('BVND'):
                    self.base_currency = self.market.replace('BVND', '')
                    self.quote_currency = 'BVND'
                elif self.market.endswith('VAI'):
                    self.base_currency = self.market.replace('VAI', '')
                    self.quote_currency = 'VAI'

                if len(self.market) != len(self.base_currency) + len(self.quote_currency):
                    raise ValueError('Binance market error.')

        elif self.exchange == 'coinbasepro':
            p = re.compile(r"^[A-Z]{3,5}\-[A-Z]{3,5}$")
            if p.match(market):
                self.market = market
                self.base_currency, self.quote_currency = market.split('-',  2)

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
                    raise Exception('Insufficient available funds to place sell order: ' + str(account.getBalance(self.getQuoteCurrency())) + ' < 0.1 ' + self.getQuoteCurrency() + "\nNote: A manual limit order places a hold on available funds.")
                elif last_action == 'BUY'and account.getBalance(self.getBaseCurrency()) < 0.001:
                    raise Exception('Insufficient available funds to place buy order: ' + str(account.getBalance(self.getBaseCurrency())) + ' < 0.1 ' + self.getBaseCurrency() + "\nNote: A manual limit order places a hold on available funds.")

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