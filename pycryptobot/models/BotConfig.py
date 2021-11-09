from ..core.version import get_version
from cement import App as CementApp

import argparse
import json
import os
import re
import sys

import yaml
from yaml.constructor import ConstructorError
from yaml.scanner import ScannerError

from pycryptobot.models.ConfigBuilder import ConfigBuilder
from pycryptobot.models.chat import Telegram
from pycryptobot.models.config import (
    binanceConfigParser,
    coinbaseProConfigParser,
    kucoinConfigParser,
    dummyConfigParser,
    loggerConfigParser,
)
from pycryptobot.models.helper.LogHelper import Logger
from pycryptobot.models.exchange.ExchangesEnum import Exchange


class BotConfig:
    def __init__(self, app: CementApp, exchange: str):
        self.cli_args = app.pargs
        self.configbuilder = False
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
        self.nosellminpcnt = None
        self.nosellmaxpcnt = None
        self.trailing_stop_loss = None
        self.trailing_stop_loss_trigger = 0
        self.sell_at_loss = 1
        self.smart_switch = 1
        self.telegram = False
        self.telegramdatafolder = ""
        self.logbuysellinjson = False
        self.buypercent = 100
        self.sellpercent = 100
        self.last_action = None
        self._chat_client = None
        self.buymaxsize = None

        self.sellatresistance = False
        self.autorestart = False
        self.stats = False
        self.statgroup = None
        self.statstartdate = None
        self.statdetail = False
        self.nobuynearhighpcnt = 3
        self.simresultonly = False

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
        self.enableml = False
        self.websocket = False

        self.enableinsufficientfundslogging = False
        self.insufficientfunds = False
        self.enabletelegrambotcontrol = False

        self.filelog = True
        self.logfile = self.cli_args.logfile
        self.fileloglevel = "DEBUG"
        self.consolelog = True
        self.consoleloglevel = "INFO"

        self.ema1226_15m_cache = None
        self.ema1226_1h_cache = None
        self.ema1226_6h_cache = None
        self.sma50200_1h_cache = None

        self.sim_smartswitch = False

        self.recv_window = self._set_recv_window()

        # self.config_file = kwargs.get("config_file", "config.json") //TODO: get rid of it
        self.config_file = "config.json"

        self.tradesfile = (
            self.cli_args.tradesfile if self.cli_args.tradesfile else "trades.csv"
        )

        self.config_provided = True
        self.config = app.config.get_dict()

        # set exchange platform
        self.exchange = self._set_exchange(exchange)

        # set defaults
        (
            self.api_url,
            self.api_key,
            self.api_secret,
            self.api_passphrase,
            self.market,
        ) = self._set_default_api_info(self.exchange)

        if self.config_provided:
            if self.exchange == Exchange.COINBASEPRO.value and "coinbasepro" in self.config:
                coinbaseProConfigParser(self, self.config["coinbasepro"], self.cli_args)

            elif self.exchange == Exchange.BINANCE.value and "binance" in self.config:
                binanceConfigParser(self, self.config["binance"], self.cli_args)

            elif self.exchange == Exchange.KUCOIN.value and "kucoin" in self.config:
                kucoinConfigParser(self, self.config["kucoin"], self.cli_args)

            elif self.exchange == Exchange.DUMMY.value and "dummy" in self.config:
                dummyConfigParser(self, self.config["dummy"], self.cli_args)

            if (
                    not self.disabletelegram
                    and "telegram" in self.config
                    and "token" in self.config["telegram"]
                    and "client_id" in self.config["telegram"]
            ):
                telegram = self.config["telegram"]
                self._chat_client = Telegram(telegram["token"], telegram["client_id"])
                if "datafolder" in self.config["telegram"]:
                    self.telegramdatafolder = telegram["datafolder"]
                self.telegram = True

            if "logger" in self.config:
                loggerConfigParser(self, self.config["logger"])

            if self.disablelog:
                self.filelog = 0
                self.fileloglevel = "NOTSET"
                self.logfile == "/dev/null"

        else:
            if self.exchange == Exchange.BINANCE.value:
                binanceConfigParser(self, None, self.cli_args)
            elif self.exchange == Exchange.KUCOIN.value:
                kucoinConfigParser(self, None, self.cli_args)
            else:
                coinbaseProConfigParser(self, None, self.cli_args)

            self.filelog = 0
            self.fileloglevel = "NOTSET"
            self.logfile == "/dev/null"

        Logger.configure(
            filelog=self.filelog,
            logfile=self.logfile,
            fileloglevel=self.fileloglevel,
            consolelog=self.consolelog,
            consoleloglevel=self.consoleloglevel,
        )

    def _set_exchange(self, exchange: str = None) -> str:
        valid_exchanges = ["coinbasepro", "binance", "kucoin", "dummy"]

        if self.cli_args.exchange is not None:
            exchange = self.cli_args.exchange

        if exchange and exchange in valid_exchanges:
            return exchange

        if not exchange:
            if ("coinbasepro" or "api_pass") in self.config:
                exchange = "coinbasepro"
            elif "binance" in self.config:
                exchange = "binance"
            elif "kucoin" in self.config:
                exchange = "kucoin"
            else:
                exchange = "dummy"

        if exchange not in valid_exchanges:
            raise TypeError(
                f"Invalid exchange: {exchange}. Valid choices: {valid_exchanges}"
            )
        return exchange

    def _set_default_api_info(self, exchange: str = "dummy") -> tuple:
        conf = {
            "binance": {
                "api_url": "https://api.binance.com",
                "api_key": "0000000000000000000000000000000000000000000000000000000000000000",
                "api_secret": "0000000000000000000000000000000000000000000000000000000000000000",
                "api_passphrase": "",
                "market": "BTCGBP",
            },
            "coinbasepro": {
                "api_url": "https://api.pro.coinbase.com",
                "api_key": "00000000000000000000000000000000",
                "api_secret": "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000==",
                "api_passphrase": "00000000000",
                "market": "BTC-GBP",
            },
            "kucoin": {
                "api_url": "https://api.kucoin.com",
                "api_key": "00000000000000000000000000000000",
                "api_secret": "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000==",
                "api_passphrase": "00000000000",
                "market": "BTC-GBP",
            },
            "dummy": {
                "api_url": "https://api.pro.coinbase.com",
                "api_key": "00000000000000000000000000000000",
                "api_secret": "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000==",
                "api_passphrase": "00000000000",
                "market": "BTC-GBP",
            },
        }
        return (
            conf[exchange]["api_url"],
            conf[exchange]["api_key"],
            conf[exchange]["api_secret"],
            conf[exchange]["api_passphrase"],
            conf[exchange]["market"],
        )

    def getVersionFromREADME(self) -> str:
        return get_version()

    def _set_recv_window(self):
        recv_window = 5000
        if self.cli_args.recvWindow and isinstance(self.cli_args.recvWindow, int):
            if 5000 <= int(self.cli_args.recvWindow) <= 60000:
                recv_window = int(self.cli_args.recvWindow)
            else:
                raise ValueError(
                    "recvWindow out of bounds! Should be between 5000 and 60000."
                )
        return recv_window
