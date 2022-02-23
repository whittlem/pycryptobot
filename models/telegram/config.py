""" Telegram Bot Config Editor """
import json
from models.telegram import callbacktags
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from models.telegram.helper import TelegramHelper
from models.exchange.ExchangesEnum import Exchange
from models.exchange.Granularity import Granularity


class ConfigEditor:
    """Telegram Bot Config Editor"""

    def __init__(self, tg_helper: TelegramHelper) -> None:
        self.helper = tg_helper

    @staticmethod
    def exchange_convert(exchange_int: int = None, exchange_str: str = ""):
        """convert exchange from an int to string"""
        if isinstance(exchange_int, int):
            if exchange_int == 0:
                return "scanner"
            if exchange_int == 1:
                return "binance"
            if exchange_int == 2:
                return "coinbasepro"
            if exchange_int == 3:
                return "kucoin"

        if exchange_str != "":
            if exchange_str == "scanner":
                return 0
            if exchange_str == "binance":
                return 1
            if exchange_str == "coinbasepro":
                return 2
            if exchange_str == "kucoin":
                return 3
        return None

    def get_config_from_file(self, exchange: str = "binance"):
        """Read config file parameters and values"""
        config = {"float": {}, "int": {}, "disabled": {}, "normal": {}}

        for param in self.helper.config[exchange]["config"]:
            if type(self.helper.config[exchange]["config"][param]) is float:
                config["float"].update(
                    {param: self.helper.config[exchange]["config"][param]}
                )
            elif param.__contains__("disable"):
                config["disabled"].update(
                    {param: self.helper.config[exchange]["config"][param]}
                )
            elif type(self.helper.config[exchange]["config"][param]) is int and (
                self.helper.config[exchange]["config"][param] > 1
                or self.helper.config[exchange]["config"][param] < 0
            ):
                config["int"].update(
                    {param: self.helper.config[exchange]["config"][param]}
                )
            elif type(self.helper.config[exchange]["config"][param]) is int:
                config["normal"].update(
                    {param: self.helper.config[exchange]["config"][param]}
                )

        return config

    def get_scanner_config_from_file(self):
        """Read scanner config file parameters and values"""
        config = {"float": {}, "int": {}, "disabled": {}, "normal": {}}

        for param in self.helper.config["scanner"]:
            if type(self.helper.config["scanner"][param]) is float:
                config["float"].update({param: self.helper.config["scanner"][param]})
            elif param.__contains__("disable"):
                config["disabled"].update({param: self.helper.config["scanner"][param]})
            elif type(self.helper.config["scanner"][param]) is int and (
                self.helper.config["scanner"][param] > 1
                or self.helper.config["scanner"][param] < 0
            ):
                config["int"].update({param: self.helper.config["scanner"][param]})
            elif type(self.helper.config["scanner"][param]) is int:
                config["normal"].update({param: self.helper.config["scanner"][param]})

        return config

    def get_screener_config_from_file(self, exchange):
        """Read screener config file parameters and values"""
        config = {"float": {}, "int": {}, "disabled": {}, "normal": {}}

        for param in self.helper.screener[exchange]:
            if type(self.helper.screener[exchange][param]) is float:
                config["float"].update({param: self.helper.screener[exchange][param]})
            elif param.__contains__("disable"):
                config["disabled"].update(
                    {param: self.helper.screener[exchange][param]}
                )
            elif type(self.helper.screener[exchange][param]) is int and (
                self.helper.screener[exchange][param] > 1
                or self.helper.screener[exchange][param] < 0
            ):
                config["int"].update({param: self.helper.screener[exchange][param]})
            elif type(self.helper.screener[exchange][param]) is int:
                config["normal"].update({param: self.helper.screener[exchange][param]})

        return config

    def get_config_options(
        self, update: Update, context: CallbackContext, callback: str = ""
    ):
        """Get Config Options"""
        query = update.callback_query
        if callback == "":
            if query.data.__contains__("edit_"):
                exchange = query.data.replace("edit_", "")
            elif (
                query.data.__contains__(Exchange.COINBASEPRO.value)
                or query.data.__contains__(Exchange.BINANCE.value)
                or query.data.__contains__(Exchange.KUCOIN.value)
                or query.data.__contains__("scanner")
                or query.data.__contains__("screener")
            ):
                exchange = query.data
        elif isinstance(callback, int):
            exchange = self.exchange_convert(callback)
        else:
            try:
                callback_json = json.loads(query.data)
                if callback_json["c"] == callbacktags.SCREENER:
                    exchange = "screener"
                    callback = callback_json["e"]
            except: # pylint: disable=bare-except
                exchange = callback

        buttons = []
        if exchange == "scanner":
            config_properties = self.get_scanner_config_from_file()
        elif exchange == "screener":
            config_properties = self.get_screener_config_from_file(callback)
        else:
            config_properties = self.get_config_from_file(exchange)

        cb_exchange = self.exchange_convert(exchange_str=exchange)

        for prop in config_properties["normal"]:
            config_value = bool(config_properties["normal"][prop])
            light_icon = "\U0001F7E2" if config_value == 1 else "\U0001F534"

            buttons.append(
                InlineKeyboardButton(
                    f"{light_icon} {prop}",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.DISABLE[0]
                        if config_value == 1
                        else callbacktags.ENABLE[0],
                        cb_exchange,
                        prop,
                    ),  # f"{exchange}_{'disable' if config_value == 1 else 'enable' }_({prop})",
                )
            )
        for prop in config_properties["disabled"]:
            config_value = bool(config_properties["disabled"][prop])
            light_icon = "\U0001F7E2" if config_value == 1 else "\U0001F534"

            buttons.append(
                InlineKeyboardButton(
                    f"{light_icon} {prop}",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.DISABLE[0]
                        if config_value == 1
                        else callbacktags.ENABLE[0],
                        cb_exchange,
                        prop,
                    ),  # f"{exchange}_{'disable' if config_value == 1 else 'enable' }_({prop})",
                )
            )

        for prop in config_properties["float"]:
            config_value = float(config_properties["float"][prop])
            buttons.append(
                InlineKeyboardButton(
                    f"{prop}: {config_value}",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.FLOAT[0], cb_exchange, prop
                    ),  # f"{exchange}_float_{prop}",
                )
            )

        for prop in config_properties["int"]:
            if config_properties["int"][prop] > 1 or config_properties["int"][prop] < 0:
                config_value = int(config_properties["int"][prop])
            else:
                config_value = bool(config_properties["int"][prop])
            buttons.append(
                InlineKeyboardButton(
                    f"{prop}: {config_value}",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.INTEGER[0], cb_exchange, prop
                    ),  # f"{exchange}_integer_{prop}",
                )
            )

        keyboard = []
        i = 0
        while i <= len(buttons) - 1:
            if len(buttons) - 1 >= i + 1:
                keyboard.append([buttons[i], buttons[i + 1]])
            else:
                keyboard.append([buttons[i]])
            i += 2
        if exchange not in ("scanner", "screener"):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "Granularity",
                        callback_data=self.helper.create_callback_data(
                            callbacktags.GRANULARITY[0], exchange
                        ),
                    )
                ]
            )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "\U0001F4BE Save",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.SAVECONFIG[0]
                    ),
                )
            ]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "\U000025C0 Back",
                    callback_data=self.helper.create_callback_data(callbacktags.BACK[0]),
                )
            ]
        )

        self.helper.send_telegram_message(
            update,
            f"<b>{exchange.capitalize()} Config Options.</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
            context, new_message=False
        )

    def get_scanner_options(self, update: Update, context: CallbackContext): #pylint: disable=missing-function-docstring
        buttons = []
        config_properties = self.helper.config["scanner"]
        for prop in config_properties:
            config_value = self.helper.config["scanner"][prop]
            light_icon = "\U0001F7E2" if config_value == 1 else "\U0001F534"

            buttons.append(
                InlineKeyboardButton(
                    f"{light_icon} {prop}",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.DISABLE[0]
                        if config_value == 1
                        else callbacktags.ENABLE[0],
                        "scanner",
                        prop,
                    ),  # f"scanner_{'disable' if config_value == 1 else 'enable' }_{prop}",
                )
            )

        keyboard = []
        i = 0
        while i <= len(buttons) - 1:
            if len(buttons) - 1 >= i + 1:
                keyboard.append([buttons[i], buttons[i + 1]])
            else:
                keyboard.append([buttons[i]])
            i += 2

        keyboard.append(
            [
                InlineKeyboardButton(
                    "\U0001F4BE Save",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.SAVECONFIG[0]
                    ),
                )
            ]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "Reload all running bots",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.RELOADCONFIG[0]
                    ),
                )
            ]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "\U000025C0 Back",
                    callback_data=self.helper.create_callback_data(callbacktags.BACK[0]),
                )
            ]
        )

        self.helper.send_telegram_message(
            update,
            "<b>Scanner Config Options.</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
            context, new_message=False
        )

    def disable_option(self, exchange, parameter):
        """Disable option"""
        exchange = self.exchange_convert(exchange_int=int(exchange))
        if exchange != "scanner":
            self.helper.config[exchange]["config"][parameter] = 0
        else:
            self.helper.config[exchange][parameter] = 0

    def enable_option(self, exchange, parameter):
        """Enable option"""
        exchange = self.exchange_convert(exchange_int=int(exchange))
        if exchange != "scanner":
            self.helper.config[exchange]["config"][parameter] = 1
        else:
            self.helper.config[exchange][parameter] = 1

    def increase_value(self, exchange, parameter, unitsize):
        """Increase value"""
        exchange = self.exchange_convert(exchange_int=int(exchange))
        if exchange != "scanner":
            self.helper.config[exchange]["config"][parameter] = round(
                self.helper.config[exchange]["config"][parameter] + unitsize, 1
            )
        else:
            self.helper.config[exchange][parameter] = round(
                self.helper.config[exchange][parameter] + unitsize, 1
            )

    def decrease_value(self, exchange, parameter, unitsize):
        """Decrease value"""
        exchange = self.exchange_convert(exchange_int=int(exchange))
        if exchange != "scanner":
            self.helper.config[exchange]["config"][parameter] = round(
                self.helper.config[exchange]["config"][parameter] - unitsize, 1
            )
        else:
            self.helper.config[exchange][parameter] = round(
                self.helper.config[exchange][parameter] - unitsize, 1
            )

    def save_updated_config(self, update):
        """Save config file"""
        self.helper.write_config()
        self.helper.send_telegram_message(update, "<b>Config File Updated</b>", new_message=False)

    def get_granularity(self, update, exchange, context): #pylint: disable=missing-function-docstring
        cb_exchange = self.exchange_convert(exchange_str=exchange)
        buttons = []
        for gran in Granularity:
            config_value = (
                self.helper.config[exchange]["config"]["granularity"]
                if "granularity" in self.helper.config[exchange]["config"]
                else "SS"
            )
            gran_convert = gran.to_integer if exchange == "coinbasepro" else gran.to_short if exchange == "kucoin" else gran.to_medium
            light_icon = (
                "\U0001F534" if config_value != str(gran_convert) else "\U0001F7E2") #U0001F7E2

            buttons.append(
                InlineKeyboardButton(
                    f"{light_icon} {gran.name}",
                    callback_data=self.helper.create_callback_data(callbacktags.GRANULARITY[0], cb_exchange, gran.name) #f"{cb_exchange}_granularity_({gran.name})",
                )
            )

        keyboard = []
        i = 0
        while i <= len(buttons) - 1:
            if len(buttons) - 1 >= i + 1:
                keyboard.append([buttons[i], buttons[i + 1]])
            else:
                keyboard.append([buttons[i]])
            i += 2

        light_icon = "\U0001F7E2" if config_value == "SS" else "\U0001F534"
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{light_icon} Smart Switch",
                    callback_data=self.helper.create_callback_data(callbacktags.GRANULARITY[0], cb_exchange, "smartswitch") #f"{exchange}_granularity_(smartswitch)",
                )
            ]
        )

        keyboard.append(
            [InlineKeyboardButton("\U0001F4BE Save", callback_data=self.helper.create_callback_data(callbacktags.SAVECONFIG[0]))] # "save_config")]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "\U000025C0 Back",
                    callback_data=self.helper.create_callback_data(callbacktags.BACK[0]),
                )
            ]
        )
        self.helper.send_telegram_message(
            update,
            f"<b>{exchange.capitalize()} Granularity Options.</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
            context,
        )


#     def conversation_handler(self, update, context):
#
#         self.helper.send_telegram_message(update, self.helper.config["binance"]["granularity"], context=context)
#         # return VALUE_ENTRY
