import os
from time import sleep
from datetime import datetime

from models.telegram.control import TelegramControl
from models.telegram.helper import TelegramHelper
from models.telegram.actions import TelegramActions

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater
from telegram.ext.callbackcontext import CallbackContext

helper = None
control = None
actions = None

class TelegramHandler():
    def __init__(self, datafolder, authuserid, tg_helper: TelegramHelper) -> None:
        self.authoriseduserid = authuserid
        self.datafolder = datafolder
        global helper ; helper = tg_helper
        global control ; control = TelegramControl(self.datafolder, tg_helper)
        global actions ; actions = TelegramActions(self.datafolder, tg_helper)

    def _checkifallowed(self, userid, update) -> bool:
        if str(userid) != self.authoriseduserid:
            update.message.reply_text("<b>Not authorised!</b>", parse_mode="HTML")
            return False

        return True

    def getRequest(self) -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("\U0001F4C8 Margins", callback_data="margin"),
                InlineKeyboardButton("\U00002139 Bot Status", callback_data="status"),
            ],
            [
                InlineKeyboardButton("\U0001F4D6 View configuration", callback_data="showconfig"),
            ],
            [
                InlineKeyboardButton("\U0001F9FE Restart open orders", callback_data="reopen"),
            ],
            [
                InlineKeyboardButton("\U0001F7E2 startbot(s)", callback_data="start"),
                InlineKeyboardButton("\U000023F8 pausebot(s)", callback_data="pause"),
            ],
            [
                InlineKeyboardButton("\U0000267B resumebot(s)", callback_data="resume"),
                InlineKeyboardButton("\U0001F534 stopbot(s)", callback_data="stop"),
            ],
            [
                InlineKeyboardButton("\U0001FA99 Buy", callback_data="buy"),
            ],
            [
                InlineKeyboardButton("\U0001F4B0 Sell", callback_data="sell"),
            ],
                        [
                InlineKeyboardButton("\U0001F50E Start Market Scanner", callback_data="startmarket"),
            ],
            [
                InlineKeyboardButton("Scanner Exceptions", callback_data="startmarket"),
                # InlineKeyboardButton("Remove\nscanner exception", callback_data="startmarket"),
            ],
            [
                InlineKeyboardButton("Stop Market Scanner", callback_data="stopmarket"),
            ],
            [InlineKeyboardButton("Cancel", callback_data="cancel")],
        ]

        return InlineKeyboardMarkup(keyboard, one_time_keyboard=True)

    def getResponse(self, update: Updater, context: CallbackContext):

        if not self._checkifallowed(update.effective_user.id, update):
            return

        query = update.callback_query
        query.answer()

        if query.data == "cancel":
            query.edit_message_text("\U00002757 User Cancelled Request", parse_mode='HTML')

        elif query.data == "margin":
            self.askMarginType(update)
        elif query.data in ("margin_orders", "margin_pairs", "margin_all"):
            self.getMargins(update)

        elif query.data == "status":
            self.getBotInfo(update)

        elif query.data == "showconfig":
            self.askConfigOptions(update)
        elif query.data.__contains__("ex_"):
            actions.showconfigresponse(update)
            
        elif query.data == "start":
            control.askStartBotList(update)
        elif query.data.__contains__("start_"):
            control.startBotResponse(update)

        elif query.data == "stop":
            control.askStopBotList(update)
        elif query.data.__contains__("stop_"):
            control.stopBotResponse(update)

        elif query.data == "pause":
            control.askPauseBotList(update)
        elif query.data.__contains__("pause_"):
            control.pauseBotResponse(update)

        elif query.data == "resume":
            control.askResumeBotList(update)
        elif query.data.__contains__("resume_"):
            control.resumeBotResponse(update)

        elif query.data == "restart":
            control.askRestartBot(update)
        elif query.data.__contains__("restart_"):
            control.restartBotResponse(update)

        elif query.data == "reopen":
            actions.startOpenOrders(update)

        elif query.data == "buy":
            control._askBotList(update, "buy", "active")
        elif query.data.__contains__("buy_"):
            actions.buyresponse(update)

        elif query.data == "sell":
            control._askBotList(update, "sell", "active")
        elif query.data.__contains__("sell_"):
            actions.sellresponse(update)

        

    def askMarginType(self, update):
        """Ask what user wants to see active order/pairs or all"""
        query = update.callback_query

        keyboard = [
            [
                InlineKeyboardButton("Active Orders", callback_data="margin_orders"),
                InlineKeyboardButton("Active Pairs", callback_data="margin_pairs"),
                InlineKeyboardButton("All", callback_data="margin_all"),
            ],
            [InlineKeyboardButton("Cancel", callback_data="cancel")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)

        try:
            query.edit_message_text("<b>Make your selection</b>", reply_markup=reply_markup, parse_mode="HTML")
        except:
            update.message.reply_text("Make your selection", reply_markup=reply_markup)

    def getMargins(self, response):

        query = response.callback_query
        query.answer()

        closeoutput = "" 
        openoutput = ""
        for file in helper.getActiveBotList():
            helper.read_data(file)
            if "margin" in helper.data:
                if "margin" in helper.data and helper.data["margin"] == " ":
                    closeoutput = (closeoutput + f"<b>{file}</b>")
                    closeoutput = closeoutput + f"\n<i>{helper.data['message']}</i>\n"
                elif len(helper.data) > 2:
                    space = 20 - len(file)
                    margin_icon = ("\U0001F7E2" if "-" not in helper.data["margin"]else "\U0001F534")
                    openoutput = (openoutput + f"\U0001F4C8 <b>{file}</b> ".ljust(space))
                    openoutput = (openoutput + f" {margin_icon}<i>Current Margin: {helper.data['margin']}  \U0001F4B0 (P/L): {helper.data['delta']}</i>\n")
        
        if query.data.__contains__("orders"):
            query.edit_message_text("<b>No open orders found.</b>" if openoutput == "" else f"<b>Open Order(s)</b>\n{openoutput}", parse_mode="HTML")

        elif query.data.__contains__("pairs"):
            query.edit_message_text("<b>No active pairs found.</b>" if closeoutput == "" else f"<b>Active Pair(s)</b>\n{closeoutput}", parse_mode="HTML")

        elif query.data.__contains__("all"):
            query.edit_message_text(f"<b>Open Order(s)</b>\n{openoutput}", parse_mode="HTML")
            response.effective_message.reply_html(f"<b>Active Pair(s)</b>\n{closeoutput}")

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

    def getBotInfo(self, update):
        query = update.callback_query
        try:
            query.answer()
        except:
            pass
        count = 0
        for file in helper.getActiveBotList():
            output = ""
            count += 1
            helper.read_data(file)

            output = output + f"\U0001F4C8 <b>{file}</b> "

            last_modified = datetime.now() - datetime.fromtimestamp(
                os.path.getmtime(
                    os.path.join(self.datafolder, "telegram_data", f"{file}.json")
                )
            )

            icon = "\U0001F6D1" # red dot
            if last_modified.seconds > 90 and last_modified.seconds != 86399:
                output = f"{output} {icon} <b>Status</b>: <i>defaulted</i>"
            elif "botcontrol" in helper.data and "status" in helper.data["botcontrol"]:
                if helper.data["botcontrol"]["status"] == "active":
                    icon = "\U00002705" # green tick
                if helper.data["botcontrol"]["status"] == "paused":
                    icon = "\U000023F8" # pause icon
                if helper.data["botcontrol"]["status"] == "exit":
                    icon = "\U0000274C" # stop icon
                output = f"{output} {icon} <b>Status</b>: <i>{helper.data['botcontrol']['status']}</i>"
                output = f"{output} \u23F1 <b>Uptime</b>: <i>{self._getUptime(helper.data['botcontrol']['started'])}</i>\n"
            else:
                output = f"{output} {icon} <b>Status</b>: <i>stopped</i> "

            if count == 1:
                try:
                    query.edit_message_text(f"{output}", parse_mode="HTML")
                except:
                    update.effective_message.reply_html(f"{output}")
            else:
                update.effective_message.reply_html(f"{output}")
            sleep(0.2)

        update.effective_message.reply_html(f"<b>Bot Count ({count})</b>")

    def askConfigOptions(self, update: Updater):
        keyboard = []
        # print(helper.config.config)
        for exchange in helper.config:
            if not exchange == "telegram":
                keyboard.append(
                    [InlineKeyboardButton(exchange, callback_data="ex_" + exchange)]
                )

        reply_markup = InlineKeyboardMarkup(keyboard)
        query = update.callback_query
        query.answer()
        query.edit_message_text("Select exchange", reply_markup=reply_markup)

    def sellrequest(self, update):
        """Manual sell request (asks which coin to sell)"""
        control._askBotList(update, "sell", "active")

    def buyrequest(self, update):
        """Manual buy request"""
        control._askBotList(update, "buy", "active")