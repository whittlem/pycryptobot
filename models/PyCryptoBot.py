import json, re
from datetime import datetime, timedelta

class Config():
    def __init__(self, exchange='dummy', filename='config.json'):
        try:
            with open(filename) as config_file:
                config = json.load(config_file)

                self.exchange = 'dummy'
                self.api_key = ''
                self.api_secret = ''
                self.api_passphrase = ''
                self.api_url = ''
                self.base_currency = 'BTC'
                self.quote_currency = 'GBP'
                self.market = 'BTC-GBP'
                self.granularity = 3600
                self.is_live = 0
                self.is_verbose = 1
                self.save_graphs = 0
                self.is_sim = 0
                self.sim_speed = 'fast'
                self.sell_upper_pcnt = None
                self.sell_lower_pcnt = None

                if exchange == 'coinbasepro' and 'api_key' in config and 'api_secret' in config and 'api_pass' in config and 'api_url' in config:
                    self.exchange = 'coinbasepro'
                    self.api_key = config['api_key']
                    self.api_secret = config['api_secret']
                    self.api_passphrase = config['api_passphrase']
                    self.api_url = config['api_url']

                    if 'config' in config:
                        config = config['config']
                        
                        if 'base_currency' in config:
                            p = re.compile(r"^[A-Z]{3,5}$")
                            if not p.match(config['base_currency']):
                                raise TypeError('Base currency is invalid.')
                            self.base_currency = config['base_currency']
                        
                        if 'quote_currency' in config:
                            p = re.compile(r"^[A-Z]{3,5}$")
                            if not p.match(config['quote_currency']):
                                raise TypeError('Quote currency is invalid.')
                            self.quote_currency = config['quote_currency']
                        
                        if 'market' in config:
                            p = re.compile(r"^[A-Z]{3,5}\-[A-Z]{3,5}$")
                            if not p.match(config['market']):
                                raise TypeError('Market is invalid.')

                            self.base_currency, self.quote_currency = config['market'].split('-',  2)
                            self.market = config['market']

                        if self.base_currency != '' and self.quote_currency != '':
                            self.market = self.base_currency + '-' + self.quote_currency
                        
                        if 'granularity' in config:
                            if isinstance(config['granularity'], int):
                                if config['granularity'] in [60, 300, 900, 3600, 21600, 86400]:
                                    self.granularity = config['granularity']

                        if 'live' in config:
                            if isinstance(config['live'], int):
                                if config['live'] in [0, 1]:
                                    self.is_live = config['live']

                        if 'verbose' in config:
                            if isinstance(config['verbose'], int):
                                if config['verbose'] in [0, 1]:
                                    self.is_live = config['verbose']

                        if 'graphs' in config:
                            if isinstance(config['graphs'], int):
                                if config['graphs'] in [0, 1]:
                                    self.save_graphs = config['graphs']

                        if 'sim' in config:
                            if isinstance(config['sim'], str):
                                if config['sim'] in ['slow', 'fast', 'slow-sample', 'fast-sample']:
                                    self.is_live = 0
                                    self.is_sim = 1
                                    self.sim_speed = config['sim']

                        if 'sellupperpcnt' in config:
                            if isinstance(config['sellupperpcnt'], int):
                                if config['sellupperpcnt'] > 0 and config['sellupperpcnt'] <= 100:
                                    self.sell_upper_pcnt = int(config['sellupperpcnt'])

                        if 'selllowerpcnt' in config:
                            if isinstance(config['selllowerpcnt'], int):
                                if config['selllowerpcnt'] >= -100 and config['selllowerpcnt'] < 0:
                                    self.sell_lower_pcnt = int(config['selllowerpcnt'])

                elif exchange == 'binance' and 'api_key' in config and 'api_secret' in config and 'api_url' in config:
                    self.exchange = 'binance'
                    self.api_key = config['api_key']
                    self.api_secret = config['api_secret']
                    self.api_url = config['api_url']
                    self.base_currency = 'BTC'
                    self.quote_currency = 'GBP'
                    self.granularity = '1h'

                    if 'config' in config['binance']:
                        config = config['binance']['config']
                        
                        if 'base_currency' in config:
                            p = re.compile(r"^[A-Z]{3,5}$")
                            if not p.match(config['base_currency']):
                                raise TypeError('Base currency is invalid.')
                            self.base_currency = config['base_currency']
                        
                        if 'quote_currency' in config:
                            p = re.compile(r"^[A-Z]{3,5}$")
                            if not p.match(config['quote_currency']):
                                raise TypeError('Quote currency is invalid.')
                            self.quote_currency = config['quote_currency']

                        if self.base_currency != '' and self.quote_currency != '':
                            self.market = self.base_currency + self.quote_currency
                        
                        if 'granularity' in config:
                            if isinstance(config['granularity'], str):
                                if config['granularity'] in ['1m', '5m', '15m', '1h', '6h', '1d']:
                                    self.granularity = config['granularity']

                        if 'live' in config:
                            if isinstance(config['live'], int):
                                if config['live'] in [0, 1]:
                                    self.is_live = config['live']

                        if 'verbose' in config:
                            if isinstance(config['verbose'], int):
                                if config['verbose'] in [0, 1]:
                                    self.is_live = config['verbose']

                        if 'graphs' in config:
                            if isinstance(config['graphs'], int):
                                if config['graphs'] in [0, 1]:
                                    self.save_graphs = config['graphs']

                        if 'sim' in config:
                            if isinstance(config['sim'], str):
                                if config['sim'] in ['slow', 'fast', 'slow-sample', 'fast-sample']:
                                    self.is_live = 0
                                    self.is_sim = 1
                                    self.sim_speed = config['sim']

                        if 'sellupperpcnt' in config:
                            if isinstance(config['sellupperpcnt'], int):
                                if config['sellupperpcnt'] > 0 and config['sellupperpcnt'] <= 100:
                                    self.sell_upper_pcnt = int(config['sellupperpcnt'])

                        if 'selllowerpcnt' in config:
                            if isinstance(config['selllowerpcnt'], int):
                                if config['selllowerpcnt'] >= -100 and config['selllowerpcnt'] < 0:
                                    self.sell_lower_pcnt = int(config['selllowerpcnt'])      

                elif exchange == 'coinbasepro' and 'coinbasepro' in config:
                    if 'api_key' in config['coinbasepro'] and 'api_secret' in config['coinbasepro'] and 'api_passphrase' in config['coinbasepro'] and 'api_url' in config['coinbasepro']:
                        self.exchange = 'coinbasepro'
                        self.api_key = config['coinbasepro']['api_key']
                        self.api_secret = config['coinbasepro']['api_secret']
                        self.api_passphrase = config['coinbasepro']['api_passphrase']
                        self.api_url = config['coinbasepro']['api_url']

                        if 'config' in config['coinbasepro']:
                            config = config['coinbasepro']['config']
                            
                            if 'base_currency' in config:
                                p = re.compile(r"^[A-Z]{3,5}$")
                                if not p.match(config['base_currency']):
                                    raise TypeError('Base currency is invalid.')
                                self.base_currency = config['base_currency']
                            
                            if 'quote_currency' in config:
                                p = re.compile(r"^[A-Z]{3,5}$")
                                if not p.match(config['quote_currency']):
                                    raise TypeError('Quote currency is invalid.')
                                self.quote_currency = config['quote_currency']
                            
                            if 'market' in config:
                                p = re.compile(r"^[A-Z]{3,5}\-[A-Z]{3,5}$")
                                if not p.match(config['market']):
                                    raise TypeError('Market is invalid.')

                                self.base_currency, self.quote_currency = config['market'].split('-',  2)
                                self.market = config['market']

                            if self.base_currency != '' and self.quote_currency != '':
                                self.market = self.base_currency + '-' + self.quote_currency
                            
                            if 'granularity' in config:
                                if isinstance(config['granularity'], int):
                                    if config['granularity'] in [60, 300, 900, 3600, 21600, 86400]:
                                        self.granularity = config['granularity']

                            if 'live' in config:
                                if isinstance(config['live'], int):
                                    if config['live'] in [0, 1]:
                                        self.is_live = config['live']

                            if 'verbose' in config:
                                if isinstance(config['verbose'], int):
                                    if config['verbose'] in [0, 1]:
                                        self.is_live = config['verbose']

                            if 'graphs' in config:
                                if isinstance(config['graphs'], int):
                                    if config['graphs'] in [0, 1]:
                                        self.save_graphs = config['graphs']

                            if 'sim' in config:
                                if isinstance(config['sim'], str):
                                    if config['sim'] in ['slow', 'fast', 'slow-sample', 'fast-sample']:
                                        self.is_live = 0
                                        self.is_sim = 1
                                        self.sim_speed = config['sim']

                            if 'sellupperpcnt' in config:
                                if isinstance(config['sellupperpcnt'], int):
                                    if config['sellupperpcnt'] > 0 and config['sellupperpcnt'] <= 100:
                                        self.sell_upper_pcnt = int(config['sellupperpcnt'])

                            if 'selllowerpcnt' in config:
                                if isinstance(config['selllowerpcnt'], int):
                                    if config['selllowerpcnt'] >= -100 and config['selllowerpcnt'] < 0:
                                        self.sell_lower_pcnt = int(config['selllowerpcnt'])

                elif exchange == 'binance' and 'binance' in config:
                    if 'api_key' in config['binance'] and 'api_secret' in config['binance'] and 'api_url' in config['binance']:
                        self.exchange = 'binance'
                        self.api_key = config['binance']['api_key']
                        self.api_secret = config['binance']['api_secret']
                        self.api_url = config['binance']['api_url']
                        self.base_currency = 'BTC'
                        self.quote_currency = 'GBP'
                        self.granularity = '1h'

                        if 'config' in config['binance']:
                            config = config['binance']['config']
                            
                            if 'base_currency' in config:
                                p = re.compile(r"^[A-Z]{3,5}$")
                                if not p.match(config['base_currency']):
                                    raise TypeError('Base currency is invalid.')
                                self.base_currency = config['base_currency']
                            
                            if 'quote_currency' in config:
                                p = re.compile(r"^[A-Z]{3,5}$")
                                if not p.match(config['quote_currency']):
                                    raise TypeError('Quote currency is invalid.')
                                self.quote_currency = config['quote_currency']

                            if self.base_currency != '' and self.quote_currency != '':
                                self.market = self.base_currency + self.quote_currency
                            
                            if 'granularity' in config:
                                if isinstance(config['granularity'], str):
                                    if config['granularity'] in ['1m', '5m', '15m', '1h', '6h', '1d']:
                                        self.granularity = config['granularity']

                            if 'live' in config:
                                if isinstance(config['live'], int):
                                    if config['live'] in [0, 1]:
                                        self.is_live = config['live']

                            if 'verbose' in config:
                                if isinstance(config['verbose'], int):
                                    if config['verbose'] in [0, 1]:
                                        self.is_live = config['verbose']

                            if 'graphs' in config:
                                if isinstance(config['graphs'], int):
                                    if config['graphs'] in [0, 1]:
                                        self.save_graphs = config['graphs']

                            if 'sim' in config:
                                if isinstance(config['sim'], str):
                                    if config['sim'] in ['slow', 'fast', 'slow-sample', 'fast-sample']:
                                        self.is_live = 0
                                        self.is_sim = 1
                                        self.sim_speed = config['sim']

                            if 'sellupperpcnt' in config:
                                if isinstance(config['sellupperpcnt'], int):
                                    if config['sellupperpcnt'] > 0 and config['sellupperpcnt'] <= 100:
                                        self.sell_upper_pcnt = int(config['sellupperpcnt'])

                            if 'selllowerpcnt' in config:
                                if isinstance(config['selllowerpcnt'], int):
                                    if config['selllowerpcnt'] >= -100 and config['selllowerpcnt'] < 0:
                                        self.sell_lower_pcnt = int(config['selllowerpcnt'])                    

        except IOError as err:
            now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            print (now, err)
        except ValueError as err:
            now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            print (now, err)

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
        return self.granularity

    def isLive(self):
        return self.is_live

    def isVerbose(self):
        return self.is_verbose

    def shouldSaveGraphs(self):
        return self.save_graphs

    def isSimulation(self):
        return self.is_sim

    def simuluationSpeed(self):
        return self.sim_speed
    
    def sellUpperPcnt(self):
        return self.sell_upper_pcnt

    def sellLowerPcnt(self):
        return self.sell_lower_pcnt