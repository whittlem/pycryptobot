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

from models.telegram import TelegramControl, TelegramHelper, TelegramHandler, TelegramActions

scannerSchedule = BackgroundScheduler(timezone='UTC')

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

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

    def _read_data(self, name: str = "data.json") -> None:
        try:
            with open(
                os.path.join(self.datafolder, "telegram_data", name), "r", encoding="utf8"
            ) as json_file:
                self.data = json.load(json_file)
        except FileNotFoundError as err:
            logger.warning(err)

    def _write_data(self, name: str = "data.json") -> None:
        try:
            with open(
                os.path.join(self.datafolder, "telegram_data", name),
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.data, outfile, indent=4)
        except:
            with open(
                os.path.join(self.datafolder, "telegram_data", name),
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.data, outfile, indent=4)

    def _getoptions(self, callbacktag, state):
        buttons = []
        keyboard = []
        jsonfiles = os.listdir(os.path.join(self.datafolder, "telegram_data"))
        for file in jsonfiles:
            if (
                ".json" in file
                and not file == "data.json"
                and not file.__contains__("output.json")
            ):
                self._read_data(file)
                if callbacktag == "sell":
                    if "margin" in self.data:
                        if self.data["margin"] != " ":
                            buttons.append(
                                InlineKeyboardButton(
                                    file.replace(".json", ""),
                                    callback_data=callbacktag + "_" + file,
                                )
                            )
                elif callbacktag == "buy":
                    if "margin" in self.data:
                        if self.data["margin"] == " ":
                            buttons.append(
                                InlineKeyboardButton(
                                    file.replace(".json", ""),
                                    callback_data=callbacktag + "_" + file,
                                )
                            )
                else:
                    if "botcontrol" in self.data:
                        if self.data["botcontrol"]["status"] == state:
                            buttons.append(
                                InlineKeyboardButton(
                                    file.replace(".json", ""),
                                    callback_data=callbacktag + "_" + file,
                                )
                            )

        if len(buttons) > 0:
            if len(buttons) > 1:
                keyboard = [
                    [InlineKeyboardButton("All", callback_data=callbacktag + "_all")]
                ]

            i = 0
            while i <= len(buttons) - 1:
                if len(buttons) - 1 >= i + 2:
                    keyboard.append([buttons[i], buttons[i + 1], buttons[i + 2]])
                elif len(buttons) - 1 >= i + 1:
                    keyboard.append([buttons[i], buttons[i + 1]])
                else:
                    keyboard.append([buttons[i]])
                i += 3
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
        return keyboard

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
        self.atr72pcnt = 4.0
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

        if not os.path.exists(os.path.join(self.datafolder, "telegram_data")):
            os.mkdir(os.path.join(self.datafolder, "telegram_data"))

        if os.path.isfile(os.path.join(self.datafolder, "telegram_data", "data.json")):
            self._read_data()
            if "markets" not in self.data:
                self.data.update({"markets": {}})
                self._write_data()
            if "scannerexceptions" not in self.data:
                self.data.update({"scannerexceptions": {}})
                self._write_data()
        else:
            ds = {"trades": {}, "markets": {}, "scannerexceptions": {}}
            self.data = ds
            self._write_data()

        self.updater = Updater(
            self.token,
            use_context=True,
        )

        self.helper = TelegramHelper(self.datafolder, self.config, self.config_file)
        self.handler = TelegramHandler(self.datafolder, self.userid, self.helper)
        self.control = TelegramControl(self.datafolder, self.helper)
        self.actions = TelegramActions(self.datafolder, self.helper)
# 
#     def _getUptime(self, date: str):
#         now = str(datetime.now())
#         # If date passed from datetime.now() remove milliseconds
#         if date.find(".") != -1:
#             dt = date.split(".")[0]
#             date = dt
#         if now.find(".") != -1:
#             dt = now.split(".", maxsplit=1)[0]
#             now = dt
# 
#         now = now.replace("T", " ")
#         now = f"{now}"
#         # Add time in case only a date is passed in
#         # new_date_str = f"{date} 00:00:00" if len(date) == 10 else date
#         date = date.replace("T", " ") if date.find("T") != -1 else date
#         # Add time in case only a date is passed in
#         new_date_str = f"{date} 00:00:00" if len(date) == 10 else date
# 
#         started = datetime.strptime(new_date_str, "%Y-%m-%d %H:%M:%S")
#         now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
#         duration = now - started
#         duration_in_s = duration.total_seconds()
#         hours = divmod(duration_in_s, 3600)[0]
#         duration_in_s -= 3600 * hours
#         minutes = divmod(duration_in_s, 60)[0]
#         return f"{round(hours)}h {round(minutes)}m"

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

    def responses(self, update, context):

        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query
            
        if "delexcep_" in query.data:
            self.ExceptionRemoveCallBack(update, context)

        elif query.data == "cancel":
            query.edit_message_text("User Cancelled Request")

    # Define a few command handlers. These usually take the two arguments update and context.

    def setcommands(self, update, context) -> None:
        command = [
            BotCommand("controlPanel", "show command buttons"),
            BotCommand("cleandata", "clean JSON data files"),
            BotCommand("addexception", "add pair to scanner exception list"),
            BotCommand("removeexception", "remove pair from scanner exception list"),
            BotCommand("startscanner", "start auto scan high volume markets and start bots"),
            BotCommand("stopscanner", "stop auto scan high volume markets"),
            BotCommand("addnew", "add and start a new bot"),
            BotCommand("deletebot", "delete bot from startbot list"),
            BotCommand("margins", "show margins for all open trades"),
            BotCommand("trades", "show closed trades"),
            BotCommand("stats", "show exchange stats for market/pair"),
            BotCommand("help", "show help text"),
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
        helptext += "<b>/showinfo</b> - <i>display bot(s) status</i>\n"
        helptext += "<b>/showconfig</b> - <i>show config for exchange</i>\n\n"
        helptext += "<b>Interactive Command List</b>\n\n"
        helptext += "<b>/addnew</b> - <i>start the requested pair</i>\n"
        helptext += "<b>/pausebots</b> - <i>pause all or the selected bot</i>\n"
        helptext += "<b>/resumebots</b> - <i>resume paused bots</i>\n"
        helptext += "<b>/stopbots</b> - <i>stop all or the selected bots</i>\n"
        helptext += "<b>/startbots</b> - <i>start all or the selected bots</i>\n"
        helptext += "<b>/sell</b> - <i>sell market pair on next iteration</i>\n"
        helptext += "<b>/buy</b> - <i>buy market pair on next iteration</i>\n\n"
        helptext += "<b>Market Scanner Commands</b>\n\n"
        helptext += "<b>/startscanner</b> - <i>start auto scan high volume markets and start bots</i>\n"
        helptext += "<b>/stopscanner</b> - <i>stop auto scan high volume markets</i>\n"
        helptext += "<b>/addexception</b> - <i>add pair to scanner exception list</i>\n"
        helptext += "<b>/removeexception</b> - <i>remove pair from scanner exception list</i>\n"

        mbot = Telegram(self.token, str(context._chat_id_and_data[0]))

        mbot.send(helptext, parsemode="HTML")

    def showbotinfo(self, update, context) -> None:
        """Show running bot status"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.actions.getBotInfo(update)
        return

    def trades(self, update, context):
        """List trades"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self._read_data()

        output = ""
        for time in self.data["trades"]:
            output = ""
            output = output + f"<b>{self.data['trades'][time]['pair']}</b>\n{time}"
            output = (
                output
                + f"\n<i>Sold at: {self.data['trades'][time]['price']}   Margin: {self.data['trades'][time]['margin']}</i>\n"
            )

            if output != "":
                mbot = Telegram(self.token, str(context._chat_id_and_data[0]))
                mbot.send(output, parsemode="HTML")

    def marginrequest(self, update, context):
        if not self._checkifallowed(update.effective_user.id, update):
            return

        self.handler.askMarginType(update)
        return

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

        output = self.helper.startProcess(self.pair, self.exchange, "--stats", "telegram", True)

        update.message.reply_text(output, parse_mode="HTML")

        return ConversationHandler.END

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
            self._read_data()
            if "markets" in self.data:
                if not self.pair in self.data["markets"]:
                    self.data["markets"].update(
                        {
                            self.pair: {
                                "overrides": f"--exchange {self.exchange} --market {self.pair} {self.overrides}"
                            }
                        }
                    )
                    self._write_data()
                    update.message.reply_text(f"{self.pair} saved \u2705")
                else:
                    update.message.reply_text(
                        f"{self.pair} already setup, no changes made."
                    )
            else:
                self.data.update({"markets": {}})
                self.data["markets"].update(
                    {
                        self.pair: {
                            "overrides": f"--exchange {self.exchange} --market {self.pair} {self.overrides}"
                        }
                    }
                )
                self._write_data()
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
            update.message.reply_text("Command Complete, have a nice day.", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        if self.helper.startProcess(self.pair, self.exchange, self.overrides, startmethod) == False:
            update.message.reply_text(
                f"{self.pair} is already running, no action taken.",
                reply_markup=ReplyKeyboardRemove())
        else:
            if startmethod != "scanner":
                update.message.reply_text(f"{self.pair} crypto bot Starting", reply_markup=ReplyKeyboardRemove())

        update.message.reply_text("Command Complete, have a nice day.", reply_markup=ReplyKeyboardRemove())
        
        return ConversationHandler.END

    def error(self, update, context):
        """Log Errors"""

        try:
            if "HTTPError" in context.error.args[0]: 
                while self.checkconnection() == False:
                    logger.warning("No internet connection found")
                    self.updater.start_polling(poll_interval=30)
                    sleep(30)
                self.updater.start_polling()
                return
            else:
                logger.error(msg="Exception while handling an update:", exc_info=context.error)
        except:
            pass

    def done(self, update, context):
        """added for conversations to end"""
        return ConversationHandler.END

    def deleterequest(self, update, context):
        """ask which bot to delete"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.control.askDeleteBotList(update)

    def checkconnection(self) -> bool:
        """internet connection check"""
        try:
            urllib.request.urlopen("https://api.telegram.org")
            return True
        except:
            print("No internet connection")
            return False

    def StartScanning(self,update,context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.handler._checkScheduledJob(update)
        self.actions.StartMarketScan(update, True if len(context.args) > 0 and context.args[0] == "debug" else False, False if len(context.args) > 0 and context.args[0] == "noscan" else True)

    def StopScanning(self,update,context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return
        self.handler._removeScheduledJob(update)

    def cleandata(self, update, context) -> None:
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        jsonfiles = os.listdir(os.path.join(self.datafolder, "telegram_data"))
        for i in range(len(jsonfiles), 0, -1):
            jfile = jsonfiles[i-1]
            if (
                ".json" in jfile
                and jfile != "data.json"
                and jfile.__contains__("output.json") == False
            ):
                logger.info("checking %s", jfile)
                self._read_data(jfile)
                last_modified = datetime.now() - datetime.fromtimestamp(
                    os.path.getmtime(
                        os.path.join(self.datafolder, "telegram_data", jfile)
                    )
                )                
                if "margin" not in self.data:
                    logger.info("deleting %s", jfile)
                    os.remove(os.path.join(self.datafolder, "telegram_data", jfile))
                    continue
                if (
                    self.data["botcontrol"]["status"] == "active"
                    and last_modified.seconds > 120
                    and (last_modified.seconds != 86399 and last_modified.days != -1)
                ):
                    logger.info("deleting %s %s", jfile, str(last_modified))
                    os.remove(os.path.join(self.datafolder, "telegram_data", jfile))
                    continue
                elif (
                    self.data["botcontrol"]["status"] == "exit"
                    and last_modified.seconds > 120
                    and last_modified.seconds != 86399
                ):
                    logger.info("deleting %s %s", jfile, str(last_modified.seconds))
                    os.remove(os.path.join(self.datafolder, "telegram_data", jfile))

        self.showbotinfo(update, context)
        update.message.reply_text("Operation Complete")

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

        self._read_data()

        if "scannerexceptions" not in self.data:
            self.data.update({"scannerexceptions": {}})

        if not self.pair in self.data["scannerexceptions"]:
            self.data["scannerexceptions"].update({self.pair : {}})
            self._write_data()
            update.message.reply_text(f"{self.pair} Added to Scanner Exception List \u2705", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text(f"{self.pair} Already on exception list", reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END

    def ExceptionRemove(self, update, context):
        """ask which bot to delete"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = []
        keyboard = []

        self._read_data()
        for pair in self.data["scannerexceptions"]:
            buttons.append(
                InlineKeyboardButton(pair, callback_data="delexcep_" + pair)
            )

        if len(buttons) > 0:
            i = 0
            while i <= len(buttons) - 1:
                if len(buttons) - 1 >= i + 2:
                    keyboard.append([buttons[i], buttons[i + 1], buttons[i + 2]])
                elif len(buttons) - 1 >= i + 1:
                    keyboard.append([buttons[i], buttons[i + 1]])
                else:
                    keyboard.append([buttons[i]])
                i += 3
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            "<b>What do you want to remove from the scanner exception list?</b>",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    def ExceptionRemoveCallBack(self, update, context):
        """delete selected bot"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self._read_data()

        query = update.callback_query

        self.data["scannerexceptions"].pop(str(query.data).replace("delexcep_", ""))

        self._write_data()

        query.edit_message_text(
            f"<i>Removed {str(query.data).replace('delexcep_', '')} from exception list. bot</i>",
            parse_mode="HTML",
        )

    def RestartBots(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return None

        self.control.askRestartBot(update)

#     def GetActiveBotList(self):
# 
#         return self.helper.getActiveBotList(self.datafolder)

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

    def UpdateBuyMaxSize(self, update, context):

        # t = models.helper.UpdateConfigHelper.UpdateConfigFile(context.args)


        self._read_data("config.json")

        with open(os.path.join(self.config_file), "r", encoding="utf8") as json_file:
            self.config = json.load(json_file)

        if len(context.args) > 0:
            for ex in self.config:
                if ex in ("coinbasepro", "binance", "kucoin"):
                    self.config[ex]["config"].update({"buymaxsize": context.args[0]})

        with open(os.path.join(self.config_file), "w", encoding="utf8") as outfile:
                json.dump(self.config, outfile, indent=4)

        update.message.reply_text("Config Updated")

    def Request(self, update, context):

        userid = context._user_id_and_data[0]
        
        if self._checkifallowed(userid, update):
            key_markup = self.handler.getRequest()
            update.message.reply_text(
                "<b>Choose a command.</b>",
                reply_markup=key_markup,
                parse_mode="HTML",
            )

    def ExitBot(self, update, context):
        # self.updater.stop()
        # self.updater.dispatcher.stop()
        os._exit(0)

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
    # dp.add_handler(CommandHandler("buy", botconfig.buyrequest, Filters.text))
    # dp.add_handler(CommandHandler("sell", botconfig.sellrequest, Filters.text))
    dp.add_handler(CommandHandler("deletebot", botconfig.deleterequest, Filters.text))

    dp.add_handler(CommandHandler("startscanner", botconfig.StartScanning, Filters.text))
    dp.add_handler(CommandHandler("stopscanner", botconfig.StopScanning, Filters.text))

    dp.add_handler(CommandHandler("cleandata", botconfig.cleandata, Filters.text))

    dp.add_handler(CommandHandler("removeexception", botconfig.ExceptionRemove, Filters.text))

    dp.add_handler(CommandHandler("restart", botconfig.RestartBots))

    dp.add_handler(CommandHandler("reopen", botconfig.StartOpenOrderBots))

    dp.add_handler(CommandHandler("exit", botconfig.ExitBot))
    # dp.add_handler(CommandHandler("updatebuymax", botconfig.UpdateBuyMaxSize))
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

    dp.add_handler(conversation_stats)
    dp.add_handler(conversation_newbot)
    dp.add_handler(conversation_exception)
    # log all errors
    dp.add_error_handler(botconfig.error)

    # while botconfig.checkconnection() is False:
    #     sleep(10)

    # Start the Bot
    botconfig.updater.start_polling()

    # Run the bot until you press Ctrl-C
    # since start_polling() is non-blocking and will stop the bot gracefully.
    botconfig.updater.idle()


if __name__ == "__main__":
    main()
