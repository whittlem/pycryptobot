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
from threading import Event


from warnings import filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.bot import Bot, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, Filters, InlineQueryHandler
from time import time, sleep
from models.chat import Telegram

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

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
                    if not self.data['margin'] == " ":
                        buttons.append(InlineKeyboardButton(file.replace('.json', ''), callback_data=callbacktag + "_" + file))
                else:
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
            self.data = self._read_data()
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

        if query.data == "orders" or query.data == "pairs" or query.data == "allactive":
            self.marginresponse(update, context)

        if query.data == "binance" or query.data == "coinbasepro" or query.data == "kucoin":
            self.showconfigresponse(update, context)

        if "pause_" in query.data:
            self.pausebotresponse(update, context)

        if "restart_" in query.data:
            self.restartbotresponse(update, context)

        if 'sell_' in query.data:
            self.sellresponse(update, context)

        if 'stop_' in query.data:
            self.stopbotresponse(update, context)

        if 'add_' in query.data:
            self.savenewbot(update, context)

        if 'start_' in query.data:
            self.startallbotsresponse(update, context)

        if query.data == "cancel":
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
        helptext += "<b>/stats {market} {exchange}</b> - <i>display stats for market</i>\n"
        helptext += "<b>/showinfo</b> - <i>display bot(s) status</i>\n"
        helptext += "<b>/showconfig</b> - <i>show config for exchange</i>\n"
        helptext += "<b>/sell</b> - <i>sell market pair on next iteration</i>\n"
        helptext += "<b>/pausebots</b> - <i>pause all or the selected bot</i>\n"
        helptext += "<b>/restartbots</b> - <i>restart all or the selected bot</i>\n"
        helptext += "<b>/stopbots</b> - <i>stop all or the selected bots</i>\n\n"
        helptext += "<b>Optional Customisable Commands</b>\n\n"
        helptext += "<b>/startnew {bot_variables}</b> - <i>start the requested pair</i>\n"
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
        for pair in self.data['trades']:
            output = output + f"<b>{pair}</b>\n{self.data['trades'][pair]['timestamp']}"
            output = output + F"\n<i>Bought at: {self.data['trades'][pair]['price']}   Margin: {self.data['trades'][pair]['margin']}</i>\n"

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
            if not file == "data.json" and not file == "startbot_single.bat" and not file == "startbot_multi.bat":
                self._read_data(file)
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
        # update.bot.sendMessage(context._chat_id_and_data[0], 'Make your selection', reply_markup=reply_markup).then(def answerCallbacks[context._chat_id_and_data[0]] = function(answer) {
        #             donateAmount = answer.text;
        #             update.bot.sendMessage(opts.chat_id, f'Custom donation for ${donateAmount} requested.`);
        # })

    def stats(self, update, context):

        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        update.message.reply_text("<i>Gathering Stats, please wait...</i>", parse_mode='HTML')

        output = subprocess.getoutput(f"python3 pycryptobot.py --stats --exchange {context.args[1]}  --market {context.args[0]}  ")

        mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
        mBot.send(output, parsemode="HTML")

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
                if not file == "data.json" and not file == "startbot_single.bat" and not file == "startbot_multi.bat":
                    self.updatebotcontrol(file, "pause")
        else:
            self.updatebotcontrol(query.data.replace('pause_', ''), 'pause')

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
                if not file == "data.json" and not file == "startbot_single.bat" and not file == "startbot_multi.bat":
                    self.updatebotcontrol(file, "start")
        else:
            self.updatebotcontrol(query.data.replace('restart_', ''), "start")

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
                subprocess.Popen(f"python3 pycryptobot.py {overrides}", creationflags=subprocess.CREATE_NEW_CONSOLE)
                mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
                mBot.send(f"Started {pair} crypto bot")
                # query.edit_message_text(f"Started {pair} crypto bot")
                sleep(10)
        else:
            overrides = self.data["markets"][str(query.data).replace("start_", "")]["overrides"]
            subprocess.Popen(f"python3 pycryptobot.py {overrides}", creationflags=subprocess.CREATE_NEW_CONSOLE)
            query.edit_message_text(f"Started {str(query.data).replace('start_', '')} crypto bots")
        # self._read_data()

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
            for pair in self.data["markets"]:
                if os.path.isfile(os.path.join(self.datafolder, "telegram_data", "stop_" + pair + '.json')):
                    self.updatebotcontrol(pair + '.json', "exit")
                    mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
                    mBot.send(f"Stopping {pair} crypto bot")
        else:
            self.updatebotcontrol(str(query.data).replace("stop_", ""), "exit")
            mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
            mBot.send(f"Stopping {str(query.data).replace('stop_', '').replace('.json', '')} crypto bot")

        #jsonfiles = os.listdir(os.path.join(self.datafolder, 'telegram_data'))

        #for file in jsonfiles:
        #    if not file == "data.json" and not file == "startbot_single.bat" and not file == "startbot_multi.bat":
         #       self.updatebotcontrol(file, "exit")

        # mBot = Telegram(self.token, str(context._chat_id_and_data[0]))
        #query = update.callback_query

        #query.edit_message_text(f"Stopping all crypto bots")

    def startnewbotrequest(self, update, context):

        i=0
        self.cl_args = ""
        while i <= len(context.args)-1:
            if context.args[i] == "--market":
                self.market = context.args[i+1]
            self.cl_args = self.cl_args + f" {context.args[i]} {context.args[i+1]}" if i+1 <= len(context.args)-1 else self.cl_args +  f" {context.args[i]} "
            i += 2

        keyboard = [
            [
                InlineKeyboardButton("OK", callback_data='ok'),
                InlineKeyboardButton("Cancel", callback_data='no'),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(f'Starting new bot with the following CL overrides\n{self.cl_args}', reply_markup=reply_markup)   

    def startnewbotresponse (self, update, context):
        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query

        if query.data == "ok":
            query.edit_message_text("Starting Bot")

            subprocess.Popen(f"python3 pycryptobot.py {self.cl_args}", creationflags=subprocess.CREATE_NEW_CONSOLE)

            query.edit_message_text(f"{self.market} crypto bot Starting")
            keyboard = [
                        
                            [InlineKeyboardButton("Yes - (will be added to you bot startup list)", callback_data='add_ok')],
                            [InlineKeyboardButton("Cancel", callback_data='cancel')],
                        
                    ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(f"Do you want to save this?", reply_markup=reply_markup)
        elif query.data == "cancel":
            query.edit_message_text("User Cancelled Request")

    def savenewbot(self, update, context):

        if not self._checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query

        self._read_data()
        self.data["markets"].update({self.market: {"overrides": self.cl_args}})
        self._write_data()

        query.edit_message_text(f"{self.market} saved")

    def updatebotcontrol(self, market, status):
        self._read_data(market)

        self.data["botcontrol"]["status"] = status

        self._write_data(market)

    def error(self, update, context):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, context.error)

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
    dp.add_handler(CommandHandler("stats", botconfig.stats, Filters.all))
    dp.add_handler(CommandHandler("showconfig", botconfig.showconfigrequest, Filters.text))   
    dp.add_handler(CommandHandler("showinfo", botconfig.showbotinfo, Filters.text))  

    # General Action Command 
    dp.add_handler(CommandHandler("setcommands", botconfig.setcommands))
    dp.add_handler(CommandHandler("start", botconfig.start))
    dp.add_handler(CommandHandler("sell", botconfig.sellrequest, Filters.text))
    dp.add_handler(CommandHandler("pausebots", botconfig.pausebotrequest, Filters.text))
    dp.add_handler(CommandHandler("restartbots", botconfig.restartbotrequest, Filters.text))
    
    # Custom Action Commands
    dp.add_handler(CommandHandler("startbots", botconfig.startallbotsrequest))
    dp.add_handler(CommandHandler("stopbots", botconfig.stopbotrequest))
    dp.add_handler(CommandHandler("startnew", botconfig.startnewbotrequest, Filters.text))

    # Response to Question handler
    dp.add_handler(CallbackQueryHandler(botconfig._responses))

    # log all errors
    dp.add_error_handler(botconfig.error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    # since start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == "__main__":
    main()
