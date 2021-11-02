import sys
import time
import json
import pandas as pd
import os

from models.PyCryptoBot import PyCryptoBot
from models.helper.TelegramBotHelper import TelegramBotHelper as TGBot
from models.Trading import TechnicalAnalysis
from models.exchange.binance import PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import PublicAPI as CPublicAPI
from models.exchange.kucoin import PublicAPI as KPublicAPI

app = PyCryptoBot()
granularity = ""
try:
    with open("scanner.json") as json_file:
        config = json.load(json_file)
except IOError as err:
    print (err)

for ex in config:
    for quote in config[ex]["quote_currency"]:
        if ex == "binance":
            api = BPublicAPI()
            granularity = api.to_binance_granularity(3600)
        elif ex == "coinbasepro":
            api = CPublicAPI()
            granularity = api.to_coinbasepro_granularity(3600)
        elif ex:
            api = KPublicAPI()
            granularity = api.to_kucoin_granularity(3600)
        else:
            raise ValueError(f"Invalid exchange: {ex}")



        markets = []
        resp = api.getMarkets24HrStats()
        if ex == "binance":
            for row in resp:
                if row["symbol"].endswith(quote):
                    markets.append(row)
        elif ex == "coinbasepro":
            for market in resp:
                if market.endswith(f"-{quote}"):
                    resp[market]["stats_24hour"]["market"] = market
                    markets.append(resp[market]["stats_24hour"])
        elif ex == "kucoin":
            # TODO: getMarket24HrStats needs to be added to PublicAPI
            raise Exception("getMarket24HrStats needs to be added to PublicAPI")

        df_markets = pd.DataFrame(markets)

        if ex == "binance":
            df_markets = df_markets[["symbol", "lastPrice", "quoteVolume"]]
        elif ex == "coinbasepro":
            df_markets = df_markets[["market", "last", "volume"]]

        df_markets.columns = ["market", "price", "volume"]
        df_markets["price"] = df_markets["price"].astype(float)
        df_markets["volume"] = df_markets["volume"].astype(float).round(0).astype(int)
        df_markets.sort_values(by=["market"], ascending=True, inplace=True)
        df_markets.set_index("market", inplace=True)

        print("Processing, please wait...")

        row = 1
        for market, data in df_markets.T.iteritems():
            print(f"[{row}/{len(df_markets)}] {market} {round((row/len(df_markets))*100, 2)}%")
            try:
                if int(data["volume"]) > 0:
                    ta = TechnicalAnalysis(api.getHistoricalData(market, granularity, None))
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
            except:
                pass

            # don't flood exchange, sleep 1 second
            time.sleep(1)

            # current position
            row = row + 1

        # clear screen
        print(chr(27) + "[2J")
        # markets sorted by next buy action, then by most volatile
        print(
            df_markets.sort_values(
                by=["buy_next", "atr72_pcnt"], ascending=[False, False], inplace=False
            )
        )

        TGBot(app).save_scanner_output(ex, quote, df_markets.sort_values(
                by=["buy_next", "atr72_pcnt"], ascending=[False, False], inplace=False))

