#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple Bot to reply to Telegram messages.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import argparse
import logging
import os
import json
import subprocess
import platform


from warnings import filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.bot import Bot, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, Filters, InlineQueryHandler, ConversationHandler, MessageHandler, RegexHandler
from time import time, sleep
from telegram.replykeyboardremove import ReplyKeyboardRemove

from telegram.utils.helpers import DEFAULT_20
from models.chat import Telegram

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

 
CHOOSING, TYPING_REPLY = range(2)
EXCHANGE, MARKET, ANYOVERRIDES, OVERRIDES, SAVE, START = range(6)
 
reply_keyboard = [['Coinbase Pro', 'Binance', 'Kucoin']]

markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

class TelegramBotBase():
    def _read_data(self, name: str = "data.json") -> None:
        file = self.filename if name =="" else name
        # Logger.info(f"Reading {file}")
        with open(os.path.join(self.datafolder, 'telegram_data', file), 'r') as json_file:
            self.data = json.load(json_file)

    def _write_data(self, name: str = "data.json") -> None:
        file = self.filename if name =="" else name
        # Logger.info(f"Writing {file}")
        try:
            with open(os.path.join(self.datafolder, 'telegram_data', file), 'w') as outfile:
                json.dump(self.data, outfile, indent=4)
        except Exception as err:
            # Logger.critical(str(err))
            with open(os.path.join(self.datafolder, 'telegram_data', file), 'w') as outfile:
                json.dump(self.data, outfile, indent=4)

    def _getoptions(self, callbacktag, state):
        buttons = []
        keyboard = []
        jsonfiles = os.listdir(os.path.join(self.datafolder, 'telegram_data'))
        for file in jsonfiles:
            if not file == "data.json" and not file == "startbot_single.bat" and not file == "startbot_multi.bat":
                self._read_data(file)
                if callbacktag == "sell":
                    if 'margin' in self.data:
                        if not self.data['margin'] == " ":
                            buttons.append(InlineKeyboardButton(file.replace('.json', ''), callback_data=callbacktag + "_" + file))
                else:
                    if 'botcontrol' in self.data:
                        if self.data['botcontrol']['status'] == state:
                            buttons.append(InlineKeyboardButton(file.replace('.json', ''), callback_data=callbacktag + "_" + file))
        
        if len(buttons) > 0:
            if len(buttons) > 1:
                keyboard = [[InlineKeyboardButton("All", callback_data=callbacktag + '_all')]]

            i=0
            while i <= len(buttons) -1:
                if len(buttons)-1 >= i +2:
                    keyboard.append([buttons[i], buttons[i+1], buttons[i+2]])
                elif len(buttons)-1 >= i +1:
                    keyboard.append([buttons[i], buttons[i+1]])
                else:
                    keyboard.append([buttons[i]])
                i += 3
            keyboard.append([InlineKeyboardButton("Cancel", callback_data='cancel')])
        return keyboard

    def _checkifallowed(self, userid, update) -> bool:
        if not str(userid) == self.userId:
            update.message.reply_text('<b>Not authorised!</b>', parse_mode="HTML")
            return False

        return True

class TelegramBot(TelegramBotBase):
    def __init__(self):
        self.token = ""
        self.userid = ""
        self.clientid = ""
        self.config_file = ""
        self.datafolder = ".\\"
        self.cl_args = ""
        self.market = ""
        self.data = {}

        self.exchange = ""
        self.pair = ""
        self.overrides = ""

        parser = argparse.ArgumentParser(description="PyCryptoBot Telegram Bot")
        parser.add_argument(
            "--config", type=str, dest="config_file", help="pycryptobot config file", default="config.json")
        parser.add_argument(
            "--datafolder", type=str,
            help="Use the datafolder at the given location, useful for multi bots running in different folders", default="")

        args = parser.parse_args()

        self.config_file = args.config_file

        with open(os.path.join(self.config_file), 'r') as json_file:
            self.config = json.load(json_file)

        self.token = self.config["telegram"]["token"]
        self.userId = self.config["telegram"]["user_id"]
        self.clientId = self.config["telegram"]["client_id"]

        if "datafolder" in self.config["telegram"]:
            self.datafolder = self.config["telegram"]["datafolder"]
        
        if not args.datafolder == "":
            self.datafolder = args.datafolder

        self._bot = Telegram(self.token, self.clientId)

        if not os.path.exists(os.path.join(self.datafolder, "telegram_data")):
            os.mkdir(os.path.join(self.datafolder, "telegram_data"))

        if os.path.isfile(os.path.join(self.datafolder, "telegram_data", "data.json")):
            self._read_data()
            if not "markets" in self.data:
                self.data.update({"markets": {}})
                self._write_data()
        else:
            ds = {"trades" : {}}
            self.data = ds
            self._write_data()

    def _responses(self, update, context):

        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query

        if query.data == 'ok' or query.data == 'no':
            self.startnewbotresponse(update, context)

        elif query.data == "orders" or query.data == "pairs" or query.data == "allactive":
            self.marginresponse(update, context)

        elif query.data == "binance" or query.data == "coinbasepro" or query.data == "kucoin":
            self.showconfigresponse(update, context)

        elif "pause_" in query.data:
            self.pausebotresponse(update, context)

        elif "restart_" in query.data:
            self.restartbotresponse(update, context)

        elif 'sell_' in query.data:
            self.sellresponse(update, context)

        elif 'stop_' in query.data:
            self.stopbotresponse(update, context)

        elif 'add_' in query.data:
            self.savenewbot(update, context)

        elif 'start_' in query.data:
            self.startallbotsresponse(update, context)

        elif query.data == "cancel":
            query.edit_message_text("User Cancelled Request")
    # Define a few command handlers. These usually take the two arguments update and
    # context. Error handlers also receive the raised TelegramError object in error.
    def start(self, update, context):
        """Send a message when the command /start is issued."""
        update.message.reply_text("Hi!")

    def setcommands(self, update: Updater, context : Filters) -> None:
        command = [
        BotCommand("help","show help text"),
        BotCommand("margins","show margins for all open trades"),
        BotCommand("trades", "show closed trades"),
        BotCommand("stats", "show exchange stats for market/pair"),
        BotCommand("showinfo", "show all running bots status"),
        BotCommand("showconfig", "show config for selected exchange"),
        BotCommand("sell", "manually sell" ),
        BotCommand("pausebots", "pause all or selected bot"),
        BotCommand("restartbots", "restart all or selected bot"),
        BotCommand("stopbots", "stop all or the selected bot"),
        BotCommand("startnew", "start a new bot"),
        BotCommand("startbots", "start all bots"),
        ]

        ubot = Bot(self.token)
        ubot.set_my_commands(command)

        mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
        mBot.send("Bot Commands created")

    def help(self, update: Updater, context):
        """Send a message when the command /help is issued."""

        helptext = "<b>Command List</b>\n\n"
        helptext += "<b>/setcommands</b> - <i>add all commands to bot for easy access</i>\n"
        helptext += "<b>/margins</b> - <i>show margins for open trade</i>\n"
        helptext += "<b>/trades</b> - <i>show closed trades</i>\n"
        helptext += "<b>/stats</b> - <i>display stats for market</i>\n"
        helptext += "<b>/showinfo</b> - <i>display bot(s) status</i>\n"
        helptext += "<b>/showconfig</b> - <i>show config for exchange</i>\n"
        helptext += "<b>/sell</b> - <i>sell market pair on next iteration</i>\n"
        helptext += "<b>/pausebots</b> - <i>pause all or the selected bot</i>\n"
        helptext += "<b>/restartbots</b> - <i>restart all or the selected bot</i>\n"
        helptext += "<b>/stopbots</b> - <i>stop all or the selected bots</i>\n\n"
        helptext += "<b>Optional Customisable Commands</b>\n\n"
        helptext += "<b>/startnew</b> - <i>start the requested pair</i>\n"
        helptext += "<b>/startbots</b> - <i>start all or the selected bots</i>\n"

        mBot = Telegram(self.token, str(context._chat_id_and_data[0]))

        mBot.send(helptext, parsemode="HTML")

    def showbotinfo(self, update, context) -> None:
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        jsonfiles = os.listdir(os.path.join(self.datafolder, 'telegram_data'))
        output = ""
        for file in jsonfiles:
            if not file == "data.json" and not file == "startbot_single.bat" and not file == "startbot_multi.bat":
                self._read_data(file)                
                output = output + f"<b>{file.replace('.json', '')}</b> - "
                output = output + F"<i>Current Status: {self.data['botcontrol']['status']}</i>\n"

        if output != "":
            mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
            mBot.send(output, parsemode="HTML")

    def trades(self, update, context):

        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self._read_data()

        output = ""
        for time in self.data['trades']:
            output = ""
            output = output + f"<b>{self.data['trades'][time]['pair']}</b>\n{time}"
            output = output + F"\n<i>Sold at: {self.data['trades'][time]['price']}   Margin: {self.data['trades'][time]['margin']}</i>\n"

            if output != "":
                mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
                mBot.send(output, parsemode="HTML")
            # update.message.reply_text(output, parse_mode="HTML")        

    def marginrequest(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        keyboard = [
            [
                InlineKeyboardButton("Active Orders", callback_data='orders'),
                InlineKeyboardButton("Active Pairs", callback_data='pairs'),
                InlineKeyboardButton("All", callback_data='allactive'),
            ],
            [
                InlineKeyboardButton("Cancel", callback_data='cancel')
            ],
         ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Make your selection', reply_markup=reply_markup)

    def marginresponse(self, update: Updater, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        jsonfiles = os.listdir(os.path.join(self.datafolder, 'telegram_data'))
        openoutput = ''
        closeoutput = ""
        for file in jsonfiles:
            #if not file == "data.json" and not file == "startbot_single.bat" and not file == "startbot_multi.bat":
            self._read_data(file)
            if 'margin' in self.data:
                if self.data['margin'] == " ":
                    closeoutput = closeoutput + f"<b>{str(file).replace('.json', '')}</b>"
                    closeoutput = closeoutput + F"\n<i>{self.data['message']}</i>\n"
                elif len(self.data) > 2:
                    openoutput = openoutput + f"<b>{str(file).replace('.json', '')}</b>"
                    openoutput = openoutput + F"\n<i>Current Margin: {self.data['margin']}   (P/L): {self.data['delta']}</i>\n"
        
        mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
        
        query = update.callback_query

        if query.data == "orders":
            query.edit_message_text(openoutput, parse_mode="HTML")
        elif query.data == "pairs":
            query.edit_message_text(closeoutput, parse_mode="HTML")
        elif query.data == "allactive":
            query.edit_message_text(openoutput, parse_mode="HTML")
            mBot.send(closeoutput, parsemode="HTML")

    def statsrequest(self, update: Updater, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        keyboard = [
            [
                InlineKeyboardButton("Binance", callback_data='stats_binance'),
                InlineKeyboardButton("Coinbase Pro", callback_data='stats_coinbasepro'),
                InlineKeyboardButton("Kucoin", callback_data='stats_kucoin'),
            ],
            [
                InlineKeyboardButton("Cancel", callback_data='cancel')
            ],
         ]

        update.message.reply_text('Select the exchange', reply_markup=markup)

        return CHOOSING

    def stats_exchange_received(self, update, context):
        if update.message.text.lower() == 'done':
            return
        self.exchange = update.message.text.lower()
        if update.message.text == 'Coinbase Pro':
            self.exchange = 'coinbasepro'

        update.message.reply_text('Which market/pair do you want stats for?', reply_markup=ReplyKeyboardRemove())
 
        return TYPING_REPLY

    def stats_pair_received(self, update, context):
        self.pair = update.message.text

        update.message.reply_text("<i>Gathering Stats, please wait...</i>", parse_mode='HTML')

        output = subprocess.getoutput(f"python3 pycryptobot.py --stats --exchange {self.exchange}  --market {self.pair}  ")

        mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
        update.message.reply_text(output, parse_mode="HTML")
    
        # update.message.reply_text("Neat! Just so you know, this is what you already told me:")
        return ConversationHandler.END

    def sellrequest(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = self.getoptions("sell", "")

        if len(buttons) > 0:
            reply_markup = InlineKeyboardMarkup(buttons)
            update.message.reply_text('<b>What do you want to sell?</b>', reply_markup=reply_markup, parse_mode='HTML')
        else:
            update.message.reply_text('No active bots found.')

    def sellresponse(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query

        self._read_data(query.data.replace('sell_', ''))
        if 'botcontrol' in self.data:
            self.data['botcontrol']['manualsell'] = True
            self._write_data(query.data.replace('sell_', ''))
            query.edit_message_text(f"Selling: {self.wanttosell}\n<i>Please wait for sale notification...</i>", parse_mode="HTML")

    def showconfigrequest(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        keyboard = []
        for exchange in self.config:
            if not exchange == "telegram":
                keyboard.append([InlineKeyboardButton(exchange, callback_data=exchange)])

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Select exchange', reply_markup=reply_markup)

    def showconfigresponse(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        with open(os.path.join(self.config_file), 'r') as json_file:
            self.config = json.load(json_file)

        query = update.callback_query

        # tempconfig = json.load(self.config_file)
        pbot = self.config[query.data]["config"]
        mBot = Telegram(self.token, str(context._chat_id_and_data[0]))

        query.edit_message_text(query.data + "\n" + json.dumps(pbot, indent=4))
        # update.message.reply_text(json.dumps(pbot, indent=4))

    def pausebotrequest(self, update, context) -> None:
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = self._getoptions("pause", 'active')

        if len(buttons) > 0:
            reply_markup = InlineKeyboardMarkup(buttons)
            update.message.reply_text('<i>What do you want to pause?</i>', reply_markup=reply_markup, parse_mode='HTML')
        else:
            update.message.reply_text('No active bots found.')
        # update.message.reply_text('<i>What do you want to pause?</i>', reply_markup=reply_markup, parse_mode='HTML')

    def pausebotresponse(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query

        if query.data == 'pause_all':
            jsonfiles = os.listdir(os.path.join(self.datafolder, 'telegram_data'))
        
            for file in jsonfiles:
                if self.updatebotcontrol(file, "pause"):
                    query.edit_message_text(f"<i>Pausing {file.replace('.json','')}</i>", parse_mode="HTML")
        else:
            if self.updatebotcontrol(query.data.replace('pause_', ''), 'pause'):
                query.edit_message_text(f"<i>Pausing {query.data.replace('pause_', '').replace('.json','')}</i>", parse_mode="HTML")

    def restartbotrequest(self, update, context) -> None:
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = self._getoptions("restart", 'paused')

        if len(buttons) > 0:
            reply_markup = InlineKeyboardMarkup(buttons)
            update.message.reply_text('<b>What do you want to restart?</b>', reply_markup=reply_markup, parse_mode='HTML')
        else:
            update.message.reply_text('No paused bots found.')

    def restartbotresponse(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query

        if query.data == 'restart_all':
            jsonfiles = os.listdir(os.path.join(self.datafolder, 'telegram_data'))
        
            for file in jsonfiles:
                if self.updatebotcontrol(file, "start"):
                    query.edit_message_text(f"Restarting {file.replace('.json','')}", parse_mode="HTML")
        else:
            if self.updatebotcontrol(query.data.replace('restart_', ''), "start"):
                query.edit_message_text(f"Restarting {query.data.replace('restart_', '').replace('.json','')}", parse_mode="HTML")

    def startallbotsrequest(self, update, context) -> None:
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = []
        keyboard = []

        self._read_data()
        for market in self.data["markets"]:
            buttons.append(InlineKeyboardButton(market, callback_data="start_" + market))

        if len(buttons) > 0:
            if len(buttons) > 1:
                keyboard = [[InlineKeyboardButton("All", callback_data="start_" + '_all')]]

            i=0
            while i <= len(buttons) -1:
                if len(buttons)-1 >= i +2:
                    keyboard.append([buttons[i], buttons[i+1], buttons[i+2]])
                elif len(buttons)-1 >= i +1:
                    keyboard.append([buttons[i], buttons[i+1]])
                else:
                    keyboard.append([buttons[i]])
                i += 3
            keyboard.append([InlineKeyboardButton("Cancel", callback_data='cancel')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(f'<b>What crypto bots do you want to start?</b>', reply_markup=reply_markup, parse_mode='HTML')   

    def startallbotsresponse(self, update, context) -> None:
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self._read_data()

        query = update.callback_query

        if "all" in query.data:
            query.edit_message_text("Starting all bots")
            for pair in self.data["markets"]:
                overrides = self.data["markets"][pair]["overrides"]
                if platform.system() == 'Windows':
                    #subprocess.Popen(f"cmd /k python3 pycryptobot.py {overrides}", creationflags=subprocess.CREATE_NEW_CONSOLE)
                    os.system(f"start powershell -NoExit -Command $host.UI.RawUI.WindowTitle = '{pair}' ; python3 pycryptobot.py {overrides}")
                else:
                    subprocess.Popen(f'python3 pycryptobot.py {overrides}', shell=True)
                mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
                mBot.send(f"Started {pair} crypto bot")
                sleep(10)
        else:
            overrides = self.data["markets"][str(query.data).replace("start_", "")]["overrides"]
            if platform.system() == 'Windows':
                os.system(f"start powershell -NoExit -Command $host.UI.RawUI.WindowTitle = '{query.data.replace('start_', '')}' ; python3 pycryptobot.py {overrides}")
                #subprocess.Popen(f"python3 pycryptobot.py {overrides}", creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen(f'python3 pycryptobot.py {overrides}', shell=True)
                # subprocess.call(['open', '-W', '-a', 'Terminal.app', f'python3 pycryptobot.py {overrides}'])
            query.edit_message_text(f"Started {str(query.data).replace('start_', '')} crypto bots")

    def stopbotrequest(self, update, context) -> None:
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        buttons = self._getoptions("stop", 'active')
        # buttons += self._getoptions("stop", 'paused')

        if len(buttons) > 0:
            reply_markup = InlineKeyboardMarkup(buttons)
            update.message.reply_text('<b>What do you want to stop?</b>', reply_markup=reply_markup, parse_mode='HTML')
        else:
            update.message.reply_text('No paused bots found.')

    def stopbotresponse(self, update, context) -> None:
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query
        self._read_data()

        if "all" in query.data:
            query.edit_message_text("Stopping all bots")
            
            jsonfiles = os.listdir(os.path.join(self.datafolder, 'telegram_data'))

            for file in jsonfiles:
                if self.updatebotcontrol(file, "exit"):
                    mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
                    mBot.send(f"Stopping {file.replace('.json', '')} crypto bot")
        else:
            if self.updatebotcontrol(str(query.data).replace("stop_", ""), "exit"):
                mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
                mBot.send(f"Stopping {str(query.data).replace('stop_', '').replace('.json', '')} crypto bot")

    def newbot_request(self, update: Updater, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.exchange = ""
        self.market = ""
        self.overrides = ""

        update.message.reply_text('Select the exchange', reply_markup=markup)

        return EXCHANGE

    def newbot_exchange(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        if update.message.text.lower() == 'done':
            return
        self.exchange = update.message.text.lower()
        if update.message.text == 'Coinbase Pro':
            self.exchange = 'coinbasepro'

        update.message.reply_text('Which market/pair is this for?', reply_markup=ReplyKeyboardRemove())
 
        return ANYOVERRIDES

    def newbot_any_overrides(self, update, context) -> None:
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        reply_keyboard = [['Yes', 'No']]

        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

        update.message.reply_text('Do you want to use any commandline overrrides?', reply_markup=markup)

        return MARKET

    def newbot_market(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        if update.message.text == 'No':
            reply_keyboard = [['Yes', 'No']]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            update.message.reply_text(f"Do you want to save this?", reply_markup=markup)
            return SAVE

        self.pair = update.message.text
        update.message.reply_text('Tell me any other commandline overrrides to use?', reply_markup=ReplyKeyboardRemove())
 
        return OVERRIDES

    def newbot_overrides(self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        self.overrides = update.message.text

        update.message.reply_text(f"{self.pair} crypto bot Starting")
        keyboard = [
                        [InlineKeyboardButton("Yes - (will be added to you bot startup list)", callback_data='add_ok')],
                        [InlineKeyboardButton("No", callback_data='add_no')],
                ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(f"Do you want to save this?", reply_markup=reply_markup)

        return SAVE

    def newbot_save(self, update, context):

        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        if update.message.text == 'Yes':
            self._read_data()
            self.data["markets"].update({self.pair: {"overrides": f'--exchange {self.exchange} --market {self.pair} {self.overrides}'}})
            self._write_data()

            update.message.reply_text(f"{self.pair} saved")

        reply_keyboard = [['Yes', 'No']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text(f"Do you want to start this bot?", reply_markup=markup)

        return START

    def newbot_start(self, update, context) -> None:
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        if update.message.text == 'Yes':
            if platform.system() == 'Windows':
                #subprocess.Popen(f"python3 pycryptobot.py {overrides}", creationflags=subprocess.CREATE_NEW_CONSOLE)
                os.system(f"start powershell -NoExit -Command $host.UI.RawUI.WindowTitle = '{self.pair}' ; python3 pycryptobot.py --exchange {self.exchange} --market {self.pair} {self.overrides}")
            else:
                subprocess.Popen(f'python3 pycryptobot.py --exchange {self.exchange} --market {self.pair} {self.overrides}', shell=True)

            update.message.reply_text(f"{self.pair} crypto bot Starting", reply_markup=ReplyKeyboardRemove())

        update.message.reply_text(f"Command Complete, have a nice day.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def updatebotcontrol(self, market, status) -> bool:
        self._read_data(market)

        if 'botcontrol' in self.data:
            self.data["botcontrol"]["status"] = status
            self._write_data(market)
            return True

        return False

    def error(self, update, context):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, context.error)

    def done(self, update, context):
        return ConversationHandler.END

def main():
    """Start the bot."""
    # Create telegram bot configuration
    botconfig = TelegramBot()
    # Create the Updater and pass it your bot's token.
    updater = Updater(botconfig.token, use_context=True, )
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    
    # Information commands
    dp.add_handler(CommandHandler("help", botconfig.help))    
    dp.add_handler(CommandHandler("margins", botconfig.marginrequest, Filters.all))
    dp.add_handler(CommandHandler("trades", botconfig.trades, Filters.text))
    dp.add_handler(CommandHandler("showconfig", botconfig.showconfigrequest, Filters.text))   
    dp.add_handler(CommandHandler("showinfo", botconfig.showbotinfo, Filters.text))  

    # General Action Command 
    dp.add_handler(CommandHandler("setcommands", botconfig.setcommands))
    dp.add_handler(CommandHandler("sell", botconfig.sellrequest, Filters.text))
    dp.add_handler(CommandHandler("pausebots", botconfig.pausebotrequest, Filters.text))
    dp.add_handler(CommandHandler("restartbots", botconfig.restartbotrequest, Filters.text))
    
    # Custom Action Commands
    dp.add_handler(CommandHandler("startbots", botconfig.startallbotsrequest))
    dp.add_handler(CommandHandler("stopbots", botconfig.stopbotrequest))

    # Response to Question handler
    dp.add_handler(CallbackQueryHandler(botconfig._responses))

    conversation_stats = ConversationHandler(
        entry_points=[CommandHandler('stats', botconfig.statsrequest)],
        states={
            CHOOSING: [MessageHandler(Filters.text, botconfig.stats_exchange_received, pass_user_data=True)],
            TYPING_REPLY: [MessageHandler(Filters.text, botconfig.stats_pair_received, pass_user_data=True)],
        },
        fallbacks=[('Done', botconfig.done)]
    )

    conversation_newbot = ConversationHandler(
        entry_points=[CommandHandler('startnew', botconfig.newbot_request)],
        states={
            EXCHANGE: [MessageHandler(Filters.text, botconfig.newbot_exchange)],
            MARKET: [MessageHandler(Filters.text, botconfig.newbot_market)],
            ANYOVERRIDES: [MessageHandler(Filters.text, botconfig.newbot_any_overrides)],
            OVERRIDES: [MessageHandler(Filters.text, botconfig.newbot_overrides)],
            SAVE: [MessageHandler(Filters.text, botconfig.newbot_save)],
            START: [MessageHandler(Filters.text, botconfig.newbot_start)]
        },
        fallbacks=[('Done', botconfig.done)]
    )

    dp.add_handler(conversation_stats)
    dp.add_handler(conversation_newbot)
    # log all errors
    dp.add_error_handler(botconfig.error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    # since start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == "__main__":
    main()
