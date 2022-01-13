''' Telegram Bot Request Handler '''
import datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext.callbackcontext import CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler

from models.telegram.control import TelegramControl
from models.telegram.helper import TelegramHelper
from models.telegram.actions import TelegramActions
from models.telegram.config import ConfigEditor
from models.telegram.settings import SettingsEditor

scannerSchedule = BackgroundScheduler(timezone="UTC")


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

    @staticmethod
    def get_request() -> InlineKeyboardMarkup:
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
                    "\U00002139 Running Bot Status", callback_data="status"
                ),
                InlineKeyboardButton("Margins \U0001F4C8", callback_data="margin"),
            ],
            [InlineKeyboardButton("Cancel", callback_data="cancel")],
        ]

        return InlineKeyboardMarkup(keyboard, one_time_keyboard=True)

    def get_response(self, update: Update, context: CallbackContext):
        """Handles responses from TG"""
        if not self._check_if_allowed(update.effective_user.id, update):
            return

        query = update.callback_query
        query.answer()

        # Default Cancel Button
        if query.data == "cancel":
            self.helper.send_telegram_message(update, "\U00002757 User Cancelled Request")

        # Default Back Button
        if query.data == "back":
            key_markup = self.get_request()
            self.helper.send_telegram_message(
                update, "<b>PyCryptoBot Command Panel.</b>", key_markup
            )

        # Settings / Notifications
        elif query.data == "botsettings":
            self.setting.get_notifications(update)
        elif query.data.__contains__("notify_disable_"):
            self.setting.disable_option(query.data[query.data.rfind("_") + 1 :])
            self.setting.get_notifications(update)  # refresh buttons
        elif query.data.__contains__("notify_enable_"):
            self.setting.enable_option(query.data[query.data.rfind("_") + 1 :])
            self.setting.get_notifications(update)  # refresh buttons

        # Show Margins
        elif query.data == "margin":
            self.ask_margin_type(update)
        elif query.data in ("margin_orders", "margin_pairs", "margin_all"):
            self.actions.get_margins(update)

        # Show Bot Info
        elif query.data == "status":
            self.actions.get_bot_info(update)

        # Show Config
        elif query.data == "showconfig":
            self.ask_config_options(update, "ex")
        elif query.data.__contains__("ex_"):
            self.actions.show_config_response(update)

        # Edit Config
        elif query.data == "editconfig":
            self.helper.load_config()
            self.ask_config_options(update, "edit")
        elif query.data.__contains__("edit_"):
            self.editor.get_config_options(update, context)
        elif query.data.__contains__("_disable_"):
            self.editor.disable_option(
                query.data[: query.data.find("_")],
                query.data[query.data.rfind("_") + 1 :],
            )
            self.editor.get_config_options(update, context)  # refresh buttons
        elif query.data.__contains__("_enable_"):
            self.editor.enable_option(
                query.data[: query.data.find("_")],
                query.data[query.data.rfind("_") + 1 :],
            )
            self.editor.get_config_options(update, context)  # refresh buttons

        elif query.data.__contains__("_float_"):
            self.ask_percent_value(update, "float")
        elif query.data.__contains__("_integer_"):
            self.ask_percent_value(update, "integer")
        elif query.data.__contains__("increase"):
            unit_size = 0.1 if query.data.__contains__("float") else 1
            self.editor.increase_value(
                query.data[: query.data.find("_")],
                query.data[query.data.rfind("_") + 1 :],
                unit_size,
            )
            typestr = "float" if query.data.__contains__("float") else "integer"
            self.ask_percent_value(update, typestr)
        elif query.data.__contains__("decrease"):
            unit_size = 0.1 if query.data.__contains__("float") else 1
            self.editor.decrease_value(
                query.data[: query.data.find("_")],
                query.data[query.data.rfind("_") + 1 :],
                unit_size,
            )
            type_str = "float" if query.data.__contains__("float") else "integer"
            self.ask_percent_value(update, type_str)
        elif query.data.__contains__("_done"):
            self.editor.get_config_options(update, query.data[: query.data.find("_")])
        elif query.data == "save_config":
            self.editor.save_updated_config(update)
            self.helper.load_config()
            self.ask_config_options(update, "edit")
        elif query.data == "reload_config":
            update.callback_query.data = "all"
            self.control.action_bot_response(update, "reload", "reload", "active")

        # Restart Bots
        elif query.data == "restart":
            self.control.ask_restart_bot_list(update)
        elif query.data.__contains__("restart_"):
            self.control.restart_bot_response(update)

        # Start Bots
        elif query.data == "start":
            self.control.ask_start_bot_list(update)
        elif query.data.__contains__("start_"):
            self.control.start_bot_response(update, context)

        # Stop Bots
        elif query.data == "stop":
            self.control.ask_stop_bot_list(update)
        elif query.data.__contains__("stop_"):
            self.control.stop_bot_response(update, context)

        # Pause Bots
        elif query.data == "pause":
            self.control.ask_pause_bot_list(update)
        elif query.data.__contains__("pause_"):
            self.control.pause_bot_response(update, context)

        # Resume Bots
        elif query.data == "resume":
            self.control.ask_resume_bot_list(update)
        elif query.data.__contains__("resume_"):
            self.control.resume_bot_response(update, context)

        # Restart Bots with Open Orders
        elif query.data == "reopen":
            self.actions.start_open_orders(update)

        # Initiate Buy order
        elif query.data == "buy":
            self.control.ask_buy_bot_list(update)
        elif query.data.__contains__("confirm_buy_"):
            self.actions.buy_response(update)
        elif query.data.__contains__("buy_"):
            self.ask_confimation(update)

        # Initiate Sell order
        elif query.data == "sell":
            self.control.ask_sell_bot_list(update)
        elif query.data.__contains__("confirm_sell_"):
            self.actions.sell_response(update)
        elif query.data.__contains__("sell_"):
            self.ask_confimation(update)

        # Delete Bot from start bot list (not on CP yet)
        elif query.data == "delete":
            self.control.ask_delete_bot_list(update)
        elif query.data.__contains__("delete_"):
            self.actions.delete_response(update)

        # Market Scanner
        elif query.data == "scanner":
            self.get_scanner_options(update)
        elif query.data == "schedule":
            self._check_scheduled_job(update, context)
        elif query.data in ("scanonly", "noscan", "startmarket"):
            if query.data == "startmarket":
                self._check_scheduled_job(update, context)
            self.helper.send_telegram_message(update, "Command Started")
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
        elif query.data.__contains__("delexcep_"):
            self.actions.remove_exception_callback(update)

        # Actions by bot (experimental)
        elif query.data.__contains__("bot_"):
            self.get_bot_options(update)

        # query.edit_message_text(
        #     "\U000026A0 <b>Under Construction</b> \U000026A0", parse_mode="HTML"
        # )

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
            [InlineKeyboardButton("\U000025C0 Back", callback_data="back")],
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
            [InlineKeyboardButton("\U000025C0 Back", callback_data="back")],
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

    def ask_margin_type(self, update):
        """Ask what user wants to see active order/pairs or all"""
        keyboard = [
            [
                InlineKeyboardButton("Active Orders", callback_data="margin_orders"),
                InlineKeyboardButton("Active Pairs", callback_data="margin_pairs"),
                InlineKeyboardButton("All", callback_data="margin_all"),
            ],
            [InlineKeyboardButton("\U000025C0 Back", callback_data="back")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        reply = "<b>Make your selection</b>"
        self.helper.send_telegram_message(update, reply, reply_markup)

    def ask_config_options(self, update: Update, callback: str = "ex"):
        """get exchanges from config file"""
        keyboard = []
        buttons = []
        for exchange in self.helper.config:
            if exchange not in ("telegram"):
                buttons.append(
                    InlineKeyboardButton(
                        exchange.capitalize(), callback_data=f"{callback}_{exchange}"
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
                    "Reload all running bots", callback_data="reload_config"
                )
            ]
        )
            keyboard.append(
                [InlineKeyboardButton("\U000025C0 Back", callback_data="back")]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)
        query = update.callback_query
        query.answer()

        self.helper.send_telegram_message(update, "<b>Select exchange</b>", reply_markup)

    def ask_percent_value(self, update, typestr):
        """get button to increase values"""
        query = update.callback_query
        split_callback = query.data.split("_")

        exchange, prop = (
            split_callback[0],
            split_callback[2],
        )
        if query.data.__contains__("*"):
            prop = split_callback[3]

        keyboard = [
            [
                InlineKeyboardButton(
                    "-", callback_data=f"{exchange}_decrease_*{typestr}*_{prop}"
                ),
                InlineKeyboardButton(
                    "+", callback_data=f"{exchange}_increase_*{typestr}*_{prop}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "\U000025C0 Done", callback_data=f"{exchange}_value_{split_callback[2]}_done"
                )
            ],
        ]
        if exchange != "scanner":
            config_value = self.helper.config[exchange]['config'][prop]
        else:
            config_value = self.helper.config[exchange][prop]
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

    def ask_confimation(self, update):
        """confirmation question"""
        query = update.callback_query
        keyboard = [
            [
                InlineKeyboardButton("Confirm", callback_data=f"confirm_{query.data}"),
            ],
            [InlineKeyboardButton("Cancel", callback_data="cancel")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        reply = f"<b>Are you sure you want to {query.data.replace('_', ' ')}?</b>"
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
            self.helper.send_telegram_message(update, reply, context=context)

    def _remove_scheduled_job(self, update, context):
        """check if scanner/screener is scheduled to run, remove if it is"""
        reply = ""
        if len(scannerSchedule.get_jobs()) > 0:
            scannerSchedule.remove_all_jobs()
            reply = "<b>Scan job schedule has been removed</b> \u2705"

        else:
            reply = "<b>No scheduled job found!</b>"

        self.helper.send_telegram_message(update, reply, context=context)
