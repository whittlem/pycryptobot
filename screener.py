import time
import json
import pandas as pd
import re
import sys
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
from importlib.metadata import version

def volatility_calculator(bollinger_band_upper, bollinger_band_lower, keltner_upper, keltner_lower, high, low):
    """
    A break away from traditional volatility calculations. Based entirely
    on the proportionate price gap between keltner channels, bolinger, and high / low averaged out
    """

    try:
        b_spread = Decimal(bollinger_band_upper) - Decimal(bollinger_band_lower)
        k_spread = Decimal(keltner_upper) - Decimal(keltner_lower)
        p_spread = Decimal(high) - Decimal(low)
    except TypeError:
        return 0

    b_pcnt = abs(b_spread / Decimal(bollinger_band_lower)) * 100
    k_pcnt = abs(k_spread / Decimal(keltner_lower)) * 100

    chan_20_pcnt = (b_pcnt + k_pcnt) / 2

    p_pcnt = abs(p_spread / Decimal(low)) * 100
    
    return abs((chan_20_pcnt + p_pcnt) / 2)

def load_configs():
    exchanges_loaded = []
    try:
        with open("screener.json", encoding='utf8') as json_file:
            config = json.load(json_file)
    except IOError as err:
        raise(err)

    try:
        with open("config.json", encoding='utf8') as json_file:
            bot_config = json.load(json_file)
    except IOError as err:
        print (err)

    try:
        for exchange in config:
            ex = CryptoExchange(exchange)
            exchange_config = config[ex.value]
            if ex == CryptoExchange.BINANCE:
                binance_app = PyCryptoBot(exchange=ex)
                binance_app.public_api = BPublicAPI(bot_config[ex.value]["api_url"])
                binance_app.scanner_quote_currencies = exchange_config.get('quote_currency', ['USDT'])
                binance_app.granularity = Granularity(Granularity.convert_to_enum(exchange_config.get('granularity', '1h')))
                binance_app.adx_threshold = exchange_config.get('adx_threshold', 25)
                binance_app.volatility_threshold = exchange_config.get('volatility_threshold', 9)
                binance_app.minimum_volatility = exchange_config.get('minimum_volatility', 5)
                binance_app.minimum_volume = exchange_config.get('minimum_volume', 20000)
                binance_app.volume_threshold = exchange_config.get('volume_threshold', 20000)
                binance_app.minimum_quote_price = exchange_config.get('minimum_quote_price', 0.0000001)
                binance_app.selection_score = exchange_config.get('selection_score', 10)
                binance_app.tv_screener_ratings = [rating.upper() for rating in exchange_config.get('tv_screener_ratings', ['STRONG_BUY'])]
                exchanges_loaded.append(binance_app)
            elif ex == CryptoExchange.COINBASEPRO:
                coinbase_app = PyCryptoBot(exchange=ex)
                coinbase_app.public_api = CPublicAPI()
                coinbase_app.scanner_quote_currencies = exchange_config.get('quote_currency', ['USDT'])
                coinbase_app.granularity = Granularity(Granularity.convert_to_enum(int(exchange_config.get('granularity', '3600'))))
                coinbase_app.adx_threshold = exchange_config.get('adx_threshold', 25)
                coinbase_app.volatility_threshold = exchange_config.get('volatility_threshold', 9)
                coinbase_app.minimum_volatility = exchange_config.get('minimum_volatility', 5)
                coinbase_app.minimum_volume = exchange_config.get('minimum_volume', 20000)
                coinbase_app.volume_threshold = exchange_config.get('volume_threshold', 20000)
                coinbase_app.minimum_quote_price = exchange_config.get('minimum_quote_price', 0.0000001)
                coinbase_app.selection_score = exchange_config.get('selection_score', 10)
                coinbase_app.tv_screener_ratings = [rating.upper() for rating in exchange_config.get('tv_screener_ratings', ['STRONG_BUY'])]
                exchanges_loaded.append(coinbase_app)
            elif ex == CryptoExchange.KUCOIN:
                kucoin_app = PyCryptoBot(exchange=ex)
                kucoin_app.public_api = KPublicAPI(bot_config[ex.value]["api_url"])
                kucoin_app.scanner_quote_currencies = exchange_config.get('quote_currency', ['USDT'])
                kucoin_app.granularity = Granularity(Granularity.convert_to_enum(exchange_config.get('granularity', '1h')))
                kucoin_app.adx_threshold = exchange_config.get('adx_threshold', 25)
                kucoin_app.volatility_threshold = exchange_config.get('volatility_threshold', 9)
                kucoin_app.minimum_volatility = exchange_config.get('minimum_volatility', 5)
                kucoin_app.minimum_volume = exchange_config.get('minimum_volume', 20000)
                kucoin_app.volume_threshold = exchange_config.get('volume_threshold', 20000)
                kucoin_app.minimum_quote_price = exchange_config.get('minimum_quote_price', 0.0000001)
                kucoin_app.selection_score = exchange_config.get('selection_score', 10)
                kucoin_app.tv_screener_ratings = [rating.upper() for rating in exchange_config.get('tv_screener_ratings', ['STRONG_BUY'])]
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

def process_screener_data(app, markets, quote_currency, exchange_name):
    """
    Hit TradingView up for the goods so we don't waste unnecessary time/compute resources (brandon's top picks)
    """
    # Do you want it to spit out all the debug stuff?
    debug = False

    ta_screener_list = [f"{re.sub('PRO', '', app.exchange.name, re.IGNORECASE)}:{re.sub('-', '', market)}" for market in markets]
    
    screener_staging = [p for p in chunker(ta_screener_list, 100)]
    screener_analysis = []
    additional_indicators = ["ATR", "KltChnl.upper", "KltChnl.lower"]
    #TradingView.indicators.append("Volatility.D")

    for pair_list in screener_staging:
        screener_analysis.extend([a for a in get_multiple_analysis(screener='crypto', interval=app.granularity.short, symbols=pair_list, additional_indicators=additional_indicators).values()])
    
    # Take what we need and do magic, ditch the rest.
    formatted_ta = []
    for ta in screener_analysis:
        try:
            if debug : print(f"Checking {ta.symbol} on {exchange_name}\n")
            recommend = Decimal(ta.indicators.get('Recommend.All'))
            volatility = Decimal(volatility_calculator(ta.indicators['BB.upper'], ta.indicators['BB.lower'], ta.indicators['KltChnl.upper'], ta.indicators['KltChnl.lower'], ta.indicators['high'], ta.indicators['low']))
            #volatility = Decimal(ta.indicators['Volatility.D']) * 100
            adx = abs(Decimal(ta.indicators['ADX']))
            adx_posi_di = Decimal(ta.indicators['ADX+DI'])
            adx_neg_di = Decimal(ta.indicators['ADX-DI'])
            high = Decimal(ta.indicators['high']).quantize(Decimal('1e-{}'.format(8)))
            low = Decimal(ta.indicators['low']).quantize(Decimal('1e-{}'.format(8)))
            close = Decimal(ta.indicators['close']).quantize(Decimal('1e-{}'.format(8)))            
            # ATR normalised
            atr = (Decimal(ta.indicators['ATR']) / close * 100).quantize(Decimal('1e-{}'.format(2))) if "ATR" in ta.indicators else 0
            volume = Decimal(ta.indicators['volume'])
            macd = Decimal(ta.indicators['MACD.macd'])
            macd_signal = Decimal(ta.indicators['MACD.signal'])
            bollinger_upper = Decimal(ta.indicators['BB.upper'])
            bollinger_lower = Decimal(ta.indicators['BB.lower'])
            kelt_upper = Decimal(ta.indicators['KltChnl.upper'])
            kelt_lower = Decimal(ta.indicators['KltChnl.lower'])
            rsi = Decimal(ta.indicators.get('RSI', 0))
            stoch_d = Decimal(ta.indicators.get('Stoch.D', 0))
            stoch_k = Decimal(ta.indicators.get('Stoch.K', 0))
            williams_r = Decimal(ta.indicators.get('W.R', 0))
            score = 0
            analysis_summary = ta.summary
            rating = ta.summary["RECOMMENDATION"]
            #print(close)
            if rating == "SELL":
                score -= 2.5
            elif rating == "STRONG_SELL":
                score -= 5
            elif rating == "NEUTRAL":
                score += 0
            elif rating == "BUY":
                score += 2.5
            elif rating == "STRONG_BUY":
                score += 5        
            if (adx >= app.adx_threshold) and (adx_posi_di > adx_neg_di) and (adx_posi_di > adx):
                if debug : print(f"ADX({adx}) >= {app.adx_threshold}")
                score += 1 
            if volume >= app.volume_threshold:
                if debug : print(f"Volume({volume}) >= {app.volume_threshold}")
                score += 1
            if abs(macd) > abs(macd_signal):
                if debug : print(f"MACD({macd}) above signal({macd_signal})")
                score += 1
            if volatility >= app.volatility_threshold:
                if debug : print(f"Volatility({volatility} is above {app.volatility_threshold}")
                score += 1
            if volatility < app.minimum_volatility:
                if debug : print(f"{ta.symbol} ({volatility}) is below min volatility of {app.minimum_volatility}")
                score -= 100
            if volume < app.minimum_volume:
                if debug : print(f"{ta.symbol} ({volume}) is below min volume of {app.volume}")
                score -= 100
            if close < app.minimum_quote_price:
                if debug : print(f"{ta.symbol} ({close}) is below min quote price of {app.minimum_quote_price}")
                score -= 100
            if 30 >= rsi > 20:
                score += 1
            if 20 < stoch_d <= 30:
                score += 1
            if stoch_k > stoch_d:
                score += 1
            if williams_r <= -30:
                score += 1
            #print('symbol\tscore\tvolume\tvvolatilith\tadx\tadx_posi_di\tadx_neg_di\tmacd\tmacd_signal\tbollinger_upper\tbollinger_lower\trecommend')
            #print(ta.symbol, score, volume, volatility, adx, adx_posi_di, adx_neg_di, macd, macd_signal, bollinger_upper, bollinger_lower, recommend, "\n")
            #print(f"Symbol: {ta.symbol} Score: {score}/{app.selection_score} Rating: {rating}")
            if (score >= app.selection_score) and (rating in app.tv_screener_ratings):
                relavent_ta = {}
                if app.exchange == CryptoExchange.COINBASEPRO or app.exchange == CryptoExchange.KUCOIN:
                    relavent_ta['market'] = re.sub(rf'(.*){quote_currency}', rf'\1-{quote_currency}', ta.symbol)
                    #relavent_ta['market'] = re.sub(quote_currency,f"-{quote_currency}", ta.symbol)
                else:
                    relavent_ta['market'] = ta.symbol
                #relavent_ta['market'] = ta.symbol
                relavent_ta['recommend'] = recommend
                relavent_ta['volume'] = volume
                relavent_ta['volatility'] = volatility
                relavent_ta['adx'] = adx
                relavent_ta['adx+di'] = adx_posi_di
                relavent_ta['adx-di'] = adx_neg_di
                relavent_ta['macd'] = macd
                relavent_ta['macd.signal'] = macd_signal
                relavent_ta['bollinger_upper'] = bollinger_upper
                relavent_ta['bollinger_lower'] = bollinger_lower
                relavent_ta['rsi'] = rsi
                relavent_ta['stoch_d'] = stoch_d
                relavent_ta['stoch_k'] = stoch_k
                relavent_ta['williamsR'] = williams_r
                relavent_ta['rating'] = rating
                relavent_ta['score'] = score
                ## Hack a percentage from the recommendation which would take into account all the indicators rather than just ATR
                if atr > 0:
                    relavent_ta['atr72_pcnt'] = atr
                #else:
                #    if recommend > 0:
                #        relavent_ta['atr72_pcnt'] = recommend * 100
                else:
                    relavent_ta['atr72_pcnt'] = 0

                try:
                    relavent_ta['buy_next'] = 'SEND IT!' if re.search('BUY', rating) else False
                except AttributeError:
                    relavent_ta['buy_next'] = False
                formatted_ta.append(relavent_ta)
        except Exception as e:
            pass
    if formatted_ta:
        # Stick it in a DF for the bots
        df_markets = pd.DataFrame(formatted_ta)
        df_markets = df_markets[["market", "score", "recommend", "volume", "volatility", "adx", "adx+di", "adx-di", "macd", "macd.signal", "bollinger_upper", "bollinger_lower", "rsi", "stoch_d", "stoch_k", "williamsR", "rating", "buy_next", "atr72_pcnt"]]
        df_markets.columns = ["market", "score", "recommend", "volume", "volatility", "adx", "adx+di", "adx-di", "macd", "macd.signal", "bollinger_upper", "bollinger_lower", "rsi", "stoch_d", "stoch_k", "williamsR", "rating", "buy_next", "atr72_pcnt"]
        df_markets["score"] = df_markets["score"].astype(float).round(0).astype(int)
        df_markets["recommend"] = df_markets["recommend"].astype(float)
        df_markets["volume"] = df_markets["volume"].astype(float).round(0).astype(int)
        df_markets["volatility"] = df_markets["volatility"].astype(float)
        df_markets["adx"] = df_markets["adx"].astype(float)
        df_markets["adx+di"] = df_markets["adx+di"].astype(float)
        df_markets["adx-di"] = df_markets["adx-di"].astype(float)
        df_markets["macd"] = df_markets["macd"].astype(float)
        df_markets["macd.signal"] = df_markets["macd.signal"].astype(float)
        df_markets["bollinger_upper"] = df_markets["bollinger_upper"].astype(float)
        df_markets["bollinger_lower"] = df_markets["bollinger_lower"].astype(float)
        df_markets['rsi'] = df_markets['rsi'].astype(float)
        df_markets['stoch_d'] = df_markets['stoch_d'].astype(float)
        df_markets['stoch_k'] = df_markets['stoch_k'].astype(float)
        df_markets['williamsR'] = df_markets['williamsR'].astype(float)
        df_markets['atr72_pcnt'] = df_markets['atr72_pcnt'].astype(float)

        df_markets.sort_values(by=["market"], ascending=True, inplace=True)
        df_markets.set_index("market", inplace=True)

        print(
            df_markets.sort_values(
                by=["buy_next", "atr72_pcnt"], ascending=[False, False], inplace=False
            )
        )
        TGBot(app, scanner=True).save_scanner_output(app.exchange.value, quote_currency, df_markets)
    else:
        blank_data = {}
        blank_data["buy_next"] = False
        blank_data["atr72_pcnt"] = 0
        blank_data["volume"] = 0
        formatted_ta.append(blank_data)

        df_markets = pd.DataFrame(formatted_ta)
        TGBot(app, scanner=True).save_scanner_output(app.exchange.value, quote_currency, df_markets)
        print('No pairs found!')

    return True


if  __name__ == '__main__':
    import time
    from datetime import datetime

    tvlib_ver = version('tradingview-ta')
    if tvlib_ver >= "3.2.10":
        print(f"Library is correct version - were good to go! (v {tvlib_ver})")
    else:
        print(f"Gotta update your tradingview-ta library please! (v {tvlib_ver})")
        sys.exit()

    start_time = time.time()
    print('Processing, please wait...')
    bootstrap_exchanges = load_configs()
    for app in bootstrap_exchanges:
        print(f"\n\n{app.exchange.name}")
        for quote_currency in app.scanner_quote_currencies:
            markets = get_markets(app, quote_currency)
            try:
                process_screener_data(app, markets, quote_currency, app.exchange.name)
            except Exception as e:
                print(e)

    print("Scan run finished!")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total elapsed time: {time.time() - start_time} sec")
