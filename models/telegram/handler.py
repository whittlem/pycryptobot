''' Telegram Bot Request Handler '''
import datetime
import json
import models.telegram.callbacktags as callbacktags
import models.exchange.ExchangesEnum
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, MessageHandler, Filters
from apscheduler.schedulers.background import BackgroundScheduler

from models.telegram.control import TelegramControl
from models.telegram.helper import TelegramHelper
from models.telegram.actions import TelegramActions
from models.telegram.config import ConfigEditor
from models.telegram.settings import SettingsEditor

scannerSchedule = BackgroundScheduler(timezone="UTC")
VALUE_ENTRY = range(1)

class TelegramHandler:
    """Handles response calls from TG"""

    def __init__(self, datafolder, authuserid, tg_helper: TelegramHelper) -> None:
        self.authoriseduserid = authuserid
        self.datafolder = datafolder
        self.helper = tg_helper

        self.control = TelegramControl(self.datafolder, tg_helper)
        self.actions = TelegramActions(self.datafolder, tg_helper)
        self.editor = ConfigEditor(self.datafolder, tg_helper)
        self.setting = SettingsEditor(self.datafolder, tg_helper)

    def _check_if_allowed(self, userid, update) -> bool:
        if str(userid) != self.authoriseduserid:
            update.message.reply_text("<b>Not authorised!</b>", parse_mode="HTML")
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
                    "\U0001F510 Edit config \U00002699", callback_data="editconfig"
                ),
            ],
            [
                InlineKeyboardButton("\U0001F4B0 Closed Trades", callback_data="closed"),
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
                InlineKeyboardButton(
                    "\U00002139 Bot Status", callback_data="status"
                ),
                InlineKeyboardButton("Margins \U0001F4C8", callback_data="margin"),
            ],
            [InlineKeyboardButton("Cancel", callback_data=self.helper.create_callback_data(callbacktags.CANCEL))]#"cancel")],
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
        except:
            pass

        # Default Cancel Button
        if callback_json is not None and callback_json["c"] == callbacktags.CANCEL:
            self.helper.send_telegram_message(update, "\U00002757 User Cancelled Request")

        # Default Back Button
        if callback_json is not None and callback_json["c"] == callbacktags.BACK:
            key_markup = self.get_request()
            self.helper.send_telegram_message(
                update, "<b>PyCryptoBot Command Panel.</b>", key_markup
            )

        # Settings / Notifications
        elif query.data == "botsettings":
            self.setting.get_notifications(update)

        elif callback_json is not None and callback_json["c"] == callbacktags.NOTIFY:
            if callback_json["e"] == callbacktags.ENABLE:
                self.setting.enable_option(callback_json["p"])
            elif callback_json["e"] == callbacktags.DISABLE:
                self.setting.disable_option(callback_json["p"])
            self.setting.get_notifications(update)  # refresh buttons

        # Show Margins
        elif query.data == "margin":
            self.ask_margin_type(update, context)

        elif callback_json is not None and callback_json["c"] == callbacktags.MARGIN:
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
        # elif query.data.__contains__("edit_"):
        #     self.editor.get_config_options(update, context)
        elif callback_json is not None and callback_json["c"] == "edit":
            update.callback_query.data = callback_json["e"]
            self.editor.get_config_options(update, context)
        # elif query.data.__contains__("_disable_"):
        #     self.editor.disable_option(
        #         query.data[: query.data.find("_")],
        #         query.data[query.data.rfind("(") +1 : query.data.rfind(")")])
        #     self.editor.get_config_options(update, context)  # refresh buttons
        elif callback_json is not None and callback_json["c"] == callbacktags.DISABLE:
            self.editor.disable_option(callback_json["e"], callback_json["p"])
            self.editor.get_config_options(update, context, callback_json["e"])  # refresh buttons

        # elif query.data.__contains__("_enable_"):
        #     self.editor.enable_option(
        #         query.data[: query.data.find("_")],
        #         query.data[query.data.rfind("(") +1 : query.data.rfind(")")],
        #     )
        #     self.editor.get_config_options(update, context)  # refresh buttons
        elif callback_json is not None and callback_json["c"] == callbacktags.ENABLE:
            self.editor.enable_option(callback_json["e"], callback_json["p"])
            self.editor.get_config_options(update, context, callback_json["e"])  # refresh buttons

        # elif query.data.__contains__("_float_"):
        #     self.ask_percent_value(update, "float")
        elif callback_json is not None and callback_json["c"] == callbacktags.FLOAT:
            self.ask_percent_value(update, "float")

        # elif query.data.__contains__("_integer_"):
        #     self.ask_percent_value(update, "integer")
        elif callback_json is not None and callback_json["c"] == callbacktags.INTEGER:
            self.ask_percent_value(update, "integer")

        # elif query.data.__contains__("increase"):
        #     unit_size = 0.1 if query.data.__contains__("float") else 1
        #     self.editor.increase_value(
        #         query.data[: query.data.find("_")],
        #         query.data[query.data.rfind("_") + 1 :],
        #         unit_size,
        #     )
        #     typestr = "float" if query.data.__contains__("float") else "integer"
        #     self.ask_percent_value(update, typestr)
        elif callback_json is not None and callback_json["c"] == callbacktags.INCREASEINT:
            unit_size = 1
            self.editor.increase_value(callback_json["e"], callback_json["p"], unit_size)
            typestr = "integer"
            self.ask_percent_value(update, typestr)
        elif callback_json is not None and callback_json["c"] == callbacktags.INCREASEFLOAT:
            unit_size = 0.1
            self.editor.increase_value(callback_json["e"], callback_json["p"], unit_size)
            typestr = "float"
            self.ask_percent_value(update, typestr)

        # elif query.data.__contains__("decrease"):
        #     unit_size = 0.1 if query.data.__contains__("float") else 1
        #     self.editor.decrease_value(
        #         query.data[: query.data.find("_")],
        #         query.data[query.data.rfind("_") + 1 :],
        #         unit_size,
        #     )
        #     type_str = "float" if query.data.__contains__("float") else "integer"
        #     self.ask_percent_value(update, type_str)
        elif callback_json is not None and callback_json["c"] == callbacktags.DECREASEINT:
            unit_size = 1
            self.editor.decrease_value(callback_json["e"], callback_json["p"], unit_size)
            typestr = "integer"
            self.ask_percent_value(update, typestr)
        elif callback_json is not None and callback_json["c"] == callbacktags.DECREASEFLOAT:
            unit_size = 0.1
            self.editor.decrease_value(callback_json["e"], callback_json["p"], unit_size)
            typestr = "float"
            self.ask_percent_value(update, typestr)

        # elif query.data.__contains__("_done"):
        #     self.editor.get_config_options(update, query.data[: query.data.find("_")])
        elif callback_json is not None and callback_json["c"] == callbacktags.DONE:
            self.editor.get_config_options(update, context, int(callback_json["e"]))
        # elif query.data == "save_config":
        #     self.editor.save_updated_config(update)
        #     self.helper.load_config()
        #     self.ask_exchange_options(update, "edit")
        elif callback_json is not None and callback_json["c"] == callbacktags.SAVECONFIG:
            self.editor.save_updated_config(update)
            self.helper.load_config()
            self.ask_exchange_options(update, "edit")

        elif query.data == "reload_config":
            update.callback_query.data = "all"
            self.control.action_bot_response(update, "reload", "reload", "active")
        elif callback_json is not None and callback_json["c"] == callbacktags.RELOADCONFIG:
            update.callback_query.data = "all"
            self.control.action_bot_response(update, "reload", "reload", "active")
        # elif query.data.__contains__("_granularity_"):
        #     self.editor.get_granularity(update, query.data[: query.data.find("_")])
        elif callback_json is not None and callback_json["c"] == callbacktags.GRANULARITY:
            self.editor.get_granularity(update, callback_json["e"], context)
        

        # Restart Bots
        elif query.data == "restart":
            self.control.ask_restart_bot_list(update)
        # elif query.data.__contains__("restart_"):
        #     self.control.restart_bot_response(update)
        elif callback_json is not None and callback_json["c"] == callbacktags.RESTART:
            update.callback_query.data = callback_json["p"]
            self.control.restart_bot_response(update)

        # Start Bots
        elif query.data == "start":
            self.control.ask_start_bot_list(update)
        # elif query.data.__contains__("start_"):
        #     self.control.start_bot_response(update, context)
        elif callback_json is not None and callback_json["c"] == callbacktags.START:
            update.callback_query.data = callback_json["p"]
            self.control.start_bot_response(update, context)

        # Stop Bots
        elif query.data == "stop":
            self.control.ask_stop_bot_list(update)
        # elif query.data.__contains__("stop_"):
        #     self.control.stop_bot_response(update, context)
        elif callback_json is not None and callback_json["c"] == callbacktags.STOP:
            update.callback_query.data = callback_json["p"]
            self.control.stop_bot_response(update, context)
        # Pause Bots
        elif query.data == "pause":
            self.control.ask_pause_bot_list(update)
        # elif query.data.__contains__("pause_"):
        #     self.control.pause_bot_response(update, context)
        elif callback_json is not None and callback_json["c"] == callbacktags.PAUSE:
            update.callback_query.data = callback_json["p"]
            self.control.pause_bot_response(update, context)

        # Resume Bots
        elif query.data == "resume":
            self.control.ask_resume_bot_list(update)
        # elif query.data.__contains__("resume_"):
        #     self.control.resume_bot_response(update, context)
        elif callback_json is not None and callback_json["c"] == callbacktags.RESUME:
            update.callback_query.data = callback_json["p"]
            self.control.resume_bot_response(update, context)

        # Restart Bots with Open Orders
        elif query.data == "reopen":
            self.actions.start_open_orders(update, context)

        # Initiate Buy order
        elif query.data == "buy":
            self.control.ask_buy_bot_list(update)
        # elif query.data.__contains__("confirm_buy_"):
        #     self.actions.buy_response(update, context)
        # elif query.data.__contains__("buy_"):
        #     self.ask_confimation(update)
        elif callback_json is not None and callback_json["c"] == callbacktags.BUY:
            update.callback_query.data = f"{callback_json['p']}"
            self.ask_confimation(update, callbacktags.CONFIRMBUY)
        elif callback_json is not None and callback_json["c"] == callbacktags.CONFIRMBUY:
            update.callback_query.data = callback_json["p"]
            self.actions.buy_response(update, context)

        # Initiate Sell order
        elif query.data == "sell":
            self.control.ask_sell_bot_list(update)
        # elif query.data.__contains__("confirm_sell_"):
        #     self.actions.sell_response(update, context)
        # elif query.data.__contains__("sell_"):
        #     self.ask_confimation(update)
        elif callback_json is not None and callback_json["c"] == callbacktags.SELL:
            update.callback_query.data = f"{callback_json['p']}"
            self.ask_confimation(update, callbacktags.CONFIRMSELL)
        elif callback_json is not None and callback_json["c"] == callbacktags.CONFIRMSELL:
            update.callback_query.data = callback_json["p"]
            self.actions.sell_response(update, context)

        # Delete Bot from start bot list (not on CP yet)
        elif query.data == "delete":
            self.control.ask_delete_bot_list(update, context)
        # elif query.data.__contains__("delete_"):
        #     self.actions.delete_response(update)
        elif callback_json is not None and callback_json["c"] == callbacktags.DELETE:
            update.callback_query.data = callback_json["p"]
            self.actions.delete_response(update)

        # Market Scanner
        elif query.data == "scanner":
            self.get_scanner_options(update)
        elif query.data == "schedule":
            self._check_scheduled_job(update, context)
        elif query.data in ("scanonly", "noscan", "startmarket"):
            if query.data == "startmarket":
                self._check_scheduled_job(update, context)
            context.bot.send_message(chat_id=update.effective_message.chat_id,
                                text="Market Scanner Started")
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
        # elif query.data.__contains__("delexcep_"):
        #     self.actions.remove_exception_callback(update)
        elif callback_json is not None and callback_json["c"] == callbacktags.REMOVEEXCEPTION:
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
                    "Last 24Hrs", callback_data=self.helper.create_callback_data(callbacktags.TRADES, "", callbacktags.TRADES24H)  #f"stop_{query.data.replace('bot_', '')}"
                )
            ],
            [
                InlineKeyboardButton(
                    "Last 7 Days", callback_data=self.helper.create_callback_data(callbacktags.TRADES, "", callbacktags.TRADES7D)  #f"stop_{query.data.replace('bot_', '')}"
                ),
                InlineKeyboardButton(
                    "Last 14 Days", callback_data=self.helper.create_callback_data(callbacktags.TRADES, "", callbacktags.TRADES14D)  #f"stop_{query.data.replace('bot_', '')}"
                )
            ],
            [
                InlineKeyboardButton(
                    "Last 31 Days", callback_data=self.helper.create_callback_data(callbacktags.TRADES, "", callbacktags.TRADES1M)  #f"stop_{query.data.replace('bot_', '')}"
                )
            ],
            [InlineKeyboardButton("\U000025C0 Back", callback_data=self.helper.create_callback_data(callbacktags.BACK))],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        reply = "<b>Closed Trades:</b>"
        self.helper.send_telegram_message(update, reply, reply_markup, context=context)

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
            [InlineKeyboardButton("\U000025C0 Back", callback_data=self.helper.create_callback_data(callbacktags.BACK))],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        reply = f"<b>{query.data.replace('bot_', '')} Actions:</b>"
        self.helper.send_telegram_message(update, reply, reply_markup)

    def get_scanner_options(self, update):
        """get scanner/screener options"""
        keyboard = [
            [
                InlineKeyboardButton("Scan Only", callback_data="scanonly"),
                InlineKeyboardButton("Start Bots Only", callback_data="noscan"),
            ],
            [InlineKeyboardButton("Scan + Start Bots", callback_data="startmarket")],
            [InlineKeyboardButton("\U000025C0 Back", callback_data=self.helper.create_callback_data(callbacktags.BACK))],
        ]

        keyboard.insert(
            0,
            [InlineKeyboardButton("Add Schedule", callback_data="schedule")]
            if len(scannerSchedule.get_jobs()) == 0
            else [
                InlineKeyboardButton("Remove Schedule", callback_data="stopmarket"),
            ],
        )

        self.helper.send_telegram_message(
            update,
            "<b>Scanning Options.</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
        )

    def ask_margin_type(self, update, context):
        """Ask what user wants to see active order/pairs or all"""
        keyboard = [
            [
                InlineKeyboardButton("Active Orders", callback_data=self.helper.create_callback_data(callbacktags.MARGIN, "", "orders")),
                InlineKeyboardButton("Active Pairs", callback_data=self.helper.create_callback_data(callbacktags.MARGIN, "", "pairs")),
                InlineKeyboardButton("All", callback_data=self.helper.create_callback_data(callbacktags.MARGIN, "", "all")),
            ],
            [InlineKeyboardButton("\U000025C0 Back", callback_data=self.helper.create_callback_data(callbacktags.BACK))],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        reply = "<b>Make your selection</b>"
        self.helper.send_telegram_message(update, reply, reply_markup, context=context)

    def ask_exchange_options(self, update: Update, callback: str = "ex"):
        """get exchanges from config file"""
        keyboard = []
        buttons = []
        for exchange in self.helper.config:
            if exchange not in ("telegram"):
                buttons.append(
                    InlineKeyboardButton(
                        exchange.capitalize(), callback_data=self.helper.create_callback_data(callback,exchange) # f"{callback}_{exchange}"
                    )
                )
        buttons.append(
                    InlineKeyboardButton(
                        "Screener", callback_data=self.helper.create_callback_data(callback,"screener")#f"{callback}_screener"
                    )
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
            [
                InlineKeyboardButton(
                    "Reload all running bots", callback_data=self.helper.create_callback_data(callbacktags.RELOADCONFIG)# "reload_config"
                )
            ]
        )
            keyboard.append(
                [InlineKeyboardButton("\U000025C0 Back", callback_data=self.helper.create_callback_data(callbacktags.BACK))]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)
        # query = update.callback_query
        # query.answer()

        self.helper.send_telegram_message(update, "<b>Select exchange</b>", reply_markup)

    def ask_percent_value(self, update, typestr):
        """get button to increase values"""
        query = update.callback_query
        query.answer()
        callback_json = None
        try:
            callback_json = json.loads(query.data)
            exchange = callback_json["e"]
            prop = callback_json["p"]
        except:
            split_callback = query.data.split("_")
            exchange, prop = (
                split_callback[0],
                split_callback[2],
            )
            if query.data.__contains__("*"):
                prop = split_callback[3]

        cb_data_decrease = self.helper.create_callback_data(callbacktags.DECREASEINT if typestr == "integer" else callbacktags.DECREASEFLOAT, f"{exchange}", prop)
        cb_data_increase = self.helper.create_callback_data(callbacktags.INCREASEINT if typestr == "integer" else callbacktags.INCREASEFLOAT, f"{exchange}", prop)

        keyboard = [
            [
                InlineKeyboardButton(
                    "-", callback_data=cb_data_decrease
                ),
                InlineKeyboardButton(
                    "+", callback_data=cb_data_increase
                ),
            ],
            [
                InlineKeyboardButton(
                    "\U000025C0 Done", callback_data=self.helper.create_callback_data(callbacktags.DONE, exchange, prop)
                )
            ],
        ]
        if self.editor.exchange_convert(int(exchange)) != "scanner":
            config_value = self.helper.config[self.editor.exchange_convert(int(exchange))]['config'][prop]
        else:
            config_value = self.helper.config[self.editor.exchange_convert(int(exchange))][prop]
        if typestr == "integer":
            self.helper.send_telegram_message(
                update,
                f"<b>{prop}: "\
                    f"{int(config_value)}</b>",
                InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
            )
        elif typestr == "float":
            self.helper.send_telegram_message(
                update,
                f"<b>{prop}: "\
                    f"{round(float(config_value),2)}</b>",
                InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
            )

    def ask_confimation(self, update, trade_choice):
        """confirmation question"""
        query = update.callback_query
        keyboard = [
            [
                InlineKeyboardButton("Confirm", callback_data=self.helper.create_callback_data(trade_choice,"", query.data)) #f"confirm_{query.data}"),
            ],
            [InlineKeyboardButton("Cancel", callback_data=self.helper.create_callback_data(callbacktags.CANCEL))] #)],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        reply = f"<b>Are you sure you want to {'buy' if trade_choice==35 else 'sell'} {query.data.replace('_', ' ')}?</b>"
        self.helper.send_telegram_message(update, reply, reply_markup)

    def _check_scheduled_job(self, update, context):
        """check if scanner/screener is scheduled to run, add if not"""
        if (
            self.helper.config["scanner"]["autoscandelay"] > 0
            and len(scannerSchedule.get_jobs()) == 0
        ):
            if not scannerSchedule.running:
                scannerSchedule.start()

            scannerSchedule.add_job(
                self.actions.start_market_scan,
                args=(update, context, self.helper.use_default_scanner, True, True),
                trigger="interval",
                minutes=self.helper.config["scanner"]["autoscandelay"] * 60,
                name=f"Volume Auto Scanner ({datetime.datetime.now().isoformat()})",
                misfire_grace_time=10,
            )

            reply = "<b>Scan job schedule created to run every "\
                f"{self.helper.config['scanner']['autoscandelay']} hour(s)</b> \u2705"
            update.effective_message.reply_html(reply)
            # self.helper.send_telegram_message(update, reply, context=context)

    def _remove_scheduled_job(self, update, context):
        """check if scanner/screener is scheduled to run, remove if it is"""
        reply = ""
        if len(scannerSchedule.get_jobs()) > 0:
            scannerSchedule.remove_all_jobs()
            reply = "<b>Scan job schedule has been removed</b> \u2705"

        else:
            reply = "<b>No scheduled job found!</b>"

        self.helper.send_telegram_message(update, reply, context=context)

    # def conversation_handler(self, update, ) -> ConversationHandler:
    #     return ConversationHandler(
    #         entry_points=[CommandHandler("value", self.editor.conversation_handler())],
    #         states={
    #             VALUE_ENTRY : {MessageHandler(Filters.text & ~Filters.command, self.editor.conversation_handler())}
    #         },
    #         fallbacks=[CommandHandler("cancel", self.editor.conversation_handler())]
    #     )