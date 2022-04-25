""" Telegram Bot Control """
from time import sleep
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext.callbackcontext import CallbackContext
from models.telegram import callbacktags

from .helper import TelegramHelper


class TelegramControl:
    """Telegram Bot Control Class"""

    def __init__(self, tg_helper: TelegramHelper) -> None:
        self.helper = tg_helper

    def _ask_bot_list(self, update: Update, call_back_tag, status):
        """Get list of {status} bots"""
        buttons = []

        for market in self.helper.get_active_bot_list(status):
            if self.helper.read_data(market) and "botcontrol" in self.helper.data:
                if "margin" in self.helper.data:
                    if (
                        call_back_tag == callbacktags.BUY
                        and self.helper.data["margin"] == " "
                    ):
                        buttons.append(
                            InlineKeyboardButton(
                                market,
                                callback_data=self.helper.create_callback_data(
                                    call_back_tag[0], "", market
                                ),  # f"{call_back_tag}_{market}"
                            )
                        )
                    elif (
                        call_back_tag == callbacktags.SELL
                        and self.helper.data["margin"] != " "
                    ):
                        buttons.append(
                            InlineKeyboardButton(
                                market,
                                callback_data=self.helper.create_callback_data(
                                    call_back_tag[0], "", market
                                ),  # f"{call_back_tag}_{market}"
                            )
                        )
                    elif call_back_tag not in (callbacktags.BUY, callbacktags.SELL):
                        buttons.append(
                            InlineKeyboardButton(
                                market,
                                callback_data=self.helper.create_callback_data(
                                    call_back_tag[0], "", market
                                ),  # f"{call_back_tag}_{market}"
                            )
                        )

        if len(buttons) > 0:
            self.helper.send_telegram_message(
                update,
                f"<b>What do you want to {call_back_tag[1]}?</b>",
                self.sort_inline_buttons(buttons, f"{call_back_tag[0]}"),
                new_message=False,
            )
        else:
            self.helper.send_telegram_message(
                update, f"<b>No {status} bots found.</b>", new_message=False
            )

    def sort_inline_buttons(self, buttons: list, call_back_tag):
        """Sort buttons for inline keyboard display"""
        keyboard = []
        if len(buttons) > 0:
            if len(buttons) > 1 and call_back_tag not in ("bot"):
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "All",
                            callback_data=self.helper.create_callback_data(
                                call_back_tag, "", "all"
                            ),
                        )
                    ]  # f"{call_back_tag}_all")]
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

            if call_back_tag not in (
                callbacktags.START,
                callbacktags.RESUME,
                callbacktags.BUY,
                callbacktags.SELL,
                "bot",
            ):
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "All (w/o open order)",
                            callback_data=self.helper.create_callback_data(
                                call_back_tag, "", "allclose"
                            ),  # f"{call_back_tag}_allclose",
                        )
                    ]
                )

            keyboard.append(
                [
                    InlineKeyboardButton(
                        "\U000025C0 Back",
                        callback_data=self.helper.create_callback_data(
                            callbacktags.BACK[0]
                        ),
                    )
                ]
            )

        return InlineKeyboardMarkup(keyboard)

    def action_bot_response(
        self, update: Update, call_back_tag, state, context, status: str = "active", market_override=""
    ):
        """Run requested bot action"""
        mode = call_back_tag.capitalize()
        if market_override != "":
            self.helper.send_telegram_message(
                update, f"<i>{mode} bots</i>", context=context, new_message=False
            )
            self.helper.stop_running_bot(
                market_override, state, True
            )
            return

        query = update.callback_query
        

        if query.data.__contains__("allclose") or query.data.__contains__("all"):
            self.helper.send_telegram_message(
                update, f"<i>{mode} bots</i>", context=context, new_message=False
            )

            for pair in self.helper.get_active_bot_list(status):
                self.helper.stop_running_bot(
                    pair, state, False if query.data.__contains__("allclose") else True
                )
                sleep(1)
        else:
            self.helper.send_telegram_message(
                update, f"<i>{mode} bots</i>", context=context, new_message=False
            )
            self.helper.stop_running_bot(
                str(query.data).replace(f"{call_back_tag}_", ""), state, True
            )
        sleep(5)
        # self.helper.send_telegram_message(
        #     update, f"<b>{mode} bots complete</b>", context=context
        # )

    def ask_start_bot_list(self, update: Update):
        """Get bot start list"""
        buttons = []
        self.helper.read_data()
        for market in self.helper.data["markets"]:
            if not self.helper.is_bot_running(market):
                buttons.append(
                    InlineKeyboardButton(
                        market,
                        callback_data=self.helper.create_callback_data(
                            callbacktags.START[0], "", market
                        ),
                    )  # "start_" + market)
                )

        if len(buttons) > 0:
            reply_markup = self.sort_inline_buttons(buttons, "start")
            self.helper.send_telegram_message(
                update,
                "<b>What crypto bots do you want to start?</b>",
                reply_markup,
                new_message=False,
            )
        else:
            self.helper.send_telegram_message(
                update,
                "<b>Nothing on your start list</b>\n<i>Use /addnew to add a market.</i>",
                new_message=False,
            )

    def start_bot_response(self, update: Update, context, market_override = ""):
        """Start bot list response"""

        if market_override != "":
            self.helper.send_telegram_message(
                update,
                f"<i>Starting {market_override} crypto bot</i>",
                context=context,
                new_message=False,
            )
            self.helper.read_data()
            if not self.helper.is_bot_running(market_override):
                overrides = self.helper.data["markets"][market_override]["overrides"]
                exchange = overrides[overrides.find("--exchange")+11: overrides.find("--market")-1]
                self.helper.start_process(
                    market_override, exchange, overrides
                )
            else:
                self.helper.send_telegram_message(
                    update,
                    f"{market_override} is already running, no action taken.",
                    context=context,
                )
            return

        query = update.callback_query

        self.helper.read_data()

        if "all" in query.data:  # start all bots
            self.helper.send_telegram_message(
                update, "<b>Starting all bots</b>", context=context, new_message=False
            )

            for market in self.helper.data["markets"]:
                if not self.helper.is_bot_running(market):
                    overrides = self.helper.data["markets"][market]["overrides"]
                    self.helper.send_telegram_message(
                        update, f"<i>Starting {market} crypto bot</i>", context=context
                    )
                    self.helper.start_process(
                        market, self.helper.get_running_bot_exchange(market), overrides
                    )
                    sleep(10)
                    self.helper.read_data()
                else:
                    self.helper.send_telegram_message(
                        update,
                        f"{market} is already running, no action taken.",
                        context=context,
                    )
        else:  # start single bot
            self.helper.send_telegram_message(
                update,
                f"<i>Starting {str(query.data).replace('start_', '')} crypto bot</i>",
                context=context,
                new_message=False,
            )

            if not self.helper.is_bot_running(str(query.data).replace("start_", "")):
                overrides = self.helper.data["markets"][
                    str(query.data).replace("start_", "")
                ]["overrides"]
                self.helper.start_process(
                    str(query.data).replace("start_", ""), "", overrides
                )
            else:
                self.helper.send_telegram_message(
                    update,
                    f"{str(query.data).replace('start_', '')} is already running, no action taken.",
                    context=context,
                )
        self.helper.send_telegram_message(
            update, "<b>Starting bots complete</b>", context=context
        )

    def ask_stop_bot_list(self, update: Update):
        """Get bot stop list"""
        self._ask_bot_list(update, callbacktags.STOP, "active")

    def stop_bot_response(self, update: Update, context, market_override=""):
        """Stop bot list response"""
        self.action_bot_response(update, "stop", "exit", context, "active", market_override)
        self.helper.send_telegram_message(
            update, "<b>Stop bots complete</b>", context=context
        )

    def ask_pause_bot_list(self, update: Update):
        """Get pause bot list"""
        self._ask_bot_list(update, callbacktags.PAUSE, "active")

    def pause_bot_response(self, update: Update, context, market_override=""):
        """Pause bot list response"""
        self.action_bot_response(update, "pause", "pause", context, "active", market_override)
        self.helper.send_telegram_message(
            update, "<b>Pausing bots complete</b>", context=context
        )

    def ask_resume_bot_list(self, update: Update):
        """Get resume bot list"""
        self._ask_bot_list(update, callbacktags.RESUME, "paused")

    def resume_bot_response(self, update: Update, context, market_override=""):
        """Resume bot list response"""
        self.action_bot_response(update, "resume", "start", context, "paused", market_override)
        self.helper.send_telegram_message(
            update, "<b>Resuming bots complete</b>", context=context
        )

    def ask_sell_bot_list(self, update):
        """Manual sell request (asks which coin to sell)"""
        self._ask_bot_list(update, callbacktags.SELL, "active")

    def ask_buy_bot_list(self, update):
        """Manual buy request"""
        self._ask_bot_list(update, callbacktags.BUY, "active")

    def ask_restart_bot_list(self, update: Update):
        """Get restart bot list"""
        self._ask_bot_list(update, callbacktags.RESTART, "active")

    def restart_bot_response(self, update: Update):
        """Restart bot list response"""
        query = update.callback_query
        bot_list = {}
        for bot in self.helper.get_active_bot_list():
            if not self.helper.read_data(bot):
                continue
            if query.data.__contains__("all"):
                bot_list.update(
                    {
                        bot: {
                            "exchange": self.helper.data["exchange"],
                            "startmethod": self.helper.data["botcontrol"][
                                "startmethod"
                            ],
                        }
                    }
                )
            elif query.data.__contains__(bot):
                bot_list.update(
                    {
                        bot: {
                            "exchange": self.helper.data["exchange"],
                            "startmethod": self.helper.data["botcontrol"][
                                "startmethod"
                            ],
                        }
                    }
                )

        self.action_bot_response(update, "restarting", "exit", context=None, status="active")
        sleep(1)
        restart_list = ""
        for bot in bot_list.items():
            restart_list += f"{bot[0]} : "
            self.helper.start_process(
                bot[0], bot[1]["exchange"], "", bot[1]["startmethod"]
            )
            sleep(10)

        self.helper.send_telegram_message(None, f"{restart_list} re-started")
        self.helper.send_telegram_message(
            update, "<b>Restarting bots complete</b>")

    #     def ask_exchange_options(self, update: Update):
    #         ''' Get available exchanges from config '''
    #         keyboard = []
    #         for exchange in self.helper.config:
    #             if not exchange == "telegram":
    #                 keyboard.append(
    #                     [InlineKeyboardButton(exchange, callback_data=exchange)]
    #                 )
    #
    #         reply_markup = InlineKeyboardMarkup(keyboard)
    #
    #         self.helper.send_telegram_message(update, "Select exchange", reply_markup)

    def ask_delete_bot_list(self, update: Update, context: CallbackContext):
        """ask which bot to delete"""
        buttons = []
        keyboard = []

        self.helper.read_data()
        for market in self.helper.data["markets"]:
            buttons.append(
                InlineKeyboardButton(
                    market,
                    callback_data=self.helper.create_callback_data(
                        callbacktags.DELETE[0], "", market
                    ),
                )  # "delete_" + market)
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
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "Cancel",
                        callback_data=self.helper.create_callback_data(
                            callbacktags.CANCEL[0]
                        ),
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        self.helper.send_telegram_message(
            update,
            "<b>What crypto bots do you want to delete?</b>",
            reply_markup,
            context=context,
        )

    def ask_exception_bot_list(self, update, context):
        """ask which bot to delete"""
        buttons = []
        keyboard = []

        self.helper.read_data()
        for pair in self.helper.data["scannerexceptions"]:
            buttons.append(
                InlineKeyboardButton(
                    pair,
                    callback_data=self.helper.create_callback_data(
                        callbacktags.REMOVEEXCEPTION[0], "", pair
                    ),
                )
            )  # "delexcep_" + pair))

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
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "Cancel",
                        callback_data=self.helper.create_callback_data(
                            callbacktags.CANCEL[0]
                        ),
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        self.helper.send_telegram_message(
            update,
            "<b>What do you want to remove from the scanner exception list?</b>",
            reply_markup,
            context=context,
        )
