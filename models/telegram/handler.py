""" Telegram Bot Request Handler """
import datetime
import json
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import  CallbackContext

from models.telegram import callbacktags
from models.telegram.control import TelegramControl
from models.telegram.helper import TelegramHelper
from models.telegram.actions import TelegramActions
from models.telegram.config import ConfigEditor
from models.telegram.settings import SettingsEditor

# self.scannerSchedule = BackgroundScheduler(timezone="UTC")
VALUE_ENTRY = range(1)


class TelegramHandler:
    """Handles response calls from TG"""

    def __init__(self, authuserid, tg_helper: TelegramHelper) -> None:
        self.scannerSchedule = BackgroundScheduler(timezone="UTC")

        self.authoriseduserid = authuserid
        self.helper = tg_helper

        self.control = TelegramControl(tg_helper)
        self.actions = TelegramActions(tg_helper)
        self.editor = ConfigEditor(tg_helper)
        self.setting = SettingsEditor(tg_helper)

    def _check_if_allowed(self, userid, update) -> bool:
        if str(userid) != self.authoriseduserid:
            if update is not None:
                self.helper.send_telegram_message(update, "<b>Not authorised!</b>", new_message=False)
            # update.message.reply_text("<b>Not authorised!</b>", parse_mode="HTML")
            return False

        return True

    def get_request(self) -> InlineKeyboardMarkup:
        """control panel buttons"""
        keyboard = [
            [InlineKeyboardButton("Notifications", callback_data="botsettings")],
            [
                InlineKeyboardButton(
                    "\U0001F4D6 View config", callback_data="showconfig"
                ),
                InlineKeyboardButton(
                    "Edit config \U00002699", callback_data="editconfig"
                ),
            ],
            [
                InlineKeyboardButton(
                    "\U0001F4B0 Trade Summary", callback_data="closed"
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
            [
                InlineKeyboardButton(
                    "Cancel",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.CANCEL[0]
                    ),
                )
            ],  # "cancel")],
        ]

        return InlineKeyboardMarkup(keyboard, one_time_keyboard=True)

    def get_response(self, update: Update, context: CallbackContext):
        """Handles responses from TG"""
        if not self._check_if_allowed(update.effective_user.id, update):
            return

        query = update.callback_query
        query.answer()
        callback_json = None
        try:
            callback_json = json.loads(query.data)
        except:  # pylint: disable=bare-except
            pass

        # Default Cancel Button
        if callback_json is not None and callback_json["c"] == callbacktags.CANCEL[0]:
            self.helper.send_telegram_message(
                update, "\U00002757 User Cancelled Request", new_message=False
            )

        # Default Back Button
        if callback_json is not None and callback_json["c"] == callbacktags.BACK[0]:
            key_markup = self.get_request()
            self.helper.send_telegram_message(
                update,
                "<b>PyCryptoBot Command Panel.</b>",
                key_markup,
                new_message=False,
            )

        # Settings / Notifications
        elif query.data == "botsettings":
            self.setting.get_notifications(update)

        elif callback_json is not None and callback_json["c"] == callbacktags.NOTIFY[0]:
            if callback_json["e"] == callbacktags.ENABLE[0]:
                self.setting.enable_option(callback_json["p"])
            elif callback_json["e"] == callbacktags.DISABLE[0]:
                self.setting.disable_option(callback_json["p"])
            self.setting.get_notifications(update)  # refresh buttons

        # Show Margins
        elif query.data == "margin":
            self.ask_margin_type(update, context)

        elif callback_json is not None and callback_json["c"] == callbacktags.MARGIN[0]:
            self.actions.get_margins(update, callback_json["p"])

        # Show Bot Info
        elif query.data == "status":
            self.actions.get_bot_info(update, context)

        # Show Config
        elif query.data == "showconfig":
            self.ask_exchange_options(update, "ex")
        # elif query.data.__contains__("ex_"):
        #     self.actions.show_config_response(update)
        elif callback_json is not None and callback_json["c"] == "ex":
            update.callback_query.data = callback_json["e"]
            self.actions.show_config_response(update)

        # Edit Config
        elif query.data == "editconfig":
            self.helper.load_config()
            self.ask_exchange_options(update, "edit")
        elif (
            callback_json is not None
            and callback_json["c"] == "edit"
            and callback_json["e"] == "screener"
        ):
            self.ask_exchange_options(update, callbacktags.SCREENER)
        elif callback_json is not None and callback_json["c"] == callbacktags.SCREENER:
            self.editor.get_config_options(update, context, callback_json["e"])
        elif callback_json is not None and callback_json["c"] == "edit":
            update.callback_query.data = callback_json["e"]
            self.editor.get_config_options(update, context)
        elif (
            callback_json is not None and callback_json["c"] == callbacktags.DISABLE[0]
        ):
            self.editor.disable_option(callback_json["e"], callback_json["p"])
            self.editor.get_config_options(
                update, context, callback_json["e"]
            )  # refresh buttons
        elif callback_json is not None and callback_json["c"] == callbacktags.ENABLE[0]:
            self.editor.enable_option(callback_json["e"], callback_json["p"])
            self.editor.get_config_options(
                update, context, callback_json["e"]
            )  # refresh buttons
        elif callback_json is not None and callback_json["c"] == callbacktags.FLOAT[0]:
            self.ask_percent_value(update, "float")
        elif (
            callback_json is not None and callback_json["c"] == callbacktags.INTEGER[0]
        ):
            self.ask_percent_value(update, "integer")
        elif (
            callback_json is not None
            and callback_json["c"] == callbacktags.INCREASEINT[0]
        ):
            unit_size = 1
            self.editor.increase_value(
                callback_json["e"], callback_json["p"], unit_size
            )
            typestr = "integer"
            self.ask_percent_value(update, typestr)
        elif (
            callback_json is not None
            and callback_json["c"] == callbacktags.INCREASEFLOAT[0]
        ):
            unit_size = 0.1
            self.editor.increase_value(
                callback_json["e"], callback_json["p"], unit_size
            )
            typestr = "float"
            self.ask_percent_value(update, typestr)
        elif (
            callback_json is not None
            and callback_json["c"] == callbacktags.DECREASEINT[0]
        ):
            unit_size = 1
            self.editor.decrease_value(
                callback_json["e"], callback_json["p"], unit_size
            )
            typestr = "integer"
            self.ask_percent_value(update, typestr)
        elif (
            callback_json is not None
            and callback_json["c"] == callbacktags.DECREASEFLOAT[0]
        ):
            unit_size = 0.1
            self.editor.decrease_value(
                callback_json["e"], callback_json["p"], unit_size
            )
            typestr = "float"
            self.ask_percent_value(update, typestr)
        elif callback_json is not None and callback_json["c"] == callbacktags.DONE[0]:
            self.editor.get_config_options(update, context, int(callback_json["e"]))

        elif (
            callback_json is not None
            and callback_json["c"] == callbacktags.SAVECONFIG[0]
        ):
            self.editor.save_updated_config(update)
            self.helper.load_config()
            self.ask_exchange_options(update, "edit")

        elif (
            callback_json is not None
            and callback_json["c"] == callbacktags.RELOADCONFIG[0]
        ):
            update.callback_query.data = "all"
            self.control.action_bot_response(update, "reload", "reload", context=context, status="active")
        elif (
            callback_json is not None
            and callback_json["c"] == callbacktags.GRANULARITY[0]
        ):
            self.editor.get_granularity(update, callback_json["e"], context)

        # Restart Bots
        elif query.data == "restart":
            self.control.ask_restart_bot_list(update)
        elif (
            callback_json is not None and callback_json["c"] == callbacktags.RESTART[0]
        ):
            update.callback_query.data = callback_json["p"]
            self.control.restart_bot_response(update)

        # Start Bots
        elif query.data == "start":
            self.control.ask_start_bot_list(update)
        elif callback_json is not None and callback_json["c"] == callbacktags.START[0]:
            update.callback_query.data = callback_json["p"]
            self.control.start_bot_response(update, context)
        # Stop Bots
        elif query.data == "stop":
            self.control.ask_stop_bot_list(update)
        elif callback_json is not None and callback_json["c"] == callbacktags.STOP[0]:
            update.callback_query.data = callback_json["p"]
            self.control.stop_bot_response(update, context)
        # Pause Bots
        elif query.data == "pause":
            self.control.ask_pause_bot_list(update)
        elif callback_json is not None and callback_json["c"] == callbacktags.PAUSE[0]:
            update.callback_query.data = callback_json["p"]
            self.control.pause_bot_response(update, context)
        # Resume Bots
        elif query.data == "resume":
            self.control.ask_resume_bot_list(update)
        elif callback_json is not None and callback_json["c"] == callbacktags.RESUME[0]:
            update.callback_query.data = callback_json["p"]
            self.control.resume_bot_response(update, context)

        # Restart Bots with Open Orders
        elif query.data == "reopen":
            self.actions.start_open_orders(update, context)

        # Initiate Buy order
        elif query.data == "buy":
            self.control.ask_buy_bot_list(update)
        elif callback_json is not None and callback_json["c"] == callbacktags.BUY[0]:
            update.callback_query.data = f"{callback_json['p']}"
            self.ask_confimation(update, callbacktags.CONFIRMBUY)
        elif (
            callback_json is not None
            and callback_json["c"] == callbacktags.CONFIRMBUY[0]
        ):
            update.callback_query.data = callback_json["p"]
            self.actions.buy_response(update, context)

        # Initiate Sell order
        elif query.data == "sell":
            self.control.ask_sell_bot_list(update)
        elif callback_json is not None and callback_json["c"] == callbacktags.SELL[0]:
            update.callback_query.data = f"{callback_json['p']}"
            self.ask_confimation(update, callbacktags.CONFIRMSELL)
        elif (
            callback_json is not None
            and callback_json["c"] == callbacktags.CONFIRMSELL[0]
        ):
            update.callback_query.data = callback_json["p"]
            self.actions.sell_response(update, context)

        # Delete Bot from start bot list (not on CP yet)
        elif query.data == "delete":
            self.control.ask_delete_bot_list(update, context)
        elif callback_json is not None and callback_json["c"] == callbacktags.DELETE[0]:
            update.callback_query.data = callback_json["p"]
            self.actions.delete_response(update)

        # Market Scanner
        elif query.data == "scanner":
            self.get_scanner_options(update)
        elif query.data == "schedule":
            self._check_scheduled_job(update, context)
        elif query.data in ("scanonly", "noscan", "startmarket"):
            self.helper.send_telegram_message(
                update,
                "Market Scanner Started",
                context=context,
                new_message=self._check_scheduled_job(update, context),
            )
            self.actions.start_market_scan(
                update,
                context,
                self.helper.use_default_scanner,
                True if query.data != "noscan" else False,
                True if query.data != "scanonly" else False,
            )
        elif query.data == "stopmarket":
            self._remove_scheduled_job(update, context)

        # Delete Exceptions
        elif (
            callback_json is not None
            and callback_json["c"] == callbacktags.REMOVEEXCEPTION[0]
        ):
            update.callback_query.data = callback_json["p"]
            self.actions.remove_exception_callback(update)

        # Actions by bot (experimental)
        elif query.data.__contains__("bot_"):
            self.get_bot_options(update)

        elif query.data == "closed":
            self.get_trade_options(update, context)

        elif callback_json is not None and callback_json["c"] == callbacktags.TRADES:
            self.actions.get_closed_trades(update, callback_json["p"])

        # query.edit_message_text(
        #     "\U000026A0 <b>Under Construction</b> \U000026A0", parse_mode="HTML"
        # )

    def get_trade_options(self, update, context):
        """individual bot controls"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "Last 24Hrs",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.TRADES, "", callbacktags.TRADES24H
                    ),  # f"stop_{query.data.replace('bot_', '')}"
                )
            ],
            [
                InlineKeyboardButton(
                    "Last 7 Days",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.TRADES, "", callbacktags.TRADES7D
                    ),  # f"stop_{query.data.replace('bot_', '')}"
                ),
                InlineKeyboardButton(
                    "Last 14 Days",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.TRADES, "", callbacktags.TRADES14D
                    ),  # f"stop_{query.data.replace('bot_', '')}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Last 31 Days",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.TRADES, "", callbacktags.TRADES1M
                    ),  # f"stop_{query.data.replace('bot_', '')}"
                )
            ],
            [
                InlineKeyboardButton(
                    "All",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.TRADES, "", callbacktags.TRADESALL
                    ),  # f"stop_{query.data.replace('bot_', '')}"
                )
            ],
            [
                InlineKeyboardButton(
                    "\U000025C0 Back",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.BACK[0]
                    ),
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        reply = "<b>Select trade summary period:</b>"
        self.helper.send_telegram_message(
            update, reply, reply_markup, context=context, new_message=False
        )

    def get_bot_options(self, update):
        """individual bot controls"""
        query = update.callback_query

        keyboard = [
            [
                InlineKeyboardButton(
                    "Stop", callback_data=f"stop_{query.data.replace('bot_', '')}"
                )
            ],
            [
                InlineKeyboardButton(
                    "Restart", callback_data=f"restart_{query.data.replace('bot_', '')}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Pause", callback_data=f"pause_{query.data.replace('bot_', '')}"
                ),
                InlineKeyboardButton(
                    "Resume", callback_data=f"resume_{query.data.replace('bot_', '')}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Sell", callback_data=f"sell_{query.data.replace('bot_', '')}"
                )
            ],
            [
                InlineKeyboardButton(
                    "\U000025C0 Back",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.BACK[0]
                    ),
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        reply = f"<b>{query.data.replace('bot_', '')} Actions:</b>"
        self.helper.send_telegram_message(
            update, reply, reply_markup, new_message=False
        )

    def get_scanner_options(self, update):
        """get scanner/screener options"""
        keyboard = [
            [
                InlineKeyboardButton("Scan Only", callback_data="scanonly"),
                InlineKeyboardButton("Start Bots Only", callback_data="noscan"),
            ],
            [InlineKeyboardButton("Scan + Start Bots", callback_data="startmarket")],
            [
                InlineKeyboardButton(
                    "\U000025C0 Back",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.BACK[0]
                    ),
                )
            ],
        ]

        keyboard.insert(
            0,
            [InlineKeyboardButton("Add Schedule", callback_data="schedule")]
            if len(self.scannerSchedule.get_jobs()) == 0
            else [
                InlineKeyboardButton("Remove Schedule", callback_data="stopmarket"),
            ],
        )

        self.helper.send_telegram_message(
            update,
            "<b>Scanning Options.</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
            new_message=False,
        )

    def ask_margin_type(self, update, context):
        """Ask what user wants to see active order/pairs or all"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "Active Orders",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.MARGIN[0], "", "orders"
                    ),
                ),
                InlineKeyboardButton(
                    "Active Pairs",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.MARGIN[0], "", "pairs"
                    ),
                ),
                InlineKeyboardButton(
                    "All",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.MARGIN[0], "", "all"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "\U000025C0 Back",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.BACK[0]
                    ),
                )
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        reply = "<b>Make your selection</b>"
        self.helper.send_telegram_message(
            update, reply, reply_markup, context=context, new_message=False
        )

    def ask_exchange_options(self, update: Update, callback: str = "ex"):
        """get exchanges from config file"""
        keyboard = []
        buttons = []
        exchange_list = self.helper.config
        if callback == callbacktags.SCREENER:
            exchange_list = self.helper.screener
        for exchange in exchange_list:
            if exchange not in ("telegram"):
                buttons.append(
                    InlineKeyboardButton(
                        exchange.capitalize(),
                        callback_data=self.helper.create_callback_data(
                            callback, exchange
                        ),  # f"{callback}_{exchange}"
                    )
                )
        i = 0
        if callback != callbacktags.SCREENER:
            buttons.append(
                InlineKeyboardButton(
                    "Screener",
                    callback_data=self.helper.create_callback_data(
                        callback, "screener"
                    ),  # f"{callback}_screener"
                )
            )
        while i <= len(buttons) - 1:
            if len(buttons) - 1 >= i + 2:
                keyboard.append([buttons[i], buttons[i + 1], buttons[i + 2]])
            elif len(buttons) - 1 >= i + 1:
                keyboard.append([buttons[i], buttons[i + 1]])
            else:
                keyboard.append([buttons[i]])
            i += 3
        if callback != callbacktags.SCREENER:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "Reload all running bots",
                        callback_data=self.helper.create_callback_data(
                            callbacktags.RELOADCONFIG[0]
                        ),  # "reload_config"
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

        reply_markup = InlineKeyboardMarkup(keyboard)

        self.helper.send_telegram_message(
            update, "<b>Select exchange</b>", reply_markup, new_message=False
        )

    def ask_percent_value(self, update, typestr):
        """get button to increase values"""
        query = update.callback_query
        query.answer()
        callback_json = None
        try:
            callback_json = json.loads(query.data)
            exchange = callback_json["e"]
            prop = callback_json["p"]
        except: #pylint: disable=bare-except
            split_callback = query.data.split("_")
            exchange, prop = (
                split_callback[0],
                split_callback[2],
            )
            if query.data.__contains__("*"):
                prop = split_callback[3]

        cb_data_decrease = self.helper.create_callback_data(
            callbacktags.DECREASEINT[0]
            if typestr == "integer"
            else callbacktags.DECREASEFLOAT[0],
            f"{exchange}",
            prop,
        )
        cb_data_increase = self.helper.create_callback_data(
            callbacktags.INCREASEINT[0]
            if typestr == "integer"
            else callbacktags.INCREASEFLOAT[0],
            f"{exchange}",
            prop,
        )

        keyboard = [
            [
                InlineKeyboardButton("-", callback_data=cb_data_decrease),
                InlineKeyboardButton("+", callback_data=cb_data_increase),
            ],
            [
                InlineKeyboardButton(
                    "\U000025C0 Done",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.DONE[0], exchange, prop
                    ),
                )
            ],
        ]
        if self.editor.exchange_convert(int(exchange)) != "scanner":
            config_value = self.helper.config[
                self.editor.exchange_convert(int(exchange))
            ]["config"][prop]
        else:
            config_value = self.helper.config[
                self.editor.exchange_convert(int(exchange))
            ][prop]
        if typestr == "integer":
            self.helper.send_telegram_message(
                update,
                f"<b>{prop}: " f"{int(config_value)}</b>",
                InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
                new_message=False,
            )
        elif typestr == "float":
            self.helper.send_telegram_message(
                update,
                f"<b>{prop}: " f"{round(float(config_value),2)}</b>",
                InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
                new_message=False,
            )

    def ask_confimation(self, update, trade_choice):
        """confirmation question"""
        query = update.callback_query
        keyboard = [
            [
                InlineKeyboardButton(
                    "Confirm",
                    callback_data=self.helper.create_callback_data(
                        trade_choice[0], "", query.data
                    ),
                )  # f"confirm_{query.data}"),
            ],
            [
                InlineKeyboardButton(
                    "Cancel",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.CANCEL[0]
                    ),
                )
            ],  # )],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        reply = f"<b>Are you sure you want to {trade_choice[1]}?</b>"
        self.helper.send_telegram_message(
            update, reply, reply_markup, new_message=False
        )

    def _check_scheduled_job(self, update=None, context=None) -> bool:
        """check if scanner/screener is scheduled to run, add if not"""
        if (
            self.helper.config["scanner"]["autoscandelay"] > 0
            and len(self.scannerSchedule.get_jobs()) == 0
        ):
            if not self.scannerSchedule.running:
                self.scannerSchedule.start()

            # if update is None:
            #     update = self.helper.default_context

            self.scannerSchedule.add_job(
                self.actions.start_market_scan,
                args=(update, context, self.helper.use_default_scanner),
                trigger="interval",
                minutes=self.helper.config["scanner"]["autoscandelay"] * 60,
                name=f"Volume Auto Scanner ({datetime.datetime.now().isoformat()})",
                misfire_grace_time=10,
            )

            reply = (
                "<b>Scan job schedule created to run every "
                f"{self.helper.config['scanner']['autoscandelay']} hour(s)</b> \u2705"
            )
            self.helper.send_telegram_message(
                update, reply, context=context, new_message=False
            )
            return True
        return False

    def _remove_scheduled_job(self, update=None, context=None):
        """check if scanner/screener is scheduled to run, remove if it is"""
        reply = ""
        if len(self.scannerSchedule.get_jobs()) > 0:
            self.scannerSchedule.remove_all_jobs()
            reply = "<b>Scan job schedule has been removed</b> \u2705"

        else:
            reply = "<b>No scheduled job found!</b>"

        self.helper.send_telegram_message(
            update, reply, context=context, new_message=False
        )

    # def conversation_handler(self, update, ) -> ConversationHandler:
    #     return ConversationHandler(
    #         entry_points=[CommandHandler("value", self.editor.conversation_handler())],
    #         states={
    #             VALUE_ENTRY : {MessageHandler(Filters.text & ~Filters.command, self.editor.conversation_handler())}
    #         },
    #         fallbacks=[CommandHandler("cancel", self.editor.conversation_handler())]
    #     )
