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


from warnings import filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, Filters

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

class TelegramBot():
    def __init__(self):
        self.token = ""
        self.userid = ""
        self.wanttosell = ""
        
        parser = argparse.ArgumentParser(description="PyCryptoBot Telegram Bot")
        parser.add_argument(
            "--config", type=str, dest="config_file", help="config file", default="config.json")
        args = parser.parse_args()

        config_file = open(args.config_file)

        self.config = json.load(config_file)
        self.token = self.config["telegram"]["token"]
        self.userId = self.config["telegram"]["user_id"]
        self.data = {}

    def _read_data(self) -> None:
        try:
            with open(os.path.join(os.curdir, 'telegram_data', 'data.json'), 'r') as json_file:
                self.data = json.load(json_file)
        except IOError as err:
            logger.error("Unable to find data.json file\n" + str(err))

    def _write_data(self) -> None:
        with open(os.path.join(os.curdir, 'telegram_data', 'data.json'), 'w') as outfile:
            json.dump(self.data, outfile, indent=4)

    def checkifallowed(self, userid, update) -> bool:
        if not str(userid) == self.userId:
            update.message.reply_text('<b>Not authorised!</b>', parse_mode="HTML")
            return False

        return True

    # Define a few command handlers. These usually take the two arguments update and
    # context. Error handlers also receive the raised TelegramError object in error.
    def start(update, context):
        """Send a message when the command /start is issued."""
        update.message.reply_text("Hi!")

    def help(self, update, context):
        """Send a message when the command /help is issued."""

        helptext = "<b>Command List</b>\n\n"
        helptext += "<b>/margins</b> - <i>show margins for open trade</i>\n"
        helptext += "<b>/trades</b> - <i>show closed trades</i>\n"
        helptext += "<b>/stats {market} {exchange}</b> - <i>display stats for market</i>\n"
        helptext += "<b>/sell {market}</b> - <i>sell market pair on next iteration</i>\n"
        helptext += "<b>/showconfig {exchange}</b> - <i>show config for exchange</i>\n"
        helptext += "<b>/stopbot {market}</b> - <i>stop the requested pair</i>\n"

        update.message.reply_text(helptext, parse_mode="HTML")

    def margins(self, update, context):

        if not self.checkifallowed(context._user_id_and_data[0], update):
            return

        self._read_data()

        output = ""
        for pair in self.data['margins']:
            if not pair == "dummy":
                output = output + f"<b>{pair}</b>"
                output = output + F"\n<i>Current Margin: {self.data['margins'][pair]['margin']}   (P/L): {self.data['margins'][pair]['delta']}</i>\n"

        if output != "":
            update.message.reply_text(output, parse_mode="HTML")

    def trades(self, update, context):

        if not self.checkifallowed(context._user_id_and_data[0], update):
            return

        self._read_data()

        output = ""
        for pair in self.data['trades']:
            # if not pair == "dummy":
            output = output + f"<b>{pair}</b>\n{self.data['trades'][pair]['timestamp']}"
            output = output + F"\n<i>Bought at: {self.data['trades'][pair]['price']}   Margin: {self.data['trades'][pair]['margin']}</i>\n"

        if output != "":
            update.message.reply_text(output, parse_mode="HTML")

    def stats(self, update, context):

        if not self.checkifallowed(context._user_id_and_data[0], update):
            return

        output = subprocess.getoutput(f"python pycryptobot.py --stats --exchange {context.args[1]}  --market {context.args[0]}  ")

        update.message.reply_text(output)

    def sell(self, update, context):
        if not self.checkifallowed(context._user_id_and_data[0], update):
            return

        self.wanttosell = context.args[0]

        keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data='sell'),
                InlineKeyboardButton("No", callback_data='nosell'),
            ],
            [InlineKeyboardButton("Cancel", callback_data='cancel')],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Are you sure you want to make a manual sell?', reply_markup=reply_markup)

    def sellresponse(self, update, context):

        if not self.checkifallowed(context._user_id_and_data[0], update):
            return

        query = update.callback_query

        if query.data == "nosell":
            query.edit_message_text("No confimation received")
        elif query.data == "cancel":
            query.edit_message_text("User Cancelled Request")

        elif query.data == "sell":
            self._read_data()
            alreadyadd = False

            for m in self.data["sell"]:
                if m == self.wanttosell:
                    alreadyadd = True

            if not alreadyadd:
                self.data.update({"sell": {self.wanttosell : {"sellnow": True}}})

            self._write_data()

            query.edit_message_text(f"Selling: {self.wanttosell}\n<i>Please wait for sale notification...</i>", parse_mode="HTML")
            self.wanttosell = ""

    def showconfig(self, update, context):
        if not self.checkifallowed(context._user_id_and_data[0], update):
            return

        pbot = self.config[context.args[0]]["config"]
        update.message.reply_text(json.dumps(pbot, indent=4))

    def stopbot(self, update, context):
        if not self.checkifallowed(context._user_id_and_data[0], update):
            return

    def echo(update, context):
        """Echo the user message."""
        update.message.reply_text("<i>" + update.message.text + "</i>", parse_mode="HTML")


    def error(update, context):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""
    bot = TelegramBot()    

    # Create the Updater and pass it your bot's token.
    updater = Updater(bot.token, use_context=True, )

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", bot.start))
    dp.add_handler(CommandHandler("help", bot.help))
    dp.add_handler(CommandHandler("margins", bot.margins, Filters.all))
    dp.add_handler(CommandHandler("trades", bot.trades, Filters.text))
    dp.add_handler(CommandHandler("sell", bot.sell, Filters.text))
    dp.add_handler(CallbackQueryHandler(bot.sellresponse))
    dp.add_handler(CommandHandler("stats", bot.stats, Filters.all))
    dp.add_handler(CommandHandler("showconfig", bot.showconfig, Filters.text))
    dp.add_handler(CommandHandler("stopbot", bot.stopbot, Filters.text))
    # on noncommand i.e message - echo the message on Telegram
    # dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(bot.error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    main()
