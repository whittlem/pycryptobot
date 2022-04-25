import time
import json
import pandas as pd

from models.PyCryptoBot import PyCryptoBot
from models.exchange import kucoin
from models.helper.TelegramBotHelper import TelegramBotHelper as TGBot
from models.Trading import TechnicalAnalysis
from models.exchange.binance import PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import PublicAPI as CPublicAPI
from models.exchange.kucoin import PublicAPI as KPublicAPI
from models.exchange.Granularity import Granularity
from models.exchange.ExchangesEnum import Exchange

GRANULARITY = Granularity(Granularity.ONE_HOUR)
try:
    with open("scanner.json", encoding='utf8') as json_file:
        config = json.load(json_file)
except IOError as err:
    print (err)

try:
    with open("config.json", encoding='utf8') as json_file:
        bot_config = json.load(json_file)
except IOError as err:
    print (err)

for exchange in config:
    ex = Exchange(exchange)
    app = PyCryptoBot(exchange=ex)
    for quote in config[ex.value]["quote_currency"]:
        if ex == Exchange.BINANCE:
            api = BPublicAPI(bot_config[ex.value]["api_url"])
        elif ex == Exchange.COINBASEPRO:
            api = CPublicAPI()
        elif ex == Exchange.KUCOIN:
            api = KPublicAPI(bot_config[ex.value]["api_url"])
        else:
            raise ValueError(f"Invalid exchange: {ex}")

        markets = []
        resp = api.getMarkets24HrStats()
        if ex == Exchange.BINANCE:
            for row in resp:
                if row["symbol"].endswith(quote):
                    markets.append(row)
        elif ex == Exchange.COINBASEPRO:
            for market in resp:
                if market.endswith(f"-{quote}"):
                    resp[market]["stats_24hour"]["market"] = market
                    markets.append(resp[market]["stats_24hour"])
        elif ex == Exchange.KUCOIN:
            results = resp["data"]["ticker"]
            for result in results:
                if result["symbol"].endswith(f"-{quote}"):
                    markets.append(result)


        df_markets = pd.DataFrame(markets)

        if ex == Exchange.BINANCE:
            df_markets = df_markets[["symbol", "lastPrice", "quoteVolume"]]
        elif ex == Exchange.COINBASEPRO:
            df_markets = df_markets[["market", "last", "volume"]]
        elif ex == Exchange.KUCOIN:
            df_markets = df_markets[["symbol", "last", "volValue"]]


        df_markets.columns = ["market", "price", "volume"]
        df_markets["price"] = df_markets["price"].astype(float)
        df_markets["volume"] = df_markets["volume"].astype(float).round(0).astype(int)
        df_markets.sort_values(by=["market"], ascending=True, inplace=True)
        df_markets.set_index("market", inplace=True)

        print("Processing, please wait...")

        ROW = 1
        for market, data in df_markets.T.iteritems():
            print(f"[{ROW}/{len(df_markets)}] {market} {round((ROW/len(df_markets))*100, 2)}%")
            try:
                if int(data["volume"]) > 0:
                    ta = TechnicalAnalysis(api.getHistoricalData(market, GRANULARITY, None))
                    ta.addEMA(12)
                    ta.addEMA(26)
                    ta.addATR(72)
                    df_1h = ta.getDataFrame()
                    df_1h["ema12ltema26"] = df_1h.ema12 < df_1h.ema26
                    df_1h_last = df_1h.tail(1)

                    # volatility over the last 72 hours
                    df_markets.at[market, "atr72"] = float(df_1h_last[["atr72"]].values[0][0])
                    df_markets["atr72_pcnt"] = (
                        df_markets["atr72"] / df_markets["price"] * 100
                    ).round(2)
                    df_markets.at[market, "buy_next"] = df_1h_last[df_1h_last["market"] == market][
                        "ema12ltema26"
                    ].values[0]
            except Exception as err:
                print(err)

            # don't flood exchange, sleep 1 second
            time.sleep(2)

            # current position
            ROW += 1

        # clear screen
        print(chr(27) + "[2J")
        # markets sorted by next buy action, then by most volatile

        print(
            df_markets.sort_values(
                by=["buy_next", "atr72_pcnt"], ascending=[False, False], inplace=False
            )
        )

        TGBot(app, scanner=True).save_scanner_output(ex.value, quote, df_markets)

