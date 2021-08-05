import argparse
import json
import math
import os
import random
import re
import sys
from datetime import datetime, timedelta
from typing import Union

import pandas as pd
import urllib3
import yaml
from urllib3.exceptions import ReadTimeoutError
from yaml.constructor import ConstructorError
from yaml.scanner import ScannerError

from models.chat import Telegram
from models.config import (
    binanceConfigParser,
    binanceParseMarket,
    coinbaseProConfigParser,
    coinbaseProParseMarket,
    dummyConfigParser,
    dummyParseMarket,
    loggerConfigParser,
)
from models.ConfigBuilder import ConfigBuilder
from models.exchange.binance import AuthAPI as BAuthAPI
from models.exchange.binance import PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import AuthAPI as CBAuthAPI
from models.exchange.coinbase_pro import PublicAPI as CBPublicAPI
from models.helper.LogHelper import Logger
from models.Trading import TechnicalAnalysis

# disable insecure ssl warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def parse_arguments():
    # instantiate the arguments parser
    parser = argparse.ArgumentParser(
        description="Python Crypto Bot using the Coinbase Pro or Binanace API"
    )

    # config builder
    parser.add_argument(
        "--init", action="store_true", help="config.json configuration builder"
    )

    # optional arguments
    parser.add_argument(
        "--exchange", type=str, help="'coinbasepro', 'binance', 'dummy'"
    )
    parser.add_argument(
        "--granularity",
        type=str,
        help="coinbasepro: (60,300,900,3600,21600,86400), binance: (1m,5m,15m,1h,6h,1d)",
    )
    parser.add_argument(
        "--graphs", type=int, help="save graphs=1, do not save graphs=0"
    )
    parser.add_argument("--live", type=int, help="live=1, test=0")
    parser.add_argument(
        "--market", type=str, help="coinbasepro: BTC-GBP, binance: BTCGBP etc."
    )
    parser.add_argument(
        "--sellatloss", type=int, help="toggle if bot should sell at a loss"
    )
    parser.add_argument(
        "--sellupperpcnt", type=float, help="optionally set sell upper percent limit"
    )
    parser.add_argument(
        "--selllowerpcnt", type=float, help="optionally set sell lower percent limit"
    )
    parser.add_argument(
        "--trailingstoploss",
        type=float,
        help="optionally set a trailing stop percent loss below last buy high",
    )
    parser.add_argument(
        "--sim", type=str, help="simulation modes: fast, fast-sample, slow-sample"
    )
    parser.add_argument(
        "--simstartdate",
        type=str,
        help="start date for sample simulation e.g '2021-01-15'",
    )
    parser.add_argument(
        "--simenddate",
        type=str,
        help="end date for sample simulation e.g '2021-01-15' or 'now'",
    )
    parser.add_argument(
        "--smartswitch",
        type=int,
        help="optionally smart switch between 1 hour and 15 minute intervals",
    )
    parser.add_argument(
        "--verbose", type=int, help="verbose output=1, minimal output=0"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Use the config file at the given location. e.g 'myconfig.json'",
    )
    parser.add_argument(
        "--logfile",
        type=str,
        help="Use the log file at the given location. e.g 'mymarket.log'",
    )
    parser.add_argument(
        "--buypercent", type=int, help="percentage of quote currency to buy"
    )
    parser.add_argument(
        "--sellpercent", type=int, help="percentage of base currency to sell"
    )
    parser.add_argument(
        "--lastaction", type=str, help="optionally set the last action (BUY, SELL)"
    )
    parser.add_argument("--buymaxsize", type=float, help="maximum size on buy")

    # optional options
    parser.add_argument(
        "--sellatresistance",
        action="store_true",
        help="sell at resistance or upper fibonacci band",
    )
    parser.add_argument(
        "--autorestart",
        action="store_true",
        help="Auto restart the bot in case of exception",
    )
    parser.add_argument(
        "--stats", action="store_true", help="display summary of completed trades"
    )
    parser.add_argument(
        "--statgroup", nargs="+", help="add multiple currency pairs to merge stats"
    )
    parser.add_argument(
        "--statstartdate",
        type=str,
        help="trades before this date are ignored in stats function e.g 2021-01-15",
    )
    parser.add_argument(
        "--statdetail",
        action="store_true",
        help="display detail of completed transactions for a given market",
    )

    # disable defaults
    parser.add_argument(
        "--disablebullonly",
        action="store_true",
        help="disable only buying in bull market",
    )
    parser.add_argument(
        "--disablebuynearhigh",
        action="store_true",
        help="disable buy within 5 percent of high",
    )
    parser.add_argument(
        "--disablebuymacd", action="store_true", help="disable macd buy signal"
    )
    parser.add_argument(
        "--disablebuyema", action="store_true", help="disable ema buy signal"
    )
    parser.add_argument(
        "--disablebuyobv", action="store_true", help="disable obv buy signal"
    )
    parser.add_argument(
        "--disablebuyelderray", action="store_true", help="disable elder ray buy signal"
    )
    parser.add_argument(
        "--disablefailsafefibonaccilow",
        action="store_true",
        help="disable failsafe sell on fibonacci lower band",
    )
    parser.add_argument(
        "--disablefailsafelowerpcnt",
        action="store_true",
        help="disable failsafe sell on 'selllowerpcnt'",
    )
    parser.add_argument(
        "--disableprofitbankupperpcnt",
        action="store_true",
        help="disable profit bank on 'sellupperpcnt'",
    )
    parser.add_argument(
        "--disableprofitbankreversal",
        action="store_true",
        help="disable profit bank on strong candlestick reversal",
    )
    parser.add_argument(
        "--disabletelegram", action="store_true", help="disable telegram messages"
    )
    parser.add_argument(
        "--disablelog", action="store_true", help="disable pycryptobot.log"
    )
    parser.add_argument(
        "--disabletracker", action="store_true", help="disable tracker.csv"
    )

    # parse arguments

    # pylint: disable=unused-variable
    args, unknown = parser.parse_known_args()
    return vars(args)


class Config:
    def __init__(self, *args, **kwargs):
        self.cli_args = parse_arguments()

        self.granularity = 3600
        self.base_currency = "BTC"
        self.quote_currency = "GBP"
        self.is_live = 0
        self.is_verbose = 0
        self.save_graphs = 0
        self.is_sim = 0
        self.simstartdate = None
        self.simenddate = None
        self.sim_speed = "fast"
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
        self.buymaxsize = None

        self.configbuilder = False

        self.sellatresistance = False
        self.autorestart = False
        self.stats = False
        self.statgroup = None
        self.statstartdate = None
        self.statdetail = False

        self.disablebullonly = False
        self.disablebuynearhigh = False
        self.disablebuymacd = False
        self.disablebuyema = False
        self.disablebuyobv = False
        self.disablebuyelderray = False
        self.disablefailsafefibonaccilow = False
        self.disablefailsafelowerpcnt = False
        self.disableprofitbankupperpcnt = False
        self.disableprofitbankreversal = False
        self.disabletelegram = False
        self.disablelog = False
        self.disabletracker = False

        self.filelog = True
        self.logfile = (
            self.cli_args["logfile"] if self.cli_args["logfile"] else "pycryptobot.log"
        )
        self.fileloglevel = "DEBUG"
        self.consolelog = True
        self.consoleloglevel = "INFO"

        self.ema1226_15m_cache = None
        self.ema1226_1h_cache = None
        self.ema1226_6h_cache = None
        self.sma50200_1h_cache = None

        self.sim_smartswitch = False

        Logger.configure(
            filelog=self.filelog,
            logfile=self.logfile,
            fileloglevel=self.fileloglevel,
            consolelog=self.consolelog,
            consoleloglevel=self.consoleloglevel,
        )

        self.config_file = kwargs.get("config_file", "config.json")
        self.config_provided = False

        if self.cli_args["init"]:
            # config builder
            cb = ConfigBuilder()
            cb.init()
            sys.exit()

        if self.cli_args["config"] is not None:
            self.config_file = self.cli_args["config"]
            self.config_provided = True

        if self.config_file == "config.json" and not os.path.isfile(self.config_file):
            self.is_live = 0  # no config will prevent live mode

        if os.path.isfile(self.config_file):
            self.config_provided = True
            try:
                with open(self.config_file, "r") as stream:
                    config = yaml.safe_load(stream)

            except (ScannerError, ConstructorError) as err:
                sys.tracebacklimit = 0
                raise ValueError(
                    f"Invalid config: cannot parse config file: {str(err)}"
                )

            except (IOError, FileNotFoundError) as err:
                sys.tracebacklimit = 0
                raise ValueError(f"Invalid config: cannot open config file: {str(err)}")

            except ValueError as err:
                sys.tracebacklimit = 0
                raise ValueError("Invalid config: " + str(err))

            except:
                raise

        # set exchange platform
        self.exchange = kwargs["exchange"]
        self.valid_exchanges = ["coinbasepro", "binance", "dummy"]
        if self.exchange and self.exchange in self.valid_exchanges:
            pass
        if not self.exchange:
            if ("coinbasepro" or "api_pass") in config:
                self.exchange = "coinbasepro"
            elif "binance" in config:
                self.exchange = "binance"
            else:
                self.exchange = "dummy"

        if self.cli_args["exchange"] is not None:
            self.exchange = self.cli_args["exchange"]

        if self.exchange not in self.valid_exchanges:
            raise TypeError(
                f"Invalid exchange: {self.exchange}. Valid choices: {self.valid_exchanges}"
            )

        if self.exchange == "binance":  # default for binance (test mode)
            self.api_key = (
                "0000000000000000000000000000000000000000000000000000000000000000"
            )
            self.api_secret = (
                "0000000000000000000000000000000000000000000000000000000000000000"
            )
            self.api_url = "https://api.binance.com"
            self.market = "BTCGBP"

        elif self.exchange == "coinbasepro":  # default for coinbase pro (test mode)
            self.api_key = "00000000000000000000000000000000"
            self.api_secret = "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000=="
            self.api_passphrase = "00000000000"
            self.api_url = "https://api.pro.coinbase.com"
            self.market = "BTC-GBP"

        else:  # default/dummy uses coinbase data (test mode)
            self.api_key = '00000000000000000000000000000000"'
            self.api_secret = "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000=="
            self.api_passphrase = "00000000000"
            self.api_url = "https://api.pro.coinbase.com"
            self.market = "BTC-GBP"

        if self.config_provided:
            if self.exchange == "coinbasepro" and "coinbasepro" in config:
                coinbaseProConfigParser(self, config["coinbasepro"], self.cli_args)

            elif self.exchange == "binance" and "binance" in config:
                binanceConfigParser(self, config["binance"], self.cli_args)

            elif self.exchange == "dummy" and "dummy" in config:
                dummyConfigParser(self, config["dummy"], self.cli_args)

            if (
                not self.disabletelegram
                and "telegram" in config
                and "token" in config["telegram"]
                and "client_id" in config["telegram"]
            ):
                telegram = config["telegram"]
                self._chat_client = Telegram(telegram["token"], telegram["client_id"])
                self.telegram = True

            if "logger" in config:
                loggerConfigParser(self, config["logger"])

            if self.disablelog:
                self.filelog = 0
                self.fileloglevel = "NOTSET"
                self.logfile == "/dev/null"

        else:
            if self.exchange == "binance":
                binanceConfigParser(self, None, self.cli_args)
            elif self.exchange == "coinbasepro":
                coinbaseProConfigParser(self, None, self.cli_args)

            self.filelog = 0
            self.fileloglevel = "NOTSET"
            self.logfile == "/dev/null"
