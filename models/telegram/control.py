from time import sleep
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update

from .helper import TelegramHelper

helper = None

class TelegramControl():
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder
        self.helper = tg_helper
    
    def _sortInlineButtons(self, buttons: list, callbackTag):
        keyboard = []
        if len(buttons) > 0:
            if (callbackTag not in ("buy", "sell")) and len(buttons) > 1:
                keyboard = [[InlineKeyboardButton("All", callback_data=f"{callbackTag}_all")]]

            i = 0
            while i <= len(buttons) - 1:
                if len(buttons) - 1 >= i + 2:
                    keyboard.append([buttons[i], buttons[i + 1], buttons[i + 2]])
                elif len(buttons) - 1 >= i + 1:
                    keyboard.append([buttons[i], buttons[i + 1]])
                else:
                    keyboard.append([buttons[i]])
                i += 3

            if callbackTag not in ("start", "resume", "buy", "sell"):
                keyboard.append([InlineKeyboardButton("All (w/o open order)", callback_data=f"{callbackTag}_allclose")])

            keyboard.append([InlineKeyboardButton("\U000025C0 Back", callback_data="back")])

        return InlineKeyboardMarkup(keyboard)

    def _askBotList(self, update: Update, callbackTag, status):
        query = update.callback_query
        try:
            query.answer()
        except:
            pass

        buttons = []

        for market in self.helper.getActiveBotList(status):
            while self.helper.read_data(market) == False:
                sleep(0.2)

            if "botcontrol" in self.helper.data:
                if callbackTag == "buy" and "margin" in self.helper.data and self.helper.data["margin"] == " ":
                    buttons.append(InlineKeyboardButton(market, callback_data=f"{callbackTag}_{market}"))
                elif callbackTag == "sell" and "margin" in self.helper.data and self.helper.data["margin"] != " ":
                    buttons.append(InlineKeyboardButton(market, callback_data=f"{callbackTag}_{market}"))
                elif callbackTag not in ("buy", "sell"):
                    buttons.append(InlineKeyboardButton(market, callback_data=f"{callbackTag}_{market}"))

        if len(buttons) > 0:
            try:
                query.edit_message_text(f"<b>What do you want to {callbackTag}?</b>",
                    reply_markup=self._sortInlineButtons(buttons, f"{callbackTag}"),
                    parse_mode="HTML")
            except:
                update.effective_message.reply_html(
                    f"<b>What do you want to {callbackTag}?</b>",
                    reply_markup=self._sortInlineButtons(buttons, f"{callbackTag}"))
        else:
            try:
                query.edit_message_text(f"<b>No {status} bots found.</b>", parse_mode="HTML")
            except:
                update.effective_message.reply_html(f"<b>No {status} bots found.</b>")

    def _actionBotResponse(self, update: Update, callbackTag, state, status: str = "active"):
        query = update.callback_query
        try:
            query.answer()
        except:
            pass
        
        mode = "Stopping" if callbackTag == "stop" else "Pausing"
        if query.data.__contains__("allclose") or query.data.__contains__("all"):
            query.edit_message_text(f"<i>{mode} bots</i>", parse_mode="HTML")

            for pair in self.helper.getActiveBotList(status):
                self.helper.stopRunningBot(pair, state, False if query.data.__contains__("allclose") else True)
                sleep(1)
        else:
            self.helper.stopRunningBot(str(query.data).replace(f"{callbackTag}_", ""), state, True)
            # query.edit_message_text(
            #         f"{mode} {str(query.data).replace(f'{callbackTag}_', '')} crypto bot"
            #     )

        update.effective_message.reply_html("<b>Operation Complete</b>")
        # query.edit_message_text("Operation Complete")

    def askStartBotList(self, update: Update):
        query = update.callback_query
        try:
            query.answer()
        except:
            pass

        buttons = []
        self.helper.read_data()
        for market in self.helper.data["markets"]:
            if not self.helper.isBotRunning(market):
                buttons.append(InlineKeyboardButton(market, callback_data="start_" + market))

        reply_markup = self._sortInlineButtons(buttons, "start")

        try:
            query.edit_message_text("<b>What crypto bots do you want to start?</b>",
            reply_markup=reply_markup,
            parse_mode="HTML")
        except:
            update.effective_message.reply_html("<b>What crypto bots do you want to start?</b>",
            reply_markup=reply_markup)

    def startBotResponse(self, update: Update):
        query = update.callback_query
        try:
            query.answer()
        except:
            pass

        self.helper.read_data()

        if "all" in query.data: # start all bots
            try:
                query.edit_message_text("<b>Starting all bots</b>", parse_mode="HTML")
            except:
                update.effective_message.reply_html("<b>Starting all bots</b>")

            for market in self.helper.data["markets"]:
                if not self.helper.isBotRunning(market):
                    overrides = self.helper.data["markets"][market]["overrides"]
                    update.effective_message.reply_html(f"<i>Starting {market} crypto bot</i>")
                    self.helper.startProcess(market, "", overrides)
                else:
                    update.effective_message.reply_html(f"{market} is already running, no action taken.")

        else: # start single bot
            try:
                query.edit_message_text(f"<i>Starting {str(query.data).replace('start_', '')} crypto bot</i>", parse_mode="HTML")
            except:
                update.effective_message.reply_html(f"<i>Starting {str(query.data).replace('start_', '')} crypto bot</i>")

            if not self.helper.isBotRunning(str(query.data).replace("start_", "")):
                overrides = self.helper.data["markets"][str(query.data).replace("start_", "")]["overrides"]
                self.helper.startProcess(str(query.data).replace("start_", ""), "", overrides)
            else:
                update.effective_message.reply_html(f"{str(query.data).replace('start_', '')} is already running, no action taken.")

    def askStopBotList(self, update: Update):
        self._askBotList(update, "stop", "active")

    def stopBotResponse(self, update: Update):
        self._actionBotResponse(update, "stop", "exit", "active")

    def askPauseBotList(self, update: Update):
        self._askBotList(update, "pause", "active")

    def pauseBotResponse(self, update: Update):
        self._actionBotResponse(update, "pause", "pause", "active")

    def askResumeBotList(self, update: Update):
        self._askBotList(update, "resume", "paused")

    def resumeBotResponse(self, update: Update):
        self._actionBotResponse(update, "resume", "start", "pause")

    def askSellBotList(self, update):
        """Manual sell request (asks which coin to sell)"""
        self._askBotList(update, "sell", "active")

    def askBuyBotList(self, update):
        """Manual buy request"""
        self._askBotList(update, "buy", "active")

    def askRestartBotList(self, update: Update):
        self._askBotList(update, "restart", "active")

    def restartBotResponse(self, update: Update):

        bList = {}
        for bot in self.helper.getActiveBotList():
            while self.helper.read_data(bot) == False:
                sleep(0.2)
            # self.helper.read_data(bot)
            bList.update({bot : {"exchange" : self.helper.data["exchange"], "startmethod" : self.helper.data["botcontrol"]["startmethod"]}})

        self._actionBotResponse(update, "stop", "exit", "active")
        sleep(1)
        allstopped = False
        while allstopped == False:
            if len(self.helper.getActiveBotList()) == 0:
                allstopped = True

        for bot in bList:
            self.helper.startProcess(bot, bList[bot]["exchange"], "", bList[bot]["startmethod"])
            sleep(10)

    def askConfigOptions(self, update: Update):
        keyboard = []
        for exchange in self.helper.config:
            if not exchange == "telegram":
                keyboard.append(
                    [InlineKeyboardButton(exchange, callback_data=exchange)]
                )

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Select exchange", reply_markup=reply_markup)

    def askDeleteBotList(self, update: Update):
        """ask which bot to delete"""
        buttons = []
        keyboard = []

        self.helper.read_data()
        for market in self.helper.data["markets"]:
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

    def askExceptionBotList(self, update):
        """ask which bot to delete"""
        buttons = []
        keyboard = []

        self.helper.read_data()
        for pair in self.helper.data["scannerexceptions"]:
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
