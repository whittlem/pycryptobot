from models.exchange.coinbase_pro.api import FREQUENCY_EQUIVALENTS, SUPPORTED_GRANULARITY
import math
import re
import numpy as np
import pandas as pd
import sys
from datetime import datetime, timedelta
from binance.client import Client
from time import sleep
from models.helper.LogHelper import Logger


DEFAULT_MAKER_FEE_RATE = 0.0015 # added 0.0005 to allow for price movements
DEFAULT_TAKER_FEE_RATE = 0.0015 # added 0.0005 to allow for price movements
DEFAULT_TRADE_FEE_RATE = 0.0015 # added 0.0005 to allow for price movements
DEFAULT_GRANULARITY="1h"
SUPPORTED_GRANULARITY = ['1m', '5m', '15m', '1h', '6h', '1d']
MULTIPLIER_EQUIVALENTS = [1, 5, 15, 60, 360, 1440]
FREQUENCY_EQUIVALENTS = ["T", "5T", "15T", "H", "6H", "D"]
DEFAULT_MARKET = "BTCGBP"


class AuthAPIBase():
    def _isMarketValid(self, market: str) -> bool:
        p = re.compile(r"^[A-Z0-9]{5,12}$")
        if p.match(market):
            return True
        return False


class AuthAPI(AuthAPIBase):
    def __init__(self, api_key: str='', api_secret: str='', api_url: str='https://api.binance.com') -> None:
        """Binance API object model
    
        Parameters
        ----------
        api_key : str
            Your Binance account portfolio API key
        api_secret : str
            Your Binance account portfolio API secret
        """
    
        # options
        self.debug = False
        self.die_on_api_error = False

        valid_urls = [
            'https://api.binance.com/',
            'https://api.binance.us/',
            'https://testnet.binance.vision/api/'
        ]

        if len(api_url) > 1 and api_url[-1] != '/':
            api_url = api_url + '/'

        # validate Binance API
        if api_url not in valid_urls:
            raise ValueError('Binance API URL is invalid')

        # validates the api key is syntactically correct
        p = re.compile(r"^[A-z0-9]{64,64}$")
        if not p.match(api_key):
            self.handle_init_error('Binance API key is invalid')
 
        # validates the api secret is syntactically correct
        p = re.compile(r"^[A-z0-9]{64,64}$")
        if not p.match(api_secret):
            self.handle_init_error('Binance API secret is invalid')

        self.mode = 'live' # TODO: check if this needs to be set here
        self.api_url = api_url
        self.api_key = api_key
        self.api_secret = api_secret

        for i in range(10):
            try:
                sys.tracebacklimit = 0
                if 'api.binance.us' in api_url:
                    self.client = Client(self.api_key, self.api_secret, { 'verify': False, 'timeout': 20 }, tld='us')
                else:
                    self.client = Client(self.api_key, self.api_secret, { 'verify': False, 'timeout': 20 })
                break
            except Exception as e:
                if i == 9:
                    raise SystemExit("Can not create instance of AuthAPI client.")
                Logger.error('Exception: ' + str(e)) 
                Logger.error('Error on creating instance of AuthAPI Client. Trying again... Attempt: ' + str(i))
                sleep(0.1)

        sys.tracebacklimit = 1


    def handle_init_error(self, err: str) -> None:
        if self.debug:
            raise TypeError(err)
        else:
            raise SystemExit(err)


    def getClient(self) -> Client:
        return self.client


    def getAccount(self):
        """Retrieves a specific account"""
        account = self.client.get_account()
        if 'balances' in account:
            df = pd.DataFrame(account['balances'])
            df = df[(df['free'] != '0.00000000') & (df['free'] != '0.00')]
            df['free'] = df['free'].astype(float)
            df['locked'] = df['locked'].astype(float)
            df['balance'] = df['free'] - df['locked']
            df.columns = ['currency', 'available', 'hold', 'balance']
            df = df[['currency', 'balance', 'hold', 'available']]
            df = df.reset_index(drop=True)
            return df
        else:
            return 0.0


    def getFees(self, market: str='') -> pd.DataFrame:
        if market != '':
            resp = self.client.get_trade_fee(symbol=market)
            if 'tradeFee' in resp and len(resp['tradeFee']) > 0:
                df = pd.DataFrame(resp['tradeFee'][0], index=[0])
                df['usd_volume'] = None
                df.columns = [ 'maker_fee_rate', 'market', 'taker_fee_rate', 'usd_volume' ]
                return df[[ 'maker_fee_rate', 'taker_fee_rate', 'usd_volume', 'market' ]]
            return pd.DataFrame(columns=[ 'maker_fee_rate', 'taker_fee_rate', 'market' ])
        else:
            resp = self.client.get_trade_fee()
            if 'tradeFee' in resp:
                df = pd.DataFrame(resp['tradeFee'])
                df['usd_volume'] = None
                df.columns = [ 'maker_fee_rate', 'market', 'taker_fee_rate', 'usd_volume' ]
                return df[[ 'maker_fee_rate', 'taker_fee_rate', 'usd_volume', 'market' ]]
            return pd.DataFrame(columns=[ 'maker_fee_rate', 'taker_fee_rate', 'market' ])


    def getMakerFee(self, market: str='') -> float:
        if market == '':
            fees = self.getFees()
        else:
            fees = self.getFees(market)
        
        if len(fees) == 0 or 'maker_fee_rate' not in fees:
            Logger.error(f"error: 'maker_fee_rate' not in fees (using {DEFAULT_MAKER_FEE_RATE} as a fallback)")
            return DEFAULT_MAKER_FEE_RATE

        if market == '':
            return fees
        else:
            return float(fees['maker_fee_rate'].to_string(index=False).strip())


    def getTakerFee(self, market: str='') -> float:
        if market == '':
            return DEFAULT_TAKER_FEE_RATE
        else:
            fees = self.getFees(market)

        if len(fees) == 0 or 'taker_fee_rate' not in fees:
            Logger.error(f"error: 'taker_fee_rate' not in fees (using {DEFAULT_TAKER_FEE_RATE} as a fallback)")
            return DEFAULT_TAKER_FEE_RATE

        return float(fees['taker_fee_rate'].to_string(index=False).strip())


    def __convertStatus(self, val: str) -> str:
        if val == 'filled':
            return 'done'
        else:
            return val


    def getOrders(self, market: str='', action: str='', status: str='all') -> pd.DataFrame:
        """Retrieves your list of orders with optional filtering"""

        # if market provided
        if market != '':
            # validates the market is syntactically correct
            if not self._isMarketValid(market):
                raise ValueError('Binance market is invalid.')

        # if action provided
        if action != '':
            # validates action is either a buy or sell
            if not action in ['buy', 'sell']:
                raise ValueError('Invalid order action.')

        # validates status is either open, pending, done, active, or all
        if not status in ['open', 'pending', 'done', 'active', 'all']:
            raise ValueError('Invalid order status.')

        resp = self.client.get_all_orders(symbol=market)
        if len(resp) > 0:
            df = pd.DataFrame(resp)
        else:
            df = pd.DataFrame()

        if len(df) == 0:
            return pd.DataFrame()

        # replace null NaN values with 0
        df.fillna(0, inplace=True)

        df = df[[ 'time', 'symbol', 'side', 'type', 'executedQty', 'cummulativeQuoteQty', 'status' ]]
        df.columns = [ 'created_at', 'market', 'action', 'type', 'filled', 'size', 'status' ]
        df['created_at'] = df['created_at'].apply(lambda x: int(str(x)[:10]))
        df['created_at'] = df['created_at'].astype("datetime64[s]")
        df['size'] = df['size'].astype(float)
        df['filled'] = df['filled'].astype(float)
        df['action'] = df['action'].str.lower()
        df['type'] = df['type'].str.lower()
        df['status'] = df['status'].str.lower()
        df['price'] = df['size'] / df['filled']

        # pylint: disable=unused-variable
        for k, v in df.items():
            if k == 'status':
                df[k] = df[k].map(self.__convertStatus)

        if action != '':
            df = df[df['action'] == action]
            df = df.reset_index(drop=True)

        if status != 'all' and status != '':
            df = df[df['status'] == status]
            df = df.reset_index(drop=True)

        return df


    def marketBuy(self, market: str='', quote_quantity: float=0) -> list:
        """Executes a market buy providing a funding amount"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise ValueError('Binance market is invalid.')

        # validates quote_quantity is either an integer or float
        if not isinstance(quote_quantity, int) and not isinstance(quote_quantity, float):
            raise TypeError('The funding amount is not numeric.')

        try:
            current_price = self.getTicker(market)[1]

            base_quantity = np.divide(quote_quantity, current_price)

            df_filters = self.getMarketInfoFilters(market)
            step_size = float(df_filters.loc[df_filters['filterType'] == 'LOT_SIZE']['stepSize'])
            precision = int(round(-math.log(step_size, 10), 0))

            # remove fees
            base_quantity = base_quantity - (base_quantity * self.getTradeFee(market))

            # execute market buy
            stepper = 10.0 ** precision
            truncated = math.trunc(stepper * base_quantity) / stepper
            Logger.info('Order quantity after rounding and fees: ' + str(truncated))

            return self.client.order_market_buy(symbol=market, quantity=truncated)
        except Exception as err:
            ts = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            Logger.error(ts + ' Binance ' + ' marketBuy ' + str(err))
            return []       


    def marketSell(self, market: str='', base_quantity: float=0) -> list:
        """Executes a market sell providing a crypto amount"""

        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise ValueError('Binance market is invalid.')

        if not isinstance(base_quantity, int) and not isinstance(base_quantity, float):
            raise TypeError('The crypto amount is not numeric.')

        try:
            df_filters = self.getMarketInfoFilters(market)
            step_size = float(df_filters.loc[df_filters['filterType'] == 'LOT_SIZE']['stepSize'])
            precision = int(round(-math.log(step_size, 10), 0))

            # remove fees
            base_quantity = base_quantity - (base_quantity * self.getTradeFee(market))

            # execute market sell
            stepper = 10.0 ** precision
            truncated = math.trunc(stepper * base_quantity) / stepper
            Logger.info('Order quantity after rounding and fees: ' + str(truncated))
            return self.client.order_market_sell(symbol=market, quantity=truncated)
        except Exception as err:
            ts = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            Logger.error(ts + ' Binance ' + ' marketSell ' + str(err))
            return []


    def getTradeFee(self, market: str) -> float:
        resp = self.client.get_trade_fee(symbol=market, timestamp=self.getTime())
      
        if 'tradeFee' not in resp:
            Logger.info('*** getTradeFee(' + market + ') - missing "tradeFee" ***')
            Logger.info(resp)
        else:
            if len(resp['tradeFee']) == 0:
                Logger.info('*** getTradeFee(' + market + ') - "tradeFee" empty ***') 
                Logger.info(resp)
            else:
                if 'taker' not in resp['tradeFee'][0]:
                    Logger.info('*** getTradeFee(' + market + ') - missing "trader" ***')
                    Logger.info(resp)                    

        if 'success' in resp:
            return resp['tradeFee'][0]['taker']
        else:
            return DEFAULT_TRADE_FEE_RATE


    def getMarketInfo(self, market: str) -> dict:
        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError('Binance market required.')

        return self.client.get_symbol_info(symbol=market)


    def getMarketInfoFilters(self, market: str) -> pd.DataFrame:
        return pd.DataFrame(self.client.get_symbol_info(symbol=market)['filters'])


    def getTicker(self, market:str) -> tuple:
        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError('Binance market required.')

        resp = self.client.get_symbol_ticker(symbol=market)

        if 'price' in resp:
            return (self.getTime().strftime('%Y-%m-%d %H:%M:%S'), float('{:.8f}'.format(float(resp['price']))))

        now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        return (now, 0.0)


    def getTime(self) -> datetime:
        """Retrieves the exchange time"""
    
        try:
            resp = self.client.get_server_time()
            epoch = int(str(resp['serverTime'])[0:10])
            return datetime.fromtimestamp(epoch)
        except:
            return None


class PublicAPI(AuthAPIBase):
    def __init__(self) -> None:
        for i in range(10):
            try:
                self.client = Client()
                break
            except Exception as e:
                if i == 9:
                    raise SystemExit("Can not create instance of AuthAPI client.")
                Logger.error('Exception: ' + str(e)) 
                Logger.error('Error on creating instance of AuthAPI Client. Trying again... Attempt: ' + str(i))
                sleep(0.1)
               

    def __truncate(self, f, n) -> int:
        return math.floor(f * 10 ** n) / 10 ** n

    
    def getClient(self) -> Client:
        return self.client

    
    def getHistoricalData(self, market: str=DEFAULT_MARKET, granularity: str=DEFAULT_GRANULARITY, iso8601start: str='', iso8601end: str='') -> pd.DataFrame:
        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError('Binance market required.')

        # validates granularity is a string
        if not isinstance(granularity, str):
            raise TypeError('Granularity string required.')

        # validates the granularity is supported by Binance
        if not granularity in SUPPORTED_GRANULARITY:
            raise TypeError('Granularity options: ' + ", ".join(map(str, SUPPORTED_GRANULARITY)))

        # validates the ISO 8601 start date is a string (if provided)
        if not isinstance(iso8601start, str):
            raise TypeError('ISO8601 start integer as string required.')

        # validates the ISO 8601 end date is a string (if provided)
        if not isinstance(iso8601end, str):
            raise TypeError('ISO8601 end integer as string required.')

        # if only a start date is provided
        if iso8601start != '' and iso8601end == '':
            try:
                multiplier = MULTIPLIER_EQUIVALENTS[SUPPORTED_GRANULARITY.index(granularity)] 
            except:
                multiplier = 1
    
            # calculate the end date using the granularity
            iso8601end = str((datetime.strptime(iso8601start, '%Y-%m-%dT%H:%M:%S.%f') + timedelta(minutes=granularity * multiplier)).isoformat())

        if iso8601start != '' and iso8601end != '':
            Logger.info('Attempting to retrieve data from ' + iso8601start)
            resp = self.client.get_historical_klines(market, granularity, iso8601start)

            if len(resp) > 300:
                resp = resp[:300]
        else: # TODO: replace with a KLINE_MESSAGE_FOO equivalent
            if granularity == '1m':
                resp = self.client.get_historical_klines(market, granularity, '12 hours ago UTC')
                resp = resp[-300:]
            elif granularity == '5m':
                resp = self.client.get_historical_klines(market, granularity, '2 days ago UTC')
                resp = resp[-300:]
            elif granularity == '15m':
                resp = self.client.get_historical_klines(market, granularity, '4 days ago UTC')
                resp = resp[-300:]
            elif granularity == '1h':
                resp = self.client.get_historical_klines(market, granularity, '13 days ago UTC')
                resp = resp[-300:]
            elif granularity == '6h':
                resp = self.client.get_historical_klines(market, granularity, '75 days ago UTC')
                resp = resp[-300:]
            elif granularity == '1d':
                resp = self.client.get_historical_klines(market, granularity, '251 days ago UTC')
            else:
                raise Exception('Something went wrong!')
                   
        # convert the API response into a Pandas DataFrame
        df = pd.DataFrame(resp, columns=[ 'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'traker_buy_quote_asset_volume', 'ignore' ])
        df['market'] = market
        df['granularity'] = granularity

        # binance epoch is too long
        df['open_time'] = df['open_time'] + 1
        df['open_time'] = df['open_time'].astype(str)
        df['open_time'] = df['open_time'].str.replace(r'\d{3}$', '', regex=True)   

        try:
            freq = FREQUENCY_EQUIVALENTS[SUPPORTED_GRANULARITY.index(granularity)]
        except:
            freq = "D"

        # convert the DataFrame into a time series with the date as the index/key
        try:
            tsidx = pd.DatetimeIndex(pd.to_datetime(df['open_time'], unit='s'), dtype='datetime64[ns]', freq=freq)
            df.set_index(tsidx, inplace=True)
            df = df.drop(columns=['open_time'])
            df.index.names = ['ts']
            df['date'] = tsidx
        except ValueError:
            tsidx = pd.DatetimeIndex(pd.to_datetime(df['open_time'], unit='s'), dtype='datetime64[ns]')
            df.set_index(tsidx, inplace=True)
            df = df.drop(columns=['open_time'])
            df.index.names = ['ts']           
            df['date'] = tsidx

        # re-order columns
        df = df[[ 'date', 'market', 'granularity', 'low', 'high', 'open', 'close', 'volume' ]]

        # correct column types
        df['low'] = df['low'].astype(float)
        df['high'] = df['high'].astype(float)   
        df['open'] = df['open'].astype(float)   
        df['close'] = df['close'].astype(float)   
        df['volume'] = df['volume'].astype(float)      

        # reset pandas dataframe index
        df.reset_index()

        return df

    
    def getTicker(self, market: str) -> tuple:
        # validates the market is syntactically correct
        if not self._isMarketValid(market):
            raise TypeError('Binance market required.')

        resp = self.client.get_symbol_ticker(symbol=market)

        if 'price' in resp:
            return (self.getTime().strftime('%Y-%m-%d %H:%M:%S'), float('{:.8f}'.format(float(resp['price']))))

        now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        return (now, 0.0)

    
    def getTime(self) -> datetime:
        """Retrieves the exchange time"""
    
        try:
            resp = self.client.get_server_time()
            epoch = int(str(resp['serverTime'])[0:10])
            return datetime.fromtimestamp(epoch)
        except:
            return None

