import argparse, json, re, sys
from models.Trading import TechnicalAnalysis
from models.CoinbasePro import PublicAPI
from views.TradingGraphs import TradingGraphs

market = ''
granularity = 0

# instantiate the arguments parser
parser = argparse.ArgumentParser(description='Python Crypto Bot using the Coinbase Pro API')

# optional arguments
parser.add_argument('--granularity', type=int, help='Provide granularity via arguments')
parser.add_argument('--market', type=str, help='Provide Market via arguments')

# parse arguments
args = parser.parse_args()

# preload config from config.json if it exists
try:
    # open the config.json file
    with open('config.json') as config_file:
        # store the configuration in dictionary
        config = json.load(config_file)

        if 'config' in config:
            if 'cryptoMarket' and 'fiatMarket' in config['config']:
                crypto_market = config['config']['cryptoMarket']
                fiat_market = config['config']['fiatMarket']
                market = crypto_market + '-' + fiat_market

            if 'granularity' in config['config']:
                if isinstance(config['config']['granularity'], int):
                    if config['config']['granularity'] in [ 60, 300, 900, 3600, 21600, 86400 ]:
                        granularity = config['config']['granularity']

except IOError:
    print("warning: 'config.json' not found.")

if args.market != None:
    # market set via --market argument
    market = args.market

if args.granularity != None:
    # granularity set via --granularity argument
    granularity = args.granularity

# validates the market is syntactically correct
p = re.compile(r"^[A-Z]{3,4}\-[A-Z]{3,4}$")
if not p.match(market):
    raise TypeError('Coinbase Pro market required.')

# validates granularity is an integer
if not isinstance(granularity, int):
    raise TypeError('Granularity integer required.')

# validates the granularity is supported by Coinbase Pro
if not granularity in [60, 300, 900, 3600, 21600, 86400]:
    raise TypeError('Granularity options: 60, 300, 900, 3600, 21600, 86400.')

api = PublicAPI()
tradingData = api.getHistoricalData(market, granularity)

technicalAnalysis = TechnicalAnalysis(tradingData)
technicalAnalysis.addAll()

tradinggraphs = TradingGraphs(technicalAnalysis)
tradinggraphs.renderFibonacciRetracement(True)
tradinggraphs.renderSupportResistance(True)
tradinggraphs.renderCandlesticks(30, True)
tradinggraphs.renderSeasonalARIMAModelPrediction(1, True)