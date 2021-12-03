import os
from time import sleep
from datetime import datetime

from models.telegram.control import TelegramControl
from models.telegram.helper import TelegramHelper
from models.telegram.actions import TelegramActions

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater
from telegram.ext.callbackcontext import CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler

helper = None
control = None
actions = None

scannerSchedule = BackgroundScheduler(timezone='UTC')

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
                InlineKeyboardButton("\U0001F4D6 View config", callback_data="showconfig"),
                InlineKeyboardButton("\U0001F510 Edit config \U00002699", callback_data="editconfig"),
            ],
            [
                InlineKeyboardButton("\U0001F4B0 Sell", callback_data="sell"),
                InlineKeyboardButton("\U0001FA99 Buy", callback_data="buy"),
            ],
            # [
            #     InlineKeyboardButton("Scanner Exceptions", callback_data="exception"),
            # ],
            [
                InlineKeyboardButton("Stop Market Scanner", callback_data="stopmarket"),
            ],
            [
                InlineKeyboardButton("\U0001F50E Start Market Scanner", callback_data="startmarket"),
            ],
            [
                InlineKeyboardButton("\U0001F9FE Restart open orders", callback_data="reopen"),
            ],
            [
                InlineKeyboardButton("\U000023F8 pausebot(s)", callback_data="pause"),
                InlineKeyboardButton("resumebot(s) \U0000267B", callback_data="resume"),
            ],
            [
                InlineKeyboardButton("\U0001F7E2 startbot(s)", callback_data="start"),
                InlineKeyboardButton("stopbot(s) \U0001F534", callback_data="stop"),
            ],
            [
                InlineKeyboardButton("\U00002139 Bot Status", callback_data="status"),
                InlineKeyboardButton("Margins \U0001F4C8", callback_data="margin"),
            ],
            [
                InlineKeyboardButton("Cancel", callback_data="cancel")
            ],
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
            actions.getBotInfo(update)

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
            control.askRestartBotList(update)
        elif query.data.__contains__("restart_"):
            control.restartBotResponse(update)

        elif query.data == "reopen":
            actions.startOpenOrders(update)

        elif query.data == "buy":
            control.askBuyBotList(update)
        elif query.data.__contains__("confirm_buy_"):
            actions.buyresponse(update)
        elif query.data.__contains__("buy_"):
            self.askConfimation(update)

        elif query.data == "sell":
            control.askSellBotList(update)
        elif query.data.__contains__("confirm_sell_"):
            actions.sellresponse(update)
        elif query.data.__contains__("sell_"):
            self.askConfimation(update)

        elif query.data == "delete":
            control.askDeleteBotList(update)
        elif query.data.__contains__("delete_"):
            actions.deleteresponse(update)

        elif query.data == "startmarket":
            self._checkScheduledJob(update)
            actions.StartMarketScan(update)
        elif query.data == "stopmarket":
            self._removeScheduledJob(update)
# 
#         elif query.data == "exception":
#             # self._checkScheduledJob(update)
#             actions.StartMarketScan(update)


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

        # closeoutput = "" 
        output = ""
        closedbotCount = 0
        openbotCount = 0
        for file in helper.getActiveBotList():
            helper.read_data(file)
            output = ""
            if "margin" in helper.data:
                if "margin" in helper.data and helper.data["margin"] == " ":
                    output = (output + f"<b>{file}</b>")
                    output = output + f"\n<i>{helper.data['message']}</i>\n"
                    closedbotCount += 1
                elif len(helper.data) > 2:
                    space = 20 - len(file)
                    margin_icon = ("\U0001F7E2" if "-" not in helper.data["margin"]else "\U0001F534")
                    output = (output + f"\U0001F4C8 <b>{file}</b> ".ljust(space))
                    output = (output + f" {margin_icon}  <i>Current Margin: {helper.data['margin']} \U0001F4B0 (P/L): {helper.data['delta']}</i>\n      (TSL Trg): {helper.data['trailingstoplosstriggered']}  --  (TSL Change): {helper.data['change_pcnt_high']}\n")
                    openbotCount += 1
                if closedbotCount + openbotCount == 1:
                    try:
                        query.edit_message_text(f"{output}", parse_mode="HTML")
                    except:
                        response.effective_message.reply_html(f"{output}")
                else:
                    response.effective_message.reply_html(f"{output}")

        if (query.data.__contains__("orders") or query.data.__contains__("all")) and openbotCount == 0:
            query.edit_message_text("<b>No open orders found.</b>", parse_mode="HTML")

        elif (query.data.__contains__("pairs") or query.data.__contains__("all")) and closedbotCount == 0:
            query.edit_message_text("<b>No active pairs found.</b>", parse_mode="HTML")

    def askConfigOptions(self, update: Updater):
        keyboard = []
        for exchange in helper.config:
            if not exchange == "telegram":
                keyboard.append(
                    [InlineKeyboardButton(exchange, callback_data="ex_" + exchange)]
                )

        reply_markup = InlineKeyboardMarkup(keyboard)
        query = update.callback_query
        query.answer()
        query.edit_message_text("Select exchange", reply_markup=reply_markup)

    def askConfimation(self, update):

        query = update.callback_query
        keyboard = [
            [
                InlineKeyboardButton("Confirm", callback_data=f"confirm_{query.data}"),
            ],
            [InlineKeyboardButton("Cancel", callback_data="cancel")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)

        try:
            query.edit_message_text(f"<b>Are you sure you want to {query.data.replace('_', ' ')}?</b>", reply_markup=reply_markup, parse_mode="HTML")
        except:
            update.message.reply_text(f"<b>Are you sure you want to {query.data.replace('_', ' ')}?</b>", reply_markup=reply_markup, parse_mode="HTML")

    def _checkScheduledJob(self, update):
        if helper.config["scanner"]["autoscandelay"] > 0 and len(scannerSchedule.get_jobs()) == 0:
            scannerSchedule.start()
            scannerSchedule.add_job(actions.StartMarketScan, args=(update, False, True), trigger='interval', minutes=helper.config["scanner"]["autoscandelay"]*60, name='Volume Auto Scanner', misfire_grace_time=10)
            # scannerSchedule.start()
            update.effective_message.reply_html(
                f"<b>Scan job schedule created to run every {helper.config['scanner']['autoscandelay']} hour(s)</b> \u2705"
            )

    def _removeScheduledJob(self, update):
        scannerSchedule.shutdown()
        query = update.callback_query
        query.answer()
        query.edit_message_text("<b>Scan job schedule has been removed</b> \u2705", parse_mode="HTML")