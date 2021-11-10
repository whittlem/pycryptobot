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
import platform
import re
import urllib.request
from sched import scheduler

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

# from telegram.utils.helpers import DEFAULT_20
from models.chat import Telegram

s = BackgroundScheduler(timezone='UTC')
# jobId: Event

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

    def _read_data(self, name: str = "data.json") -> None:
        try:
            with open(
                os.path.join(self.datafolder, "telegram_data", name), "r", encoding="utf8"
            ) as json_file:
                self.data = json.load(json_file)
        except:
            pass

    def _write_data(self, name: str = "data.json") -> None:
        try:
            with open(
                os.path.join(self.datafolder, "telegram_data", name),
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.data, outfile, indent=4)
        except Exception as err:
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

    def _getUptime(self, date: str):
        now = str(datetime.now())
        # If date passed from datetime.now() remove milliseconds
        if date.find(".") != -1:
            dt = date.split(".")[0]
            date = dt
        if now.find(".") != -1:
            dt = now.split(".", maxsplit=1)[0]
            now = dt

        now = now.replace("T", " ")
        now = f"{now}"
        # Add time in case only a date is passed in
        # new_date_str = f"{date} 00:00:00" if len(date) == 10 else date
        date = date.replace("T", " ") if date.find("T") != -1 else date
        # Add time in case only a date is passed in
        new_date_str = f"{date} 00:00:00" if len(date) == 10 else date

        started = datetime.strptime(new_date_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        duration = now - started
        duration_in_s = duration.total_seconds()
        hours = divmod(duration_in_s, 3600)[0]
        duration_in_s -= 3600 * hours
        minutes = divmod(duration_in_s, 60)[0]
        return f"{round(hours)}h {round(minutes)}m"

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

        if query.data == "orders" or query.data == "pairs" or query.data == "allactive":
            self.marginresponse(update, context)

        elif query.data in ("binance", "coinbasepro", "kucoin"):
            self.showconfigresponse(update, context)

        elif "pause_" in query.data:
            self.pausebotresponse(update, context)

        elif "restart_" in query.data:
            self.restartbotresponse(update, context)

        elif "sell_" in query.data:
            self.sellresponse(update, context)

        elif "buy_" in query.data:
            self.buyresponse(update, context)

        elif "stop_" in query.data:
            self.stopbotresponse(update, context)

        elif "start_" in query.data:
            self.startallbotsresponse(update, context)

        elif "delete_" in query.data:
            self.deleteresponse(update, context)
            
        elif "delexcep_" in query.data:
            self.ExceptionRemoveCallBack(update, context)

        elif query.data == "cancel":
            query.edit_message_text("User Cancelled Request")

    # Define a few command handlers. These usually take the two arguments update and context.

    def setcommands(self, update, context) -> None:
        command = [
            BotCommand("help", "show help text"),
            BotCommand("margins", "show margins for all open trades"),
            BotCommand("trades", "show closed trades"),
            BotCommand("stats", "show exchange stats for market/pair"),
            BotCommand("showinfo", "show all running bots status"),
            BotCommand("showconfig", "show config for selected exchange"),
            BotCommand("addnew", "add and start a new bot"),
            BotCommand("deletebot", "delete bot from startbot list"),
            BotCommand("startbots", "start all or selected bot"),
            BotCommand("stopbots", "stop all or the selected bot"),
            BotCommand("pausebots", "pause all or selected bot"),
            BotCommand("resumebots", "resume paused bots"),
            BotCommand("buy", "manual buy"),
            BotCommand("sell", "manual sell"),
            BotCommand("addexception", "add pair to scanner exception list"),
            BotCommand("removeexception", "remove pair from scanner exception list"),
            BotCommand("startscanner", "start auto scan high volumne markets and start bots"),
            BotCommand("stopscanner", "stop auto scan high volumne markets")
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
        helptext += "<b>/buy</b> - <i>buy market pair on next iteration</i>\n"

        mbot = Telegram(self.token, str(context._chat_id_and_data[0]))

        mbot.send(helptext, parsemode="HTML")

    def showbotinfo(self, update, context) -> None:
        """Show running bot status"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        mbot = Telegram(self.token, str(context._chat_id_and_data[0]))

        jsonfiles = os.listdir(os.path.join(self.datafolder, "telegram_data"))
        output = ""
        bots = 0
        for file in jsonfiles:
            if (
                ".json" in file
                and not file == "data.json"
                and not file.__contains__("output.json")
            ):
                bots += 1
                output = ""
                self._read_data(file)
                output = output + f"\U0001F4C8 <b>{file.replace('.json', '')}</b> "

                last_modified = datetime.now() - datetime.fromtimestamp(
                    os.path.getmtime(
                        os.path.join(self.datafolder, "telegram_data", file)
                    )
                )
                # print(f"{file} {last_modified.seconds < 120} {last_modified} {last_modified.seconds}")

                if "margin" in self.data:
                    if (
                        self.data["botcontrol"]["status"] == "active"
                        and last_modified.seconds < 120
                        or last_modified.seconds == 86399
                    ):
                        output = (
                            output
                            + f" \U00002705 <b>Status</b>: <i>{self.data['botcontrol']['status']}</i> "
                        )
                    elif self.data["botcontrol"]["status"] == "paused":
                        output = (
                            output
                            + f" \U000023F8 <b>Status</b>: <i>{self.data['botcontrol']['status']}</i> "
                        )
                    elif self.data["botcontrol"]["status"] == "exit":
                        output = (
                            output
                            + f" \U0000274C <b>Status</b>: <i>{self.data['botcontrol']['status']}</i> "
                        )
                    elif last_modified.seconds > 90:
                        output = (
                            output + " \U0001F6D1	 <b>Status</b>: <i>defaulted</i> "
                        )
                else:
                    output = output + " \U0001F6D1	 <b>Status</b>: <i>stopped</i> "

                if "botcontrol" in self.data and "started" in self.data['botcontrol']:
                    output = (
                        output
                        + f" \u23F1 <b>Uptime</b>: <i>{self._getUptime(self.data['botcontrol']['started'])}</i>\n"
                    )
                mbot.send(output, parsemode="HTML")
                sleep(0.2)

        output = f"<b>Bot Count ({bots})</b>"
        print(output)
        mbot.send(output, parsemode="HTML")

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
        """Ask what user wants to see active order/pairs or all"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        keyboard = [
            [
                InlineKeyboardButton("Active Orders", callback_data="orders"),
                InlineKeyboardButton("Active Pairs", callback_data="pairs"),
                InlineKeyboardButton("All", callback_data="allactive"),
            ],
            [InlineKeyboardButton("Cancel", callback_data="cancel")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Make your selection", reply_markup=reply_markup)

    def marginresponse(self, update: Updater, context):
        """Show current active orders/pairs or all margins or latest messages"""
        if not self._checkifallowed(str(context._user_id_and_data[0]), update):
            return

        jsonfiles = os.listdir(os.path.join(self.datafolder, "telegram_data"))
        openoutput = ""
        closeoutput = ""
        for file in jsonfiles:
            if (
                ".json" in file
                and not file == "data.json"
                and not file.__contains__("output.json")
            ):
                self._read_data(file)
                if "margin" in self.data:
                    if "margin" in self.data and self.data["margin"] == " ":
                        closeoutput = (
                            closeoutput + f"<b>{str(file).replace('.json', '')}</b>"
                        )
                        closeoutput = closeoutput + f"\n<i>{self.data['message']}</i>\n"
                    elif len(self.data) > 2:
                        space = 20 - len(str(file).replace(".json", ""))
                        margin_icon = (
                            "\U0001F7E2"
                            if "-" not in self.data["margin"]
                            else "\U0001F534"
                        )
                        openoutput = (
                            openoutput
                            + f"\U0001F4C8 <b>{str(file).replace('.json', '')}</b> ".ljust(
                                space
                            )
                        )
                        openoutput = (
                            openoutput
                            + f" {margin_icon}<i>Current Margin: {self.data['margin']}  \U0001F4B0 (P/L): {self.data['delta']}</i>\n"
                        )

        query = update.callback_query

        if query.data == "orders":
            if openoutput == "":
                query.edit_message_text(
                    "<b>No open orders found.</b>", parse_mode="HTML"
                )
            else:
                query.edit_message_text(
                    f"<b>Open Order(s)</b>\n{openoutput}", parse_mode="HTML"
                )
        elif query.data == "pairs":
            if closeoutput == "":
                query.edit_message_text(
                    "<b>No active pairs found.</b>", parse_mode="HTML"
                )
            else:
                query.edit_message_text(
                    f"<b>Active Pair(s)</b>\n{closeoutput}", parse_mode="HTML"
                )
        elif query.data == "allactive":
            query.edit_message_text(
                f"<b>Open Order(s)</b>\n{openoutput}", parse_mode="HTML"
            )
            mbot = Telegram(self.token, str(context._chat_id_and_data[0]))
            mbot.send(f"<b>Active Pair(s)</b>\n{closeoutput}", parsemode="HTML")

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
        output = subprocess.getoutput(
            f"python3 pycryptobot.py --stats --exchange {self.exchange}  --market {self.pair}  "
        )
        update.message.reply_text(output, parse_mode="HTML")

        return ConversationHandler.END

    def sellrequest(self, update, context):
        """Manual sell request (asks which coin to sell)"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = self._getoptions("sell", "")

        if len(buttons) > 0:
            reply_markup = InlineKeyboardMarkup(buttons)
            update.message.reply_text(
                "<b>What do you want to sell?</b>",
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        else:
            update.message.reply_text("No active bots found.")

    def sellresponse(self, update, context):
        """create the manual sell order"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query

        self._read_data(query.data.replace("sell_", ""))
        if "botcontrol" in self.data:
            self.data["botcontrol"]["manualsell"] = True
            self._write_data(query.data.replace("sell_", ""))
            query.edit_message_text(
                f"Selling: {query.data.replace('sell_', '').replace('.json','')}\n<i>Please wait for sale notification...</i>",
                parse_mode="HTML",
            )

    def buyrequest(self, update, context):
        """Manual buy request (asks which coin to buy)"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = self._getoptions("buy", "")

        if len(buttons) > 0:
            reply_markup = InlineKeyboardMarkup(buttons)
            update.message.reply_text(
                "<b>What do you want to buy?</b>",
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        else:
            update.message.reply_text("No active bots found.")

    def buyresponse(self, update, context):
        """create the manual sell order"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query

        self._read_data(query.data.replace("buy_", ""))
        if "botcontrol" in self.data:
            self.data["botcontrol"]["manualbuy"] = True
            self._write_data(query.data.replace("buy_", ""))
            query.edit_message_text(
                f"Buying: {query.data.replace('buy_', '').replace('.json','')}\n<i>Please wait for buy notification...</i>",
                parse_mode="HTML",
            )

    def showconfigrequest(self, update, context):
        """display config settings (ask which exchange)"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        keyboard = []
        for exchange in self.config:
            if not exchange == "telegram":
                keyboard.append(
                    [InlineKeyboardButton(exchange, callback_data=exchange)]
                )

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Select exchange", reply_markup=reply_markup)

    def showconfigresponse(self, update, context):
        """display config settings based on exchanged selected"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        with open(os.path.join(self.config_file), "r", encoding="utf8") as json_file:
            self.config = json.load(json_file)

        query = update.callback_query

        pbot = self.config[query.data]["config"]

        query.edit_message_text(query.data + "\n" + json.dumps(pbot, indent=4))

    def pausebotrequest(self, update, context) -> None:
        """Ask which bots to pause"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = self._getoptions("pause", "active")

        if len(buttons) > 0:
            reply_markup = InlineKeyboardMarkup(buttons)
            update.message.reply_text(
                "<i>What do you want to pause?</i>",
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        else:
            update.message.reply_text("No active bots found.")

    def pausebotresponse(self, update, context):
        """Pause all or selected bot"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query

        if query.data == "pause_all":
            jsonfiles = os.listdir(os.path.join(self.datafolder, "telegram_data"))
            for file in jsonfiles:
                if (
                    ".json" in file
                    and not file == "data.json"
                    and not file.__contains__("output.json")
                ):
                    if self.updatebotcontrol(file, "pause"):
                        mbot = Telegram(self.token, str(context._chat_id_and_data[0]))
                        mbot.send(
                            f"<i>Pausing {file.replace('.json','')}</i>",
                            parsemode="HTML",
                        )
                        sleep(1)
        else:
            if self.updatebotcontrol(query.data.replace("pause_", ""), "pause"):
                query.edit_message_text(
                    f"<i>Pausing {query.data.replace('pause_', '').replace('.json','')}</i>",
                    parse_mode="HTML",
                )

    def restartbotrequest(self, update, context) -> None:
        """Ask which bot to restart"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = self._getoptions("restart", "paused")

        if len(buttons) > 0:
            reply_markup = InlineKeyboardMarkup(buttons)
            update.message.reply_text(
                "<b>What do you want to restart?</b>",
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        else:
            update.message.reply_text("No paused bots found.")

    def restartbotresponse(self, update, context):
        """restart selected or all bots"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query

        if query.data == "restart_all":
            jsonfiles = os.listdir(os.path.join(self.datafolder, "telegram_data"))
            query.edit_message_text(f"Restarting all bots", parse_mode="HTML")
            for file in jsonfiles:
                if (
                    ".json" in file
                    and not file == "data.json"
                    and not file.__contains__("output.json")
                ):
                    if self.updatebotcontrol(file, "start"):
                        mbot = Telegram(self.token, str(context._chat_id_and_data[0]))
                        mbot.send(
                            f"<i>Restarting {file.replace('.json','')}</i>",
                            parsemode="HTML",
                        )
        else:
            if self.updatebotcontrol(query.data.replace("restart_", ""), "start"):
                query.edit_message_text(
                    f"Restarting {query.data.replace('restart_', '').replace('.json','')}",
                    parse_mode="HTML",
                )

    def startallbotsrequest(self, update, context) -> None:
        """Ask which bot to start from start list (or all)"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = []
        keyboard = []

        self._read_data()
        for market in self.data["markets"]:
            if not os.path.isfile(
                os.path.join(self.datafolder, "telegram_data", market + ".json")
            ):
                buttons.append(
                    InlineKeyboardButton(market, callback_data="start_" + market)
                )

        if len(buttons) > 0:
            if len(buttons) > 1:
                keyboard = [
                    [InlineKeyboardButton("All", callback_data="start_" + "_all")]
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

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            "<b>What crypto bots do you want to start?</b>",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    def startallbotsresponse(self, update, context) -> None:
        """start selected or all bots"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self._read_data()

        query = update.callback_query

        if "all" in query.data:
            query.edit_message_text("Starting all bots")
            for pair in self.data["markets"]:
                if not os.path.isfile(
                    os.path.join(self.datafolder, "telegram_data", pair + ".json")
                ):
                    overrides = self.data["markets"][pair]["overrides"]
                    if platform.system() == "Windows":
                        os.system(
                            f"start powershell -Command $host.UI.RawUI.WindowTitle = '{pair}' ; python3 pycryptobot.py --startmethod telegram {overrides}"
                        )
                    else:
                        subprocess.Popen(
                            f"python3 pycryptobot.py --startmethod telegram {overrides}", shell=True
                        )
                    mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
                    mBot.send(f"<i>Starting {pair} crypto bot</i>", parsemode="HTML")
                    sleep(10)
        else:
            overrides = self.data["markets"][str(query.data).replace("start_", "")][
                "overrides"
            ]
            if platform.system() == "Windows":
                os.system(
                    f"start powershell -Command $host.UI.RawUI.WindowTitle = '{query.data.replace('start_', '')}' ; python3 pycryptobot.py --startmethod telegram {overrides}"
                )
                # os.system(f"start powershell -NoExit -Command $host.UI.RawUI.WindowTitle = '{query.data.replace('start_', '')}' ; python3 pycryptobot.py {overrides}")
            else:
                subprocess.Popen(f"python3 pycryptobot.py --startmethod telegram {overrides}", shell=True)
            query.edit_message_text(
                f"<i>Starting {str(query.data).replace('start_', '')} crypto bots</i>",
                parse_mode="HTML",
            )

    def stopbotrequest(self, update, context) -> None:
        """ask which active bots to stop (or all)"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = self._getoptions("stop", "active")

        if len(buttons) > 0:

            buttons.insert(
                0,
                [
                    InlineKeyboardButton(
                        "All (w/o open order)", callback_data="stop_allclose"
                    )
                ],
            )

            reply_markup = InlineKeyboardMarkup(buttons)
            update.message.reply_text(
                "<b>What do you want to stop?</b>",
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        else:
            update.message.reply_text("No active bots found.")

    def stopbotresponse(self, update, context) -> None:
        """stop all or selected bot"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query
        self._read_data()

        if "allclose" in query.data:
            query.edit_message_text("Stopping bots")
            jsonfiles = os.listdir(os.path.join(self.datafolder, "telegram_data"))
            telegram = Telegram(self.token, str(context._chat_id_and_data[0]))
            for file in jsonfiles:
                if (
                    ".json" in file
                    and not file == "data.json"
                    and not file.__contains__("output.json")
                ):
                    self._read_data(file)
                    if "margin" in self.data and self.data["margin"] == " ":
                        if self.updatebotcontrol(file, "exit"):
                            telegram.send(
                                f"Stopping {file.replace('.json', '')} crypto bot"
                            )
                            sleep(1)

        elif "all" in query.data:
            query.edit_message_text("Stopping all bots")

            jsonfiles = os.listdir(os.path.join(self.datafolder, "telegram_data"))
            telegram = Telegram(self.token, str(context._chat_id_and_data[0]))
            for file in jsonfiles:
                if (
                    ".json" in file
                    and not file == "data.json"
                    and not file.__contains__("output.json")
                ):
                    if self.updatebotcontrol(file, "exit"):
                        telegram.send(
                            f"Stopping {file.replace('.json', '')} crypto bot"
                        )
                        sleep(1)
        else:
            if self.updatebotcontrol(str(query.data).replace("stop_", ""), "exit"):
                query.edit_message_text(
                    f"Stopping {str(query.data).replace('stop_', '').replace('.json', '')} crypto bot"
                )

        query.edit_message_text("Operation Complete")

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

        def IsBotRunning() -> bool:
            if os.path.isfile(
                    os.path.join(self.datafolder, "telegram_data", f"{self.pair}.json")
                ):
                return True
            
            return False

        def StartWindowsProcess() -> None:
            # subprocess.Popen(f"python3 pycryptobot.py {overrides}", creationflags=subprocess.CREATE_NEW_CONSOLE)
            os.system(
                    f"start powershell -Command $host.UI.RawUI.WindowTitle = '{self.pair}' ; "
                    f"python3 pycryptobot.py --startmethod {startmethod} --exchange {self.exchange} --market {self.pair} {self.overrides}"
                )

        def StartLinuxProcess() -> None:
            subprocess.Popen(
                    f"python3 pycryptobot.py --startmethod {startmethod} --exchange {self.exchange} --market {self.pair} {self.overrides}",
                    shell=True,
                )

        if update.message.text == "Auto_Yes":
            if IsBotRunning():
                update.message.reply_text(
                    "Bot is already running, no action taken.",
                    reply_markup=ReplyKeyboardRemove())
                return None

            if platform.system() == "Windows":
                StartWindowsProcess()
            else:
                StartLinuxProcess()

        if update.message.text == "Yes":

            if IsBotRunning():
                update.message.reply_text(
                    "Bot is already running, no action taken.",
                    reply_markup=ReplyKeyboardRemove())
                return None

            if platform.system() == "Windows":
                StartWindowsProcess()
                update.message.reply_text(f"{self.pair} crypto bot Starting", reply_markup=ReplyKeyboardRemove())
            else:
                StartLinuxProcess()
                update.message.reply_text(f"{self.pair} crypto bot Starting",reply_markup=ReplyKeyboardRemove())

            update.message.reply_text(
                "Command Complete, have a nice day.", reply_markup=ReplyKeyboardRemove()
            )
        return ConversationHandler.END

    def updatebotcontrol(self, market, status) -> bool:
        """used to update bot json files for controlling state"""
        self._read_data(market)

        if "botcontrol" in self.data:
            self.data["botcontrol"]["status"] = status
            self._write_data(market)
            return True

        return False

    def error(self, update, context):
        """Log Errors"""
        if len(context.error.args) > 0 or "message" in context.error:
            if "HTTPError" in context.error.args[0]: # if "HTTPError" in context.error[0] or 
                while self.checkconnection() == False:
                    logger.warning("No internet connection found")
                    self.updater.start_polling(poll_interval=30)
                    sleep(30)
                self.updater.start_polling()
            else:
                logger.warning('Update caused error "%s"', context.error.args[0])

    def done(self, update, context):
        """added for conversations to end"""
        return ConversationHandler.END

    def deleterequest(self, update, context):
        """ask which bot to delete"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = []
        keyboard = []

        self._read_data()
        for market in self.data["markets"]:
            buttons.append(
                InlineKeyboardButton(market, callback_data="delete_" + market)
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
            "<b>What crypto bots do you want to delete?</b>",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    def deleteresponse(self, update, context):
        """delete selected bot"""
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self._read_data()

        query = update.callback_query

        self.data["markets"].pop(str(query.data).replace("delete_", ""))

        self._write_data()

        query.edit_message_text(
            f"<i>Deleted {str(query.data).replace('delete_', '')} crypto bot</i>",
            parse_mode="HTML",
        )

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

        if self.autoscandelay > 0:
            s.start()
            s.add_job(self.StartMarketScan, args=(update, context), trigger='interval', minutes=self.autoscandelay*60, name='Volume Auto Scanner', misfire_grace_time=10)
            update.message.reply_text(
                f"<b>Scan job schedule created to run every {self.autoscandelay} hour(s)</b> \u2705", parse_mode="HTML"
            )
        self.StartMarketScan(update,context)

    def StopScanning(self,update,context):
        s.shutdown()
        update.message.reply_text(
                "<b>Scan job schedule has been removed</b> \u2705", parse_mode="HTML"
            )

    def StartMarketScan(self, update, context):

        debug = False

        try:
            with open("scanner.json") as json_file:
                config = json.load(json_file)
        except IOError as err:
            update.message.reply_text(
                f"<i>scanner.json config error</i>\n{err}", parse_mode="HTML"
            )
            return

        update.message.reply_text(
            f"<i>Gathering market data, please wait...</i> \u23F3", parse_mode="HTML"
        )
        # subprocess.Popen("python3 scanner.py", shell=True)
        output = subprocess.getoutput("python3 scanner.py")

        telegram = Telegram(self.token, str(context._chat_id_and_data[0]))
        telegram.send("Stopping crypto bots")
        jsonfiles = os.listdir(os.path.join(self.datafolder, "telegram_data"))
        for file in jsonfiles:
            if (
                ".json" in file
                and not file == "data.json"
                and not file.__contains__("output.json")
            ):
                self._read_data(file)
                if "margin" in self.data and self.data["margin"] == " ":
                    if self.updatebotcontrol(file, "exit"):
                        sleep(5)
        
        self._read_data()
        botcounter = 0
        for ex in config:
            for quote in config[ex]["quote_currency"]:
                logger.info(f"{ex} {quote}")
                with open(
                    os.path.join(
                        self.datafolder, "telegram_data", f"{ex}_{quote}_output.json"
                    ),
                    "r",
                    encoding="utf8",
                ) as json_file:
                    data = json.load(json_file)
                # update.message.reply_text(
                #     f"<b>{ex} ({quote})</b> \u23F3", parse_mode="HTML"
                # )
                outputmsg =  f"<b>{ex} ({quote})</b> \u23F3 \n"
                for row in data:
                    if debug:
                        logger.info("%s", row)

                    if self.maxbotcount > 0 and botcounter > self.maxbotcount:
                        continue
                    
                    if self.enableleverage == False and (
                        str(row).__contains__("DOWN") or str(row).__contains__("UP")
                    ):
                        continue

                    if row in self.data["scannerexceptions"]:
                        outputmsg = outputmsg + f"*** {row} found on scanner exception list ***\n"
                        # update.message.reply_text(f"{row} found on scanner exception list")
                    else:
                        if data[row]["atr72_pcnt"] != None:
                            if debug:
                                logger.info(data[row])
                            if data[row]["atr72_pcnt"] >= self.atr72pcnt:
                                self.exchange = ex
                                self.pair = row 
                                update.message.text = "Auto_Yes"
                                if self.enable_buy_next and data[row]["buy_next"]:
                                    outputmsg = outputmsg + f"<i><b>{row}</b>  //--//  <b>atr72_pcnt:</b> {data[row]['atr72_pcnt']}%  //--//  <b>buy_next:</b> {data[row]['buy_next']}</i>\n"
                                    self.newbot_start(update, context, "scanner")
                                elif not self.enable_buy_next:
                                    outputmsg = outputmsg + f"<i><b>{row}</b>  //--//  <b>atr72_pcnt:</b> {data[row]['atr72_pcnt']}%</i>\n"
                                    self.newbot_start(update, context, "scanner")
                                botcounter += 1
                                sleep(10)

                update.message.reply_text(f"{outputmsg}", parse_mode="HTML")

            update.message.reply_text(f"<i>Operation Complete.</i>", parse_mode="HTML")

    def cleandata(self, update, context) -> None:
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        jsonfiles = os.listdir(os.path.join(self.datafolder, "telegram_data"))
        for i in range(len(jsonfiles), 0, -1):
            jfile = jsonfiles[i-1]
        # for jfile in jsonfiles:
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
    dp.add_handler(CommandHandler("showinfo", botconfig.showbotinfo, Filters.text))

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
    dp.add_handler(CommandHandler("buy", botconfig.buyrequest, Filters.text))
    dp.add_handler(CommandHandler("sell", botconfig.sellrequest, Filters.text))
    dp.add_handler(CommandHandler("deletebot", botconfig.deleterequest, Filters.text))

    dp.add_handler(CommandHandler("startscanner", botconfig.StartScanning, Filters.text))
    dp.add_handler(CommandHandler("stopscanner", botconfig.StopScanning, Filters.text))

    dp.add_handler(CommandHandler("cleandata", botconfig.cleandata, Filters.text))

    dp.add_handler(CommandHandler("removeexception", botconfig.ExceptionRemove, Filters.text))

    # Response to Question handler
    dp.add_handler(CallbackQueryHandler(botconfig.responses))

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

    while botconfig.checkconnection() is False:
        sleep(30)

    # Start the Bot
    botconfig.updater.start_polling()

    # Run the bot until you press Ctrl-C
    # since start_polling() is non-blocking and will stop the bot gracefully.
    botconfig.updater.idle()


if __name__ == "__main__":
    main()
