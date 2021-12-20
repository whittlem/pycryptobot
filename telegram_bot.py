#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bot to reply to Telegram messages.

Usage:
Press Ctrl-C on the command line or send a signal to the process to stop the bot.
"""
import argparse
import logging
import os
import json
import subprocess
import sys
import re
import urllib.request

from datetime import datetime
from time import sleep, time

# from pandas.core.frame import DataFrame
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.bot import Bot, BotCommand
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    Filters,
    ConversationHandler,
    MessageHandler,
)
from telegram.replykeyboardremove import ReplyKeyboardRemove
from apscheduler.schedulers.background import BackgroundScheduler
from models.chat import Telegram

from models.telegram import (
    TelegramControl,
    TelegramHelper,
    TelegramHandler,
    TelegramActions,
    ConfigEditor,
)

scannerSchedule = BackgroundScheduler(timezone="UTC")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

# TYPING_RESPONSE = 1
CHOOSING, TYPING_REPLY = range(2)
EXCHANGE, MARKET, ANYOVERRIDES, OVERRIDES, SAVE, START = range(6)
EXCEPT_EXCHANGE, EXCEPT_MARKET = range(2)

reply_keyboard = [["Coinbase Pro", "Binance", "Kucoin"]]

markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


class TelegramBotBase:
    """
    base level for telegram bot
    """

    userid = ""
    datafolder = os.curdir
    data = {}

    helper = None
    handler = None
    editor = None

    def _checkifallowed(self, userid, update) -> bool:
        if str(userid) != self.userid:
            update.message.reply_text("<b>Not authorised!</b>", parse_mode="HTML")
            return False

        return True


class TelegramBot(TelegramBotBase):
    """
    main telegram bot class
    """

    def __init__(self):
        self.token = ""
        self.config_file = ""

        self.cl_args = ""
        self.market = ""

        self.exchange = ""
        self.pair = ""
        self.overrides = ""

        parser = argparse.ArgumentParser(description="PyCryptoBot Telegram Bot")
        parser.add_argument(
            "--config",
            type=str,
            dest="config_file",
            help="pycryptobot config file",
            default="config.json",
        )
        parser.add_argument(
            "--datafolder",
            type=str,
            help="Use the datafolder at the given location, useful for multi bots running in different folders",
            default="",
        )

        args = parser.parse_args()

        self.config_file = args.config_file

        with open(os.path.join(self.config_file), "r", encoding="utf8") as json_file:
            self.config = json.load(json_file)

        self.token = self.config["telegram"]["token"]
        self.userid = self.config["telegram"]["user_id"]

        # Config section for bot pair scanner
        self.atr72pcnt = 2.0
        self.enableleverage = False
        self.maxbotcount = 0
        self.autoscandelay = 0
        self.enable_buy_next = True
        self.autostart = False
        if "scanner" in self.config:
            self.atr72pcnt = (
                self.config["scanner"]["atr72_pcnt"]
                if "atr72_pcnt" in self.config["scanner"]
                else self.atr72pcnt
            )
            self.enableleverage = (
                self.config["scanner"]["enableleverage"]
                if "enableleverage" in self.config["scanner"]
                else self.enableleverage
            )
            self.maxbotcount = (
                self.config["scanner"]["maxbotcount"]
                if "maxbotcount" in self.config["scanner"]
                else self.maxbotcount
            )
            self.autoscandelay = (
                self.config["scanner"]["autoscandelay"]
                if "autoscandelay" in self.config["scanner"]
                else 0
            )
            self.enable_buy_next = (
                self.config["scanner"]["enable_buy_next"]
                if "enable_buy_next" in self.config["scanner"]
                else True
            )

            # self.autostart = (
            #     self.config["scanner"]["autostart"]
            #     if "autostart" in self.config["scanner"]
            #     else True
            # )

        if "datafolder" in self.config["telegram"]:
            self.datafolder = self.config["telegram"]["datafolder"]

        if args.datafolder != "":
            self.datafolder = args.datafolder

        self.helper = TelegramHelper(self.datafolder, self.config, self.config_file)

        if not os.path.exists(os.path.join(self.datafolder, "telegram_data")):
            os.mkdir(os.path.join(self.datafolder, "telegram_data"))

        if os.path.isfile(os.path.join(self.datafolder, "telegram_data", "data.json")):
            self.helper.read_data()
            if "markets" not in self.helper.data:
                self.helper.data.update({"markets": {}})
                self.helper.write_data()
            if "scannerexceptions" not in self.helper.data:
                self.helper.data.update({"scannerexceptions": {}})
                self.helper.write_data()
        else:
            ds = {"trades": {}, "markets": {}, "scannerexceptions": {}}
            self.helper.data = ds
            self.helper.write_data()

        self.updater = Updater(
            self.token,
            use_context=True,
        )

        self.handler = TelegramHandler(self.datafolder, self.userid, self.helper)
        self.control = TelegramControl(self.datafolder, self.helper)
        self.actions = TelegramActions(self.datafolder, self.helper)
        self.editor = ConfigEditor(self.datafolder, self.helper)

    def _question_which_exchange(self, update):
        """start new bot ask which exchange"""

        self.exchange = ""
        self.overrides = ""

        update.message.reply_text("Select the exchange:", reply_markup=markup)

    def _answer_which_exchange(self, update) -> bool:
        """start bot validate exchange and ask which market/pair"""
        if update.message.text.lower() == "cancel":
            update.message.reply_text(
                "Operation Cancelled", reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if (
            update.message.text == "Coinbase Pro"
            or update.message.text == "Kucoin"
            or update.message.text == "Binance"
        ):
            self.exchange = update.message.text.lower()
            if update.message.text == "Coinbase Pro":
                self.exchange = "coinbasepro"
        else:
            if self.exchange == "":
                update.message.reply_text("Invalid Exchange Entered!")
                # self.newbot_request(update, context)
                return False

        return True

    def _question_which_pair(self, update):

        self.market = ""

        update.message.reply_text(
            "Which market/pair is this for?", reply_markup=ReplyKeyboardRemove()
        )

    def _answer_which_pair(self, update) -> bool:
        if update.message.text.lower() == "cancel":
            update.message.reply_text(
                "Operation Cancelled", reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if self.exchange in ("coinbasepro", "kucoin"):
            p = re.compile(r"^[1-9A-Z]{2,9}\-[1-9A-Z]{2,5}$")
            if not p.match(update.message.text):
                update.message.reply_text(
                    "Invalid market format", reply_markup=ReplyKeyboardRemove()
                )
                # self.newbot_exchange(update, context)
                return False
        elif self.exchange == "binance":
            p = re.compile(r"^[A-Z0-9]{5,13}$")
            if not p.match(update.message.text):
                update.message.reply_text(
                    "Invalid market format.", reply_markup=ReplyKeyboardRemove()
                )
                # self.newbot_exchange(update, context)
                return False

        self.pair = update.message.text

        return True

    # Define command handlers. These usually take the two arguments update and context.

    def setcommands(self, update, context) -> None:
        command = [
            BotCommand("controlpanel", "show command buttons"),
            BotCommand("cleandata", "clean JSON data files"),
            BotCommand("addexception", "add pair to scanner exception list"),
            BotCommand("removeexception", "remove pair from scanner exception list"),
            BotCommand(
                "startscanner", "start auto scan high volume markets and start bots"
            ),
            BotCommand("stopscanner", "stop auto scan high volume markets"),
            BotCommand("addnew", "add and start a new bot"),
            BotCommand("deletebot", "delete bot from startbot list"),
            BotCommand("margins", "show margins for all open trades"),
            BotCommand("trades", "show closed trades"),
            BotCommand("stats", "show exchange stats for market/pair"),
            BotCommand("help", "show help text")
            # BotCommand("showinfo", "show all running bots status"),
            # BotCommand("showconfig", "show config for selected exchange"),
            # BotCommand("startbots", "start all or selected bot"),
            # BotCommand("stopbots", "stop all or the selected bot"),
            # BotCommand("pausebots", "pause all or selected bot"),
            # BotCommand("resumebots", "resume paused bots"),
            # BotCommand("buy", "manual buy"),
            # BotCommand("sell", "manual sell"),
        ]

        ubot = Bot(self.token)
        ubot.set_my_commands(command)

        update.message.reply_text(
            "<i>Bot Commands Created</i>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )

    def help(self, update, context):
        """Send a message when the command /help is issued."""

        helptext = "<b>Information Command List</b>\n\n"
        helptext += (
            "<b>/setcommands</b> - <i>add all commands to bot for easy access</i>\n"
        )
        helptext += "<b>/margins</b> - <i>show margins for open trade</i>\n"
        helptext += "<b>/trades</b> - <i>show closed trades</i>\n"
        helptext += "<b>/stats</b> - <i>display stats for market</i>\n"
        # helptext += "<b>/showinfo</b> - <i>display bot(s) status</i>\n"
        # helptext += "<b>/showconfig</b> - <i>show config for exchange</i>\n\n"
        helptext += "<b>Interactive Command List</b>\n\n"
        helptext += "<b>/controlpanel</b> - <i>show interactive control buttons</i>\n"
        helptext += "<b>/cleandata</b> - <i>check and remove any bad Json files</i>\n"
        helptext += "<b>/addnew</b> - <i>start the requested pair</i>\n"
        # helptext += "<b>/pausebots</b> - <i>pause all or the selected bot</i>\n"
        # helptext += "<b>/resumebots</b> - <i>resume paused bots</i>\n"
        # helptext += "<b>/stopbots</b> - <i>stop all or the selected bots</i>\n"
        # helptext += "<b>/startbots</b> - <i>start all or the selected bots</i>\n"
        # helptext += "<b>/sell</b> - <i>sell market pair on next iteration</i>\n"
        # helptext += "<b>/buy</b> - <i>buy market pair on next iteration</i>\n\n"
        helptext += "<b>Market Scanner Commands</b>\n\n"
        helptext += "<b>/startscanner</b> - <i>start auto scan high volume markets and start bots</i>\n"
        helptext += "<b>/stopscanner</b> - <i>stop auto scan high volume markets</i>\n"
        helptext += "<b>/addexception</b> - <i>add pair to scanner exception list</i>\n"
        helptext += (
            "<b>/removeexception</b> - <i>remove pair from scanner exception list</i>\n"
        )

        mbot = Telegram(self.token, str(context._chat_id_and_data[0]))

        mbot.send(helptext, parsemode="HTML")

    def trades(self, update, context):
        """List trades"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.helper.read_data()

        output = ""
        for time in self.helper.data["trades"]:
            output = ""
            output = (
                output + f"<b>{self.helper.data['trades'][time]['pair']}</b>\n{time}"
            )
            output = (
                output
                + f"\n<i>Sold at: {self.helper.data['trades'][time]['price']}   Margin: {self.helper.data['trades'][time]['margin']}</i>\n"
            )

            if output != "":
                mbot = Telegram(self.token, str(context._chat_id_and_data[0]))
                mbot.send(output, parsemode="HTML")

    def statsrequest(self, update: Updater, context):
        """Ask which exchange stats are wanted for"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return None

        update.message.reply_text("Select the exchange", reply_markup=markup)

        return CHOOSING

    def stats_exchange_received(self, update, context):
        """Ask which market stats are wanted for"""
        if update.message.text.lower() == "done":
            return None

        if update.message.text.lower() == "cancel":
            update.message.reply_text(
                "Operation Cancelled", reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if update.message.text in ("Coinbase Pro", "Kucoin", "Binance"):
            self.exchange = update.message.text.lower()
            if update.message.text == "Coinbase Pro":
                self.exchange = "coinbasepro"
        else:
            if self.exchange == "":
                update.message.reply_text("Invalid Exchange Entered!")
                self.statsrequest(update, context)
                return None

        update.message.reply_text(
            "Which market/pair do you want stats for?",
            reply_markup=ReplyKeyboardRemove(),
        )

        return TYPING_REPLY

    def stats_pair_received(self, update, context):
        """Show stats for selected exchange and market"""
        if update.message.text.lower() == "done":
            return None

        if update.message.text.lower() == "cancel":
            update.message.reply_text(
                "Operation Cancelled", reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if self.exchange == "coinbasepro" or self.exchange == "kucoin":
            p = re.compile(r"^[1-9A-Z]{2,5}\-[1-9A-Z]{2,5}$")
            if not p.match(update.message.text):
                update.message.reply_text(
                    "Invalid market format", reply_markup=ReplyKeyboardRemove()
                )
                self.stats_exchange_received(update, context)
                return None
        elif self.exchange == "binance":
            p = re.compile(r"^[A-Z0-9]{5,12}$")
            if not p.match(update.message.text):
                update.message.reply_text(
                    "Invalid market format.", reply_markup=ReplyKeyboardRemove()
                )
                self.stats_exchange_received(update, context)
                return None

        self.pair = update.message.text

        update.message.reply_text(
            "<i>Gathering Stats, please wait...</i>", parse_mode="HTML"
        )

        output = self.helper.startProcess(
            self.pair, self.exchange, "--stats", "telegram", True
        )

        update.message.reply_text(output, parse_mode="HTML")

        return ConversationHandler.END

    def newbot_request(self, update: Updater, context):
        """start new bot ask which exchange"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return None

        self._question_which_exchange(update)

        return EXCHANGE

    def newbot_exchange(self, update, context):
        """start bot validate exchange and ask which market/pair"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return None

        if not self._answer_which_exchange(update):
            self.newbot_request(update, context)

        self._question_which_pair(update)

        return ANYOVERRIDES

    def newbot_any_overrides(self, update, context) -> None:
        """start bot validate market and ask if overrides required"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return None

        if not self._answer_which_pair(update):
            self.newbot_exchange(update, context)
            return None

        r_keyboard = [["Yes", "No"]]

        mark_up = ReplyKeyboardMarkup(r_keyboard, one_time_keyboard=True)

        update.message.reply_text(
            "Do you want to use any commandline overrides?", reply_markup=mark_up
        )

        return MARKET

    def newbot_market(self, update, context):
        """start bot - ask for overrides if none required ask to save bot"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return None

        if update.message.text == "No":
            reply_keyboard = [["Yes", "No"]]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            update.message.reply_text("Do you want to save this?", reply_markup=markup)
            return SAVE

        update.message.reply_text(
            "Tell me any other commandline overrides to use?",
            reply_markup=ReplyKeyboardRemove(),
        )

        return OVERRIDES

    def newbot_overrides(self, update, context):
        """start bot - ask to save bot"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return None

        # Telegram desktop client can auto replace -- with a single long dash
        # this converts it back to --
        self.overrides = update.message.text.replace(
            b"\xe2\x80\x94".decode("utf-8"), "--"
        )

        reply_keyboard = [["Yes", "No"]]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text("Do you want to save this?", reply_markup=markup)

        return SAVE

    def newbot_save(self, update, context):
        """start bot - save if required ask if want to start"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return None

        if update.message.text == "Yes":
            self.helper.read_data()
            if "markets" in self.helper.data:
                if not self.pair in self.helper.data["markets"]:
                    self.helper.data["markets"].update(
                        {
                            self.pair: {
                                "overrides": f"--exchange {self.exchange} --market {self.pair} {self.overrides}"
                            }
                        }
                    )
                    self.helper.write_data()
                    update.message.reply_text(f"{self.pair} saved \u2705")
                else:
                    update.message.reply_text(
                        f"{self.pair} already setup, no changes made."
                    )
            else:
                self.helper.data.update({"markets": {}})
                self.helper.data["markets"].update(
                    {
                        self.pair: {
                            "overrides": f"--exchange {self.exchange} --market {self.pair} {self.overrides}"
                        }
                    }
                )
                self.helper.write_data()
                update.message.reply_text(f"{self.pair} saved")

        reply_keyboard = [["Yes", "No"]]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text("Do you want to start this bot?", reply_markup=markup)

        return START

    def newbot_start(self, update, context, startmethod: str = "telegram") -> None:
        """start bot - start bot if want"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return None

        if update.message.text == "No":
            update.message.reply_text(
                "Command Complete, have a nice day.", reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if (
            self.helper.startProcess(
                self.pair, self.exchange, self.overrides, startmethod
            )
            == False
        ):
            update.message.reply_text(
                f"{self.pair} is already running, no action taken.",
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            if startmethod != "scanner":
                update.message.reply_text(
                    f"{self.pair} crypto bot Starting",
                    reply_markup=ReplyKeyboardRemove(),
                )

        update.message.reply_text(
            "Command Complete, have a nice day.", reply_markup=ReplyKeyboardRemove()
        )

        return ConversationHandler.END

    def error(self, update, context):
        """Log Errors"""
        logger.error(msg="Exception while handling an update:", exc_info=context.error)
        try:
            if "HTTPError" in context.error.args[0]:
                while self.checkconnection() == False:
                    logger.warning("No internet connection found")
                    self.updater.start_polling(poll_interval=30)
                    sleep(30)
                self.updater.start_polling()
                return
            # else:
            # logger.error(msg="Exception while handling an update:", exc_info=context.error)
        except:
            pass

    def done(self, update, context):
        """added for conversations to end"""
        return ConversationHandler.END

    def checkconnection(self) -> bool:
        """internet connection check"""
        try:
            urllib.request.urlopen("https://api.telegram.org")
            return True
        except:
            print("No internet connection")
            return False

    def _cleandata(self):
        jsonfiles = self.helper.getActiveBotList()
        for i in range(len(jsonfiles), 0, -1):
            jfile = jsonfiles[i - 1]

            logger.info("checking %s", jfile)

            while self.helper.read_data(jfile) == False:
                sleep(0.2)

            last_modified = datetime.now() - datetime.fromtimestamp(
                os.path.getmtime(
                    os.path.join(self.datafolder, "telegram_data", f"{jfile}.json")
                )
            )
            if "margin" not in self.helper.data:
                logger.info("deleting %s", jfile)
                os.remove(os.path.join(self.datafolder, "telegram_data", f"{jfile}.json"))
                continue
            if (
                self.helper.data["botcontrol"]["status"] == "active"
                and last_modified.seconds > 120
                and (last_modified.seconds != 86399 and last_modified.days != -1)
            ):
                logger.info("deleting %s %s", jfile, str(last_modified))
                os.remove(
                    os.path.join(self.datafolder, "telegram_data", f"{jfile}.json")
                )
                continue
            elif (
                self.helper.data["botcontrol"]["status"] == "exit"
                and last_modified.seconds > 120
                and last_modified.seconds != 86399
            ):
                logger.info("deleting %s %s", jfile, str(last_modified.seconds))
                os.remove(os.path.join(self.datafolder, "telegram_data", f"{jfile}.json"))

    def ExceptionExchange(self, update, context):
        """start new bot ask which exchange"""
        self._question_which_exchange(update)

        return EXCEPT_EXCHANGE

    def ExceptionPair(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self._answer_which_exchange(update)

        self._question_which_pair(update)

        return EXCEPT_MARKET

    def ExceptionAdd(self, update, context):
        """start bot - save if required ask if want to start"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return None

        self._answer_which_pair(update)

        self.helper.read_data()

        if "scannerexceptions" not in self.helper.data:
            self.helper.data.update({"scannerexceptions": {}})

        if not self.pair in self.helper.data["scannerexceptions"]:
            self.helper.data["scannerexceptions"].update({self.pair: {}})
            self.helper.write_data()
            update.message.reply_text(
                f"{self.pair} Added to Scanner Exception List \u2705",
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            update.message.reply_text(
                f"{self.pair} Already on exception list",
                reply_markup=ReplyKeyboardRemove(),
            )

        return ConversationHandler.END

    def ExceptionRemove(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.control.askExceptionBotList(update)
        return

    def marginrequest(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.handler.askMarginType(update)
        return

    def showbotinfo(self, update, context) -> None:
        """Show running bot status"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.actions.getBotInfo(update)
        return

    def sellrequest(self, update, context):
        """Manual sell request (asks which coin to sell)"""
        self.control.askSellBotList(update)
        return

    def buyrequest(self, update, context):
        """Manual buy request (asks which coin to buy)"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.control.askBuyBotList(update)
        return

    def showconfigrequest(self, update, context):
        """display config settings (ask which exchange)"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.handler.askConfigOptions(update)
        return

    def pausebotrequest(self, update, context) -> None:
        """Ask which bots to pause"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.control.askPauseBotList(update)

    def restartbotrequest(self, update, context) -> None:
        """Ask which bot to restart"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.control.askResumeBotList(update)

    def startallbotsrequest(self, update, context) -> None:
        """Ask which bot to start from start list (or all)"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.control.askStartBotList(update)
        return

    def stopbotrequest(self, update, context) -> None:
        """ask which active bots to stop (or all)"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.control.askStopBotList(update)
        return

    def deleterequest(self, update, context):
        """ask which bot to delete"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.control.askDeleteBotList(update)

    def StartScanning(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.handler._checkScheduledJob(update)
        self.actions.StartMarketScan(
            update,
            False if len(context.args) > 0 and context.args[0] == "debug" else True,
            False if len(context.args) > 0 and context.args[0] == "noscan" else True,
        )

    def StopScanning(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return
        self.handler._removeScheduledJob(update)

    def cleandata(self, update, context) -> None:
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self._cleandata

        self.actions.getBotInfo(update)
        update.message.reply_text("Operation Complete")

    def RestartBots(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return None

        self.control.askRestartBotList(update)

    def StartOpenOrderBots(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return None

        self.actions.startOpenOrders(update)

    def statstwo(self, update, context):

        jsonfiles = os.listdir(os.path.join(self.datafolder, "telegram_data"))
        for file in jsonfiles:
            exchange = "coinbasepro"
            if file.__contains__("output.json"):
                if file.__contains__("coinbasepro"):
                    exchange = "coinbasepro"
                if file.__contains__("binance"):
                    exchange = "binance"
                if file.__contains__("kucoin"):
                    exchange = "kucoin"

                update.message.reply_text(
                    "<i>Gathering Stats, please wait...</i>", parse_mode="HTML"
                )

                with open(
                    os.path.join(self.datafolder, "telegram_data", file),
                    "r",
                    encoding="utf8",
                ) as json_file:
                    data = json.load(json_file)

                pairs = ""
                count = 0
                for pair in data:
                    if pair.__contains__("DOWN") or pair.__contains__("UP"):
                        continue

                    # count += 1
                    pairs = pairs + pair + " "

                output = subprocess.getoutput(
                    f"python3 pycryptobot.py --stats --exchange {exchange}  --statgroup {pairs}  "
                )
                update.message.reply_text(output, parse_mode="HTML")
                sleep(30)
                update.message.reply_text("Pausing before next set", parse_mode="HTML")

    #     def UpdateBuyMaxSize(self, update, context):
    #
    #         self.helper.read_data("config.json")
    #
    #         with open(os.path.join(self.config_file), "r", encoding="utf8") as json_file:
    #             self.config = json.load(json_file)
    #
    #         if len(context.args) > 0:
    #             for ex in self.config:
    #                 if ex in ("coinbasepro", "binance", "kucoin"):
    #                     self.config[ex]["config"].update({"buymaxsize": context.args[0]})
    #
    #         with open(os.path.join(self.config_file), "w", encoding="utf8") as outfile:
    #                 json.dump(self.config, outfile, indent=4)
    #
    #         update.message.reply_text("Config Updated")

    def Request(self, update, context):

        userid = context._user_id_and_data[0]

        if self._checkifallowed(userid, update):
            key_markup = self.handler.getRequest()
            update.message.reply_text(
                "<b>PyCryptoBot Command Panel.</b>",
                reply_markup=key_markup,
                parse_mode="HTML",
            )

    # def ExitBot(self, update, context):
    # self.updater.stop()
    # self.updater.dispatcher.stop()
    # os._exit(0)


def main():
    """Start the bot."""
    # Create telegram bot configuration
    botconfig = TelegramBot()

    # Get the dispatcher to register handlers
    dp = botconfig.updater.dispatcher

    # Information commands
    dp.add_handler(CommandHandler("help", botconfig.help))
    dp.add_handler(CommandHandler("margins", botconfig.marginrequest, Filters.all))
    dp.add_handler(CommandHandler("trades", botconfig.trades, Filters.text))
    dp.add_handler(
        CommandHandler("showconfig", botconfig.showconfigrequest, Filters.text)
    )
    # dp.add_handler(CommandHandler("showinfo", botconfig.showbotinfo, Filters.text))

    # General Action Command
    dp.add_handler(CommandHandler("setcommands", botconfig.setcommands))
    dp.add_handler(CommandHandler("buy", botconfig.buyrequest, Filters.text))
    dp.add_handler(CommandHandler("sell", botconfig.sellrequest, Filters.text))
    dp.add_handler(CommandHandler("pausebots", botconfig.pausebotrequest, Filters.text))
    dp.add_handler(
        CommandHandler("resumebots", botconfig.restartbotrequest, Filters.text)
    )
    dp.add_handler(CommandHandler("startbots", botconfig.startallbotsrequest))
    dp.add_handler(CommandHandler("stopbots", botconfig.stopbotrequest))
    dp.add_handler(CommandHandler("deletebot", botconfig.deleterequest, Filters.text))

    dp.add_handler(
        CommandHandler("startscanner", botconfig.StartScanning, Filters.text)
    )
    dp.add_handler(CommandHandler("stopscanner", botconfig.StopScanning, Filters.text))

    dp.add_handler(CommandHandler("cleandata", botconfig.cleandata, Filters.text))

    dp.add_handler(
        CommandHandler("removeexception", botconfig.ExceptionRemove, Filters.text)
    )

    dp.add_handler(CommandHandler("restart", botconfig.RestartBots))

    dp.add_handler(CommandHandler("reopen", botconfig.StartOpenOrderBots))

    # dp.add_handler(CommandHandler("exit", botconfig.ExitBot))

    dp.add_handler(CommandHandler("statsgroup", botconfig.statstwo))
    # Response to Question handler
    dp.add_handler(CallbackQueryHandler(botconfig.handler.getResponse))

    dp.add_handler(CommandHandler("controlPanel", botconfig.Request))

    conversation_exception = ConversationHandler(
        entry_points=[CommandHandler("addexception", botconfig.ExceptionExchange)],
        states={
            EXCEPT_EXCHANGE: [
                MessageHandler(
                    Filters.text, botconfig.ExceptionPair, pass_user_data=True
                )
            ],
            EXCEPT_MARKET: [
                MessageHandler(
                    Filters.text, botconfig.ExceptionAdd, pass_user_data=True
                )
            ],
        },
        fallbacks=[("Done", botconfig.done)],
    )

    conversation_stats = ConversationHandler(
        entry_points=[CommandHandler("stats", botconfig.statsrequest)],
        states={
            CHOOSING: [
                MessageHandler(
                    Filters.text, botconfig.stats_exchange_received, pass_user_data=True
                )
            ],
            TYPING_REPLY: [
                MessageHandler(
                    Filters.text, botconfig.stats_pair_received, pass_user_data=True
                )
            ],
        },
        fallbacks=[("Done", botconfig.done)],
    )

    conversation_newbot = ConversationHandler(
        entry_points=[CommandHandler("addnew", botconfig.newbot_request)],
        states={
            EXCHANGE: [MessageHandler(Filters.text, botconfig.newbot_exchange)],
            MARKET: [MessageHandler(Filters.text, botconfig.newbot_market)],
            ANYOVERRIDES: [
                MessageHandler(Filters.text, botconfig.newbot_any_overrides)
            ],
            OVERRIDES: [MessageHandler(Filters.text, botconfig.newbot_overrides)],
            SAVE: [MessageHandler(Filters.text, botconfig.newbot_save)],
            START: [MessageHandler(Filters.text, botconfig.newbot_start)],
        },
        fallbacks=[("Done", botconfig.done)],
    )

    # conversation_stats = ConversationHandler(entry_points=[CommandHandler("buymax", botconfig.editor.ask_buy_max_size)],
    #     states={
    #         TYPING_RESPONSE: [
    #             MessageHandler(
    #                 Filters.text, botconfig.editor.buy_max_size
    #             )],
    #     },
    #     fallbacks=[("Done", botconfig.done)],
    # )
    # CallbackQueryHandler(botconfig.editor.ask_buy_max_size)
    # dp.add_handler(botconfig.editor.get_conversation_handler())

    dp.add_handler(conversation_stats)
    dp.add_handler(conversation_newbot)
    dp.add_handler(conversation_exception)
    # log all errors
    dp.add_error_handler(botconfig.error)

    botconfig._cleandata()

    # while botconfig.checkconnection() is False:
    #     sleep(10)

    # Start the Bot
    botconfig.updater.start_polling()

    # Run the bot until you press Ctrl-C
    # since start_polling() is non-blocking and will stop the bot gracefully.
    botconfig.updater.idle()


if __name__ == "__main__":
    main()
