import ast
import json
import os.path
import re
import sys

from .default_parser import is_currency_valid, default_config_parse, merge_config_and_args


def is_market_valid(market) -> bool:
    if market is None:
        return False

    p = re.compile(r"^[0-9A-Z]{4,25}$")
    if p.match(market):
        return True
    p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
    if p.match(market):
        return True
    return False


def parse_market(market):
    base_currency = "BTC"
    quote_currency = "GBP"

    if not is_market_valid(market):
        raise ValueError(f"Binance market invalid: {market}")

    quote_currencies = [
        "BTC",
        "BNB",
        "ETH",
        "USDT",
        "TUSD",
        "DAX",
        "NGN",
        "RUB",
        "TRY",
        "EUR",
        "GBP",
        "ZAR",
        "UAH",
        "DAI",
        "BIDR",
        "AUD",
        "USD",
        "NGN",
        "BRL",
        "BVND",
        "VAI",
    ]

    for qc in quote_currencies:
        if market.endswith(qc):
            base_currency = market.replace(qc, "")
            quote_currency = qc
            break

    if len(market) != len(base_currency) + len(quote_currency):
        raise ValueError("Binance market error.")

    return market, base_currency, quote_currency


def parser(app, binance_config, args={}):
    if not app:
        raise Exception("No app is passed")

    if isinstance(binance_config, dict):
        if "api_key" in binance_config or "api_secret" in binance_config:
            print(">>> migrating api keys to binance.key <<<\n")

            # create 'binance.key'
            fh = open("binance.key", "w")
            fh.write(f"{binance_config['api_key']}\n{binance_config['api_secret']}")
            fh.close()

            if os.path.isfile("config.json") and os.path.isfile("binance.key"):
                binance_config["api_key_file"] = binance_config.pop("api_key")
                binance_config["api_key_file"] = "binance.key"
                del binance_config["api_secret"]

                # read 'binance' element from config.json
                fh = open("config.json", "r")
                config_json = ast.literal_eval(fh.read())
                config_json["binance"] = binance_config
                fh.close()

                # write new 'binance' element
                fh = open("config.json", "w")
                fh.write(json.dumps(config_json, indent=4))
                fh.close()
            else:
                print("migration failed (io error)\n")

        app.api_key_file = "binance.key"
        if "api_key_file" in args and args["api_key_file"] is not None:
            app.api_key_file = args["api_key_file"]
        elif "api_key_file" in binance_config:
            app.api_key_file = binance_config["api_key_file"]

        if app.api_key_file is not None:
            if not os.path.isfile(app.api_key_file):
                try:
                    raise Exception(f"Unable to read {app.api_key_file}, please check the file exists and is readable. Remove it from the config file for test mode!\n")
                except Exception as e:
                    print(f"{type(e).__name__}: {e}")
                    sys.exit(1)
            else:
                try:
                    with open(app.api_key_file, "r") as f:
                        key = f.readline().strip()
                        secret = f.readline().strip()
                    binance_config["api_key"] = key
                    binance_config["api_secret"] = secret
                except Exception:
                    raise RuntimeError(f"Unable to read {app.api_key_file}")

        if "api_key" in binance_config and "api_secret" in binance_config and "api_url" in binance_config:
            # validates the api key is syntactically correct
            p = re.compile(r"^[A-z0-9]{64,64}$")
            if not p.match(binance_config["api_key"]):
                raise TypeError("Binance API key is invalid")

            app.api_key = binance_config["api_key"]  # noqa: F841

            # validates the api secret is syntactically correct
            p = re.compile(r"^[A-z0-9]{64,64}$")
            if not p.match(binance_config["api_secret"]):
                raise TypeError("Binance API secret is invalid")

            app.api_secret = binance_config["api_secret"]  # noqa: F841

            valid_urls = [
                "https://api.binance.com/",
                "https://testnet.binance.vision/",
                "https://api.binance.com",
                "https://testnet.binance.vision",
                "https://api.binance.us",
            ]

            # validate Binance API
            if binance_config["api_url"] not in valid_urls:
                raise ValueError("Binance API URL is invalid")

            app.api_url = binance_config["api_url"]  # noqa: F841
            app.base_currency = "BTC"
            app.quote_currency = "GBP"
    else:
        binance_config = {}

    config = merge_config_and_args(binance_config, args)

    default_config_parse(app, config)

    if "base_currency" in config and config["base_currency"] is not None:
        if not is_currency_valid(config["base_currency"]):
            raise TypeError("Base currency is invalid.")
        app.base_currency = config["base_currency"]

    if "quote_currency" in config and config["quote_currency"] is not None:
        if not is_currency_valid(config["quote_currency"]):
            raise TypeError("Quote currency is invalid.")
        app.quote_currency = config["quote_currency"]

    if "market" in config and config["market"] is not None:
        app.market, app.base_currency, app.quote_currency = parse_market(config["market"])

    if app.base_currency != "" and app.quote_currency != "":
        app.market = app.base_currency + app.quote_currency  # noqa: F841

    if "use_sell_fee" in config:
        app.use_sell_fee = config["use_sell_fee"]  # noqa: F841
