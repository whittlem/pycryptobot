import time
import json
import pandas as pd
import re
from decimal import Decimal
from itertools import islice
from models.PyCryptoBot import PyCryptoBot
from models.helper.TelegramBotHelper import TelegramBotHelper as TGBot
from models.exchange.binance import PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import PublicAPI as CPublicAPI
from models.exchange.kucoin import PublicAPI as KPublicAPI
from models.exchange.Granularity import Granularity
from models.exchange.ExchangesEnum import Exchange as CryptoExchange
from tradingview_ta import *


def volatility_calculator(bollinger_band_upper, bollinger_band_lower):
    """
    A break away from traditional volatility calcuations. Based entirely
    on the proportionate price gap between bollinger upper and lower bands.
    """

    try:
        b_spread = Decimal(bollinger_band_upper) - Decimal(bollinger_band_lower)
    except TypeError:
        return 0
    
    return abs(b_spread / Decimal(bollinger_band_lower)) * 100

def load_configs():
    exchanges_loaded = []
    try:
        with open("scanner.json", encoding='utf8') as json_file:
            config = json.load(json_file)
    except IOError as err:
        raise(err)
    try:
        for exchange in config:
            ex = CryptoExchange(exchange)
            exchange_config = config[ex.value]
            if ex == CryptoExchange.BINANCE:
                binance_app = PyCryptoBot(exchange=ex)
                binance_app.public_api = BPublicAPI()
                binance_app.scanner_quote_currencies = exchange_config.get('quote_currency', ['USDT'])
                binance_app.granularity = Granularity(Granularity.convert_to_enum(config.get('granularity', '1h')))
                binance_app.adx_threshold = config.get('adx_threshold', 25)
                binance_app.volatility_threshold = config.get('volatility_threshold', 9)
                binance_app.volume_threshold = config.get('volume_threshold', 20000)
                binance_app.tv_screener_ratings = [rating.upper() for rating in config.get('tv_screener_ratings', ['STRONG_BUY'])]
                exchanges_loaded.append(binance_app)
            elif ex == CryptoExchange.COINBASEPRO:
                coinbase_app = PyCryptoBot(exchange=ex)
                coinbase_app.public_api = CPublicAPI()
                coinbase_app.scanner_quote_currencies = exchange_config.get('quote_currency', ['USDT'])
                coinbase_app.granularity = Granularity(Granularity.convert_to_enum(int(config.get('granularity', '3600'))))
                coinbase_app.adx_threshold = config.get('adx_threshold', 25)
                coinbase_app.volatility_threshold = config.get('volatility_threshold', 9)
                coinbase_app.volume_threshold = config.get('volume_threshold', 20000)
                coinbase_app.tv_screener_ratings = [rating.upper() for rating in config.get('tv_screener_ratings', ['STRONG_BUY'])]
                exchanges_loaded.append(coinbase_app)
            elif ex == CryptoExchange.KUCOIN:
                kucoin_app = PyCryptoBot(exchange=ex)
                kucoin_app.public_api = KPublicAPI()
                kucoin_app.scanner_quote_currencies = exchange_config.get('quote_currency', ['USDT'])
                kucoin_app.granularity = Granularity(Granularity.convert_to_enum(config.get('granularity', '1h')))
                kucoin_app.adx_threshold = config.get('adx_threshold', 25)
                kucoin_app.volatility_threshold = config.get('volatility_threshold', 9)
                kucoin_app.volume_threshold = config.get('volume_threshold', 20000)
                kucoin_app.tv_screener_ratings = [rating.upper() for rating in config.get('tv_screener_ratings', ['STRONG_BUY'])]
                exchanges_loaded.append(kucoin_app)
            else:
                raise ValueError(f"Invalid exchange found in config: {ex}")
    except AttributeError as e:
        print(f"Invalid exchange: {e}...ignoring.")

    return exchanges_loaded

def chunker(market_list, chunk_size):
    markets = iter(market_list)
    market_chunk = list(islice(markets, chunk_size))
    while market_chunk:
        yield market_chunk
        market_chunk = list(islice(markets, chunk_size))

def get_markets(app, quote_currency):
    markets = []
    quote_currency = quote_currency.upper()
    api = app.public_api
    resp = api.getMarkets24HrStats()
    if app.exchange == CryptoExchange.BINANCE:
        for row in resp:
            if row["symbol"].endswith(quote_currency):
                markets.append(row['symbol'])
    elif app.exchange == CryptoExchange.COINBASEPRO:
        for market in resp:
            market = str(market)
            if market.endswith(f"-{quote_currency}"):
                markets.append(market)
    elif app.exchange == CryptoExchange.KUCOIN:
        results = resp["data"]["ticker"]
        for result in results:
            if result["symbol"].endswith(f"-{quote_currency}"):
                markets.append(result['symbol'])
    
    return markets

def process_screener_data(app, markets, quote_currency):
    """
    Hit TradingView up for the goods so we don't waste unnecessary time/compute resources (brandon's top picks)
    """
    
    ta_screener_list = [f"{re.sub('PRO', '', app.exchange.name, re.IGNORECASE)}:{re.sub('-', '', market)}" for market in markets]
    screener_staging = [p for p in chunker(ta_screener_list, 100)]
    screener_analysis = []
    for pair_list in screener_staging:
        screener_analysis.extend([a for a in get_multiple_analysis(screener='crypto', interval=app.granularity.short, symbols=pair_list).values()])
    # Take what we need and do magic, ditch the rest.
    formatted_ta = []
    for ta in screener_analysis:
        try:
            recommend = ta.summary.get('RECOMMENDATION')
            volatility = Decimal(volatility_calculator(ta.indicators['BB.upper'], ta.indicators['BB.lower']))
            adx = abs(Decimal(ta.indicators['ADX']))
            adx_posi_di = Decimal(ta.indicators['ADX+DI'])
            adx_neg_di = Decimal(ta.indicators['ADX-DI'])
            volume = Decimal(ta.indicators['volume'])
            macd = Decimal(ta.indicators['MACD.macd'])
            macd_signal = Decimal(ta.indicators['MACD.signal'])
            bollinger_upper = Decimal(ta.indicators['BB.upper'])
            bollinger_lower = Decimal(ta.indicators['BB.lower'])
            score = 0
            # print('symbol\tvolume\tvvolatilith\tadx\tadx_posi_di\tadx_neg_di\tmacd\tmacd_signal\tbollinger_upper\tbollinger_lower\trecommend')
            # print(ta.symbol, volume, volatility, adx, adx_posi_di, adx_neg_di, macd, macd_signal, bollinger_upper, bollinger_lower, recommend)
            if recommend in app.tv_screener_ratings:
                # print(ta.summary.get('RECOMMENDATION'))
                score += 5
            if (adx >= app.adx_threshold or adx_posi_di > adx) and (adx_posi_di > adx_neg_di):
                # print(f"ADX({adx}) >= {app.adx_threshold}")
                score += 2
            if volume >= app.volume_threshold:
                # print(f"Volume({volume}) >= {app.volume_threshold}")
                score += 1
            if abs(macd) > abs(macd_signal):
                # print(f"MACD({macd}) above signal({macd_signal})")
                score += 1
            if volatility >= app.volatility_threshold:
                # print(f"Volatility({volatility} is above {app.volatility_threshold}")
                score += 1
            if score >= 10:
                relavent_ta = {}
                if app.exchange == CryptoExchange.COINBASEPRO or app.exchange == CryptoExchange.KUCOIN:
                    relavent_ta['market'] = re.sub(quote_currency,f"-{quote_currency}", ta.symbol)
                else:
                    relavent_ta['market'] = ta.symbol
                #relavent_ta['market'] = ta.symbol
                relavent_ta['volume'] = volume
                relavent_ta['volatility'] = volatility
                relavent_ta['adx'] = adx
                relavent_ta['adx+di'] = adx_posi_di
                relavent_ta['adx-di'] = adx_neg_di
                relavent_ta['macd'] = macd
                relavent_ta['macd.signal'] = macd_signal
                relavent_ta['bollinger_upper'] = bollinger_upper
                relavent_ta['bollinger_lower'] = bollinger_lower
                relavent_ta['rating'] = recommend
                try:
                    relavent_ta['buy_next'] = 'SEND IT!' if re.search('.*BUY', recommend).group() else False
                except AttributeError:
                    relavent_ta['buy_next'] = False
                formatted_ta.append(relavent_ta)
        except Exception as e:
            continue
    if formatted_ta:
        # Stick it in a DF for the bots
        df_markets = pd.DataFrame(formatted_ta)
        df_markets = df_markets[["market", "volume", "volatility", "adx", "adx+di", "adx-di", "macd", "macd.signal", "bollinger_upper", "bollinger_lower", "rating", "buy_next"]]
        df_markets.columns = ["market", "volume", "volatility", "adx", "adx+di", "adx-di", "macd", "macd.signal", "bollinger_upper", "bollinger_lower", "rating", "buy_next"]
        df_markets["volume"] = df_markets["volume"].astype(float).round(0).astype(int)
        df_markets["volatility"] = df_markets["volatility"].astype(float)
        df_markets["adx"] = df_markets["adx"].astype(float)
        df_markets["adx+di"] = df_markets["adx+di"].astype(float)
        df_markets["adx-di"] = df_markets["adx-di"].astype(float)
        df_markets["macd"] = df_markets["macd"].astype(float)
        df_markets["macd.signal"] = df_markets["macd.signal"].astype(float)
        df_markets["bollinger_upper"] = df_markets["bollinger_upper"].astype(float)
        df_markets["bollinger_lower"] = df_markets["bollinger_lower"].astype(float)
        df_markets.sort_values(by=["market"], ascending=True, inplace=True)
        df_markets.set_index("market", inplace=True)

        print(df_markets.sort_values(by=["buy_next", "adx"], ascending=[False, False], inplace=False))
        TGBot(app, scanner=True).save_scanner_output(app.exchange.value, quote_currency, df_markets)
    else:
        print('No pairs found!')

    return True


if  __name__ == '__main__':
    import time
    from datetime import datetime


    start_time = time.time()
    print('Processing, please wait...')
    bootstrap_exchanges = load_configs()
    for app in bootstrap_exchanges:
        print(f"\n\n{app.exchange.name}")
        for quote_currency in app.scanner_quote_currencies:
            markets = get_markets(app, quote_currency)
            try:
                process_screener_data(app, markets, quote_currency)
            except Exception as e:
                print(e)
    print("Scan run finished!")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total elapsed time: {time.time() - start_time} sec")
