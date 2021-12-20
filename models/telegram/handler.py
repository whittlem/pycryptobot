# import os
# from time import sleep

# from datetime import datetime

from models.telegram.control import TelegramControl
from models.telegram.helper import TelegramHelper
from models.telegram.actions import TelegramActions
from models.telegram.config import ConfigEditor

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update

from telegram.ext.callbackcontext import CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler

scannerSchedule = BackgroundScheduler(timezone="UTC")

class TelegramHandler:
    def __init__(self, datafolder, authuserid, tg_helper: TelegramHelper) -> None:
        self.authoriseduserid = authuserid
        self.datafolder = datafolder
        self.helper = tg_helper

        self.control = TelegramControl(self.datafolder, tg_helper)
        self.actions = TelegramActions(self.datafolder, tg_helper)
        self.editor = ConfigEditor(self.datafolder, tg_helper)

    def _checkifallowed(self, userid, update) -> bool:
        if str(userid) != self.authoriseduserid:
            update.message.reply_text("<b>Not authorised!</b>", parse_mode="HTML")
            return False

        return True

    def getRequest(self) -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton(
                    "\U0001F4D6 View config", callback_data="showconfig"
                ),
                InlineKeyboardButton(
                    "\U0001F510 Edit config \U00002699", callback_data="editconfig"
                ),
            ],
            [
                InlineKeyboardButton("\U0001F4B0 Sell", callback_data="sell"),
                InlineKeyboardButton("\U0001FA99 Buy", callback_data="buy"),
            ],
            [
                InlineKeyboardButton(
                    "\U0001F50E Market Scanner", callback_data="scanner"
                ),
            ],
            [
                InlineKeyboardButton(
                    "\U0001F9FE Restart open orders", callback_data="reopen"
                ),
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
                InlineKeyboardButton(
                    "\U0000267B Restart active bots", callback_data="restart"
                ),
            ],
            [
                InlineKeyboardButton("\U00002139 Bot Status", callback_data="status"),
                InlineKeyboardButton("Margins \U0001F4C8", callback_data="margin"),
            ],
            [InlineKeyboardButton("Cancel", callback_data="cancel")],
        ]

        return InlineKeyboardMarkup(keyboard, one_time_keyboard=True)

    def getResponse(self, update: Update, context: CallbackContext):

        if not self._checkifallowed(update.effective_user.id, update):
            return

        query = update.callback_query
        query.answer()

        if query.data == "cancel":
            query.edit_message_text(
                "\U00002757 User Cancelled Request", parse_mode="HTML"
            )

        if query.data == "back":
            key_markup = self.getRequest()
            query.edit_message_text(
                "<b>PyCryptoBot Command Panel.</b>",
                reply_markup=key_markup,
                parse_mode="HTML",
            )

        elif query.data == "margin":
            self.askMarginType(update)
        elif query.data in ("margin_orders", "margin_pairs", "margin_all"):
            self.actions.getMargins(update)

        elif query.data == "status":
            self.actions.getBotInfo(update)

        elif query.data == "showconfig":
            self.askConfigOptions(update)
        elif query.data.__contains__("ex_"):
            self.actions.showconfigresponse(update)

        elif query.data == "restart":
            self.control.askRestartBotList(update)
        elif query.data.__contains__("restart_"):
            self.control.restartBotResponse(update)
            
        elif query.data == "start":
            self.control.askStartBotList(update)
        elif query.data.__contains__("start_"):
            self.control.startBotResponse(update)

        elif query.data == "stop":
            self.control.askStopBotList(update)
        elif query.data.__contains__("stop_"):
            self.control.stopBotResponse(update)

        elif query.data == "pause":
            self.control.askPauseBotList(update)
        elif query.data.__contains__("pause_"):
            self.control.pauseBotResponse(update)

        elif query.data == "resume":
            self.control.askResumeBotList(update)
        elif query.data.__contains__("resume_"):
            self.control.resumeBotResponse(update)

        elif query.data == "reopen":
            self.actions.startOpenOrders(update)

        elif query.data == "buy":
            self.control.askBuyBotList(update)
        elif query.data.__contains__("confirm_buy_"):
            self.actions.buyresponse(update)
        elif query.data.__contains__("buy_"):
            self.askConfimation(update)

        elif query.data == "sell":
            self.control.askSellBotList(update)
        elif query.data.__contains__("confirm_sell_"):
            self.actions.sellresponse(update)
        elif query.data.__contains__("sell_"):
            self.askConfimation(update)

        elif query.data == "delete":
            self.control.askDeleteBotList(update)
        elif query.data.__contains__("delete_"):
            self.actions.deleteresponse(update)

        elif query.data == "scanner":
            self.getScannerOptions(update)
        elif query.data == "schedule":
            self._checkScheduledJob(update)
        elif query.data == "scanonly" or query.data == "noscan" or query.data == "startmarket":
            if query.data == "startmarket":
                self._checkScheduledJob(update)
            self.actions.StartMarketScan(update, True if query.data != "noscan" else False, True if query.data != "scanonly" else False)
        elif query.data == "stopmarket":
            self._removeScheduledJob(update)

        elif query.data == "editconfig":
            query.edit_message_text(
                "\U000026A0 <b>Under Construction</b> \U000026A0", parse_mode="HTML"
            )
            # key_markup = self.getConfigOptions()
            # query.edit_message_text(
            #     "<b>PyCryptoBot Config Panel.</b>",
            #     reply_markup=key_markup,
            #     parse_mode="HTML")

        elif query.data.__contains__("edit_"):
            self.editor.ask_buy_max_size(query, context)

        elif query.data.__contains__("delexcep_"):
            self.actions.RemoveExceptionCallBack(update)

    def getScannerOptions(self, update):
        query = update.callback_query

        keyboard = [
            [
                InlineKeyboardButton("Add Schedule", callback_data="schedule")
            ],
            [
                InlineKeyboardButton("Remove Schedule", callback_data="stopmarket"),
            ],
            [
                InlineKeyboardButton("Scan Only", callback_data="scanonly"),
                InlineKeyboardButton("Start Bots Only", callback_data="noscan")
            ],
            [
                InlineKeyboardButton("Scan + Start Bots", callback_data="startmarket")
            ],
            [InlineKeyboardButton("\U000025C0 Back", callback_data="back")],
        ]

        query.edit_message_text(
            "<b>Scanning Options.</b>",
            reply_markup=InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
            parse_mode="HTML")

    def getConfigOptions(self):
        keyboard = [
            [
                InlineKeyboardButton("BuyMaxSize", callback_data="edit_buymaxsize"),
            ],
            [InlineKeyboardButton("\U000025C0 Back", callback_data="back")],
        ]

        return InlineKeyboardMarkup(keyboard, one_time_keyboard=True)

    def askMarginType(self, update):
        """Ask what user wants to see active order/pairs or all"""
        query = update.callback_query

        keyboard = [
            [
                InlineKeyboardButton("Active Orders", callback_data="margin_orders"),
                InlineKeyboardButton("Active Pairs", callback_data="margin_pairs"),
                InlineKeyboardButton("All", callback_data="margin_all"),
            ],
            [InlineKeyboardButton("\U000025C0 Back", callback_data="back")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)

        try:
            query.edit_message_text(
                "<b>Make your selection</b>",
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        except:
            update.message.reply_text("Make your selection", reply_markup=reply_markup)

    def askConfigOptions(self, update: Update):
        keyboard = []
        buttons = []
        for exchange in self.helper.config:
            if not exchange == "telegram":
                buttons.append(
                    InlineKeyboardButton(exchange, callback_data="ex_" + exchange)
                )

        i = 0
        while i <= len(buttons) - 1:
            if len(buttons) - 1 >= i + 2:
                keyboard.append([buttons[i], buttons[i + 1], buttons[i + 2]])
            elif len(buttons) - 1 >= i + 1:
                keyboard.append([buttons[i], buttons[i + 1]])
            else:
                keyboard.append([buttons[i]])
            i += 3

            keyboard.append(
                [InlineKeyboardButton("\U000025C0 Back", callback_data="back")]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)
        query = update.callback_query
        query.answer()
        query.edit_message_text(
            "<b>Select exchange</b>", reply_markup=reply_markup, parse_mode="HTML"
        )

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
            query.edit_message_text(
                f"<b>Are you sure you want to {query.data.replace('_', ' ')}?</b>",
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        except:
            update.message.reply_text(
                f"<b>Are you sure you want to {query.data.replace('_', ' ')}?</b>",
                reply_markup=reply_markup,
                parse_mode="HTML",
            )

    def _checkScheduledJob(self, update):
        if (
            self.helper.config["scanner"]["autoscandelay"] > 0
            and len(scannerSchedule.get_jobs()) == 0
        ):
            scannerSchedule.start()
            scannerSchedule.add_job(
                self.actions.StartMarketScan,
                args=(update, False, True),
                trigger="interval",
                minutes=self.helper.config["scanner"]["autoscandelay"] * 60,
                name="Volume Auto Scanner",
                misfire_grace_time=10,
            )

            try:
                query = update.callback_query
                query.edit_message_text(
                    f"<b>Scan job schedule created to run every {self.helper.config['scanner']['autoscandelay']} hour(s)</b> \u2705", parse_mode="HTML"
                )
            except:
                update.message.reply_text(f"<b>Scan job schedule created to run every {self.helper.config['scanner']['autoscandelay']} hour(s)</b> \u2705", parse_mode="HTML")

    def _removeScheduledJob(self, update):
        try:
            query = update.callback_query
            query.answer()
        except:
            pass

        reply = ""
        if len(scannerSchedule.get_jobs()) > 0:
            scannerSchedule.shutdown()
            reply = "Scan job schedule has been removed"

        else:
            reply = "No scheduled job found"

        try:
            query.edit_message_text(f"<b>{reply}</b> \u2705", parse_mode="HTML")
        except:
            update.message.reply_text(f"<b>{reply}</b> \u2705", parse_mode="HTML")