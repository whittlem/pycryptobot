''' Telegram Bot Control '''
from time import sleep
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update

from .helper import TelegramHelper

class TelegramControl:
    ''' Telegram Bot Control Class '''
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder
        self.helper = tg_helper

    def _ask_bot_list(self, update: Update, call_back_tag, status):
        ''' Get list of {status} bots '''
        buttons = []

        for market in self.helper.get_active_bot_list(status):
            while self.helper.read_data(market) is False:
                sleep(0.2)

            if "botcontrol" in self.helper.data:
                if "margin" in self.helper.data:
                    if call_back_tag == "buy" and self.helper.data["margin"] == " ":
                        buttons.append(
                            InlineKeyboardButton(
                                market, callback_data=f"{call_back_tag}_{market}"
                            )
                        )
                    elif call_back_tag == "sell" and self.helper.data["margin"] != " ":
                        buttons.append(
                            InlineKeyboardButton(
                                market, callback_data=f"{call_back_tag}_{market}"
                            )
                        )
                    elif call_back_tag not in ("buy", "sell"):
                        buttons.append(
                            InlineKeyboardButton(
                                market, callback_data=f"{call_back_tag}_{market}"
                            )
                        )

        if len(buttons) > 0:
            self.helper.send_telegram_message(
                update,
                f"<b>What do you want to {call_back_tag}?</b>",
                self.sort_inline_buttons(buttons, f"{call_back_tag}"),
            )
        else:
            self.helper.send_telegram_message(update, f"<b>No {status} bots found.</b>")

    def sort_inline_buttons(self, buttons: list, call_back_tag):
        ''' Sort buttons for inline keyboard display '''
        keyboard = []
        if len(buttons) > 0:
            if len(buttons) > 1 and call_back_tag not in ("bot"):
                keyboard = [
                    [InlineKeyboardButton("All", callback_data=f"{call_back_tag}_all")]
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

            if call_back_tag not in ("start", "resume", "buy", "sell", "bot"):
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "All (w/o open order)",
                            callback_data=f"{call_back_tag}_allclose",
                        )
                    ]
                )

            keyboard.append(
                [InlineKeyboardButton("\U000025C0 Back", callback_data="back")]
            )

        return InlineKeyboardMarkup(keyboard)

    def action_bot_response(
        self, update: Update, call_back_tag, state, context, status: str = "active"
    ):
        ''' Run requested bot action '''
        query = update.callback_query

        mode = call_back_tag.capitalize()
        # mode = "Stopping" if callbackTag == "stop" else "Pausing"
        if query.data.__contains__("allclose") or query.data.__contains__("all"):
            self.helper.send_telegram_message(update, f"<i>{mode} bots</i>", context=context)

            for pair in self.helper.get_active_bot_list(status):
                self.helper.stop_running_bot(
                    pair, state, False if query.data.__contains__("allclose") else True
                )
                sleep(1)
        else:
            self.helper.send_telegram_message(update, f"<i>{mode} bots</i>", context=context)
            self.helper.stop_running_bot(
                str(query.data).replace(f"{call_back_tag}_", ""), state, True
            )

        update.effective_message.reply_html("<b>Operation Complete</b>")

    def ask_start_bot_list(self, update: Update):
        ''' Get bot start list '''
        buttons = []
        self.helper.read_data()
        for market in self.helper.data["markets"]:
            if not self.helper.is_bot_running(market):
                buttons.append(
                    InlineKeyboardButton(market, callback_data="start_" + market)
                )

        if len(buttons) > 0:
            reply_markup = self.sort_inline_buttons(buttons, "start")
            self.helper.send_telegram_message(
                update, "<b>What crypto bots do you want to start?</b>", reply_markup
            )
        else:
            self.helper.send_telegram_message(
                update, "<b>Nothing on your start list</b>\n<i>Use /addnew to add a market.</i>"
            )

    def start_bot_response(self, update: Update, context):
        ''' Start bot list response '''
        query = update.callback_query

        self.helper.read_data()

        if "all" in query.data:  # start all bots
            self.helper.send_telegram_message(update, "<b>Starting all bots</b>", context=context)

            for market in self.helper.data["markets"]:
                if not self.helper.is_bot_running(market):
                    overrides = self.helper.data["markets"][market]["overrides"]
                    update.effective_message.reply_html(
                        f"<i>Starting {market} crypto bot</i>"
                    )
                    self.helper.start_process(market, "", overrides)
                    sleep(10)
                else:
                    update.effective_message.reply_html(
                        f"{market} is already running, no action taken."
                    )

        else:  # start single bot
            self.helper.send_telegram_message(
                update,
                f"<i>Starting {str(query.data).replace('start_', '')} crypto bot</i>", context=context
            )

            if not self.helper.is_bot_running(str(query.data).replace("start_", "")):
                overrides = self.helper.data["markets"][
                    str(query.data).replace("start_", "")
                ]["overrides"]
                self.helper.start_process(
                    str(query.data).replace("start_", ""), "", overrides
                )
            else:
                update.effective_message.reply_html(
                    f"{str(query.data).replace('start_', '')} is already running, no action taken."
                )

    def ask_stop_bot_list(self, update: Update):
        ''' Get bot stop list '''
        self._ask_bot_list(update, "stop", "active")

    def stop_bot_response(self, update: Update, context):
        ''' Stop bot list response '''
        self.action_bot_response(update, "stop", "exit", context, "active")

    def ask_pause_bot_list(self, update: Update):
        ''' Get pause bot list '''
        self._ask_bot_list(update, "pause", "active")

    def pause_bot_response(self, update: Update, context):
        ''' Pause bot list response '''
        self.action_bot_response(update, "pause", "pause", context, "active")

    def ask_resume_bot_list(self, update: Update):
        ''' Get resume bot list '''
        self._ask_bot_list(update, "resume", "paused")

    def resume_bot_response(self, update: Update, context):
        ''' Resume bot list response '''
        self.action_bot_response(update, "resume", "start", context, "paused")

    def ask_sell_bot_list(self, update):
        """Manual sell request (asks which coin to sell)"""
        self._ask_bot_list(update, "sell", "active")

    def ask_buy_bot_list(self, update):
        """Manual buy request"""
        self._ask_bot_list(update, "buy", "active")

    def ask_restart_bot_list(self, update: Update):
        ''' Get restart bot list '''
        self._ask_bot_list(update, "restart", "active")

    def restart_bot_response(self, update: Update):
        ''' Restart bot list response '''
        query = update.callback_query
        bot_list = {}
        for bot in self.helper.get_active_bot_list():
            while self.helper.read_data(bot) is False:
                sleep(0.2)
            if query.data.__contains__("all"):
                bot_list.update(
                    {
                        bot: {
                            "exchange": self.helper.data["exchange"],
                            "startmethod": self.helper.data["botcontrol"]["startmethod"],
                        }
                    }
                )
            elif query.data.__contains__(bot):
                bot_list.update(
                    {
                        bot: {
                            "exchange": self.helper.data["exchange"],
                            "startmethod": self.helper.data["botcontrol"]["startmethod"],
                        }
                    }
                )

        self.action_bot_response(update, "restart", "exit", "active")
        sleep(1)

        for bot in bot_list.items():
            self.helper.start_process(
                bot[0], bot[1]["exchange"], "", bot[1]["startmethod"]
            )
            sleep(10)

    def ask_config_options(self, update: Update):
        ''' Get available exchanges from config '''
        keyboard = []
        for exchange in self.helper.config:
            if not exchange == "telegram":
                keyboard.append(
                    [InlineKeyboardButton(exchange, callback_data=exchange)]
                )

        reply_markup = InlineKeyboardMarkup(keyboard)

        self.helper.send_telegram_message(update, "Select exchange", reply_markup)

    def ask_delete_bot_list(self, update: Update):
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

        self.helper.send_telegram_message(
            update, "<b>What crypto bots do you want to delete?</b>", reply_markup
        )

    def ask_exception_bot_list(self, update):
        """ask which bot to delete"""
        buttons = []
        keyboard = []

        self.helper.read_data()
        for pair in self.helper.data["scannerexceptions"]:
            buttons.append(InlineKeyboardButton(pair, callback_data="delexcep_" + pair))

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

        self.helper.send_telegram_message(
            update,
            "<b>What do you want to remove from the scanner exception list?</b>",
            reply_markup,
        )
