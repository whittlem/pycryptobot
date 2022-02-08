''' Telegram Bot Config Editor '''
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from models.telegram.helper import TelegramHelper
from models.exchange.ExchangesEnum import Exchange


class ConfigEditor:
    '''Telegram Bot Config Editor '''

    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder
        self.helper = tg_helper

    def get_config_from_file(self, exchange: str = "binance"):
        ''' Read config file parameters and values '''
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
        ''' Read scanner config file parameters and values '''
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
        ''' Read screener config file parameters and values '''
        config = {"float": {}, "int": {}, "disabled": {}, "normal": {}}

        for param in self.helper.screener[exchange]:
            if type(self.helper.screener[exchange][param]) is float:
                config["float"].update({param: self.helper.screener[exchange][param]})
            elif param.__contains__("disable"):
                config["disabled"].update({param: self.helper.screener[exchange][param]})
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
                exchange = query.data[: query.data.find("_")]

        else:
            exchange = callback

        buttons = []
        if exchange == "scanner":
            config_properties = self.get_scanner_config_from_file()
        elif exchange == "screener":
            config_properties = self.get_screener_config_from_file("binance")
        else:
            config_properties = self.get_config_from_file(exchange)

        for prop in config_properties["normal"]:
            config_value = bool(config_properties["normal"][prop])
            light_icon = "\U0001F7E2" if config_value == 1 else "\U0001F534"

            buttons.append(
                InlineKeyboardButton(
                    f"{light_icon} {prop}",
                    callback_data=f"{exchange}_{'disable' if config_value == 1 else 'enable' }_({prop})",
                )
            )
        for prop in config_properties["disabled"]:
            config_value = bool(config_properties["disabled"][prop])
            light_icon = "\U0001F7E2" if config_value == 1 else "\U0001F534"

            buttons.append(
                InlineKeyboardButton(
                    f"{light_icon} {prop}",
                    callback_data=f"{exchange}_{'disable' if config_value == 1 else 'enable' }_({prop})",
                )
            )

        for prop in config_properties["float"]:
            config_value = float(config_properties["float"][prop])
            buttons.append(
                InlineKeyboardButton(
                    f"{prop}: {config_value}",
                    callback_data=f"{exchange}_float_{prop}",
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
                    callback_data=f"{exchange}_integer_{prop}",
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
            [InlineKeyboardButton("\U0001F4BE Save", callback_data="save_config")]
        )
        # keyboard.append(
        #     [
        #         InlineKeyboardButton(
        #             "Reload all running bots", callback_data="reload_config"
        #         )
        #     ]
        # )
        keyboard.append([InlineKeyboardButton("\U000025C0 Back", callback_data="back")])

        self.helper.send_telegram_message(
            update,
            f"<b>{exchange.capitalize()} Config Options.</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
            context,
        )

    def get_scanner_options(self, update: Update, context: CallbackContext):
        buttons = []
        config_properties = self.helper.config["scanner"]
        for prop in config_properties:
            config_value = self.helper.config["scanner"][prop]
            light_icon = "\U0001F7E2" if config_value == 1 else "\U0001F534"

            buttons.append(
                InlineKeyboardButton(
                    f"{light_icon} {prop}",
                    callback_data=f"scanner_{'disable' if config_value == 1 else 'enable' }_{prop}",
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
            [InlineKeyboardButton("\U0001F4BE Save", callback_data="save_config")]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "Reload all running bots", callback_data="reload_config"
                )
            ]
        )
        keyboard.append([InlineKeyboardButton("\U000025C0 Back", callback_data="back")])

        self.helper.send_telegram_message(
            update,
            "<b>Scanner Config Options.</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
            context,
        )

    def disable_option(self, exchange, parameter):
        """Disable option"""
        if exchange != "scanner":
            self.helper.config[exchange]["config"][parameter] = 0
        else:
            self.helper.config[exchange][parameter] = 0

    def enable_option(self, exchange, parameter):
        """Enable option"""
        if exchange != "scanner":
            self.helper.config[exchange]["config"][parameter] = 1
        else:
            self.helper.config[exchange][parameter] = 1

    def increase_value(self, exchange, parameter, unitsize):
        """Increase value"""
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
        self.helper.send_telegram_message(update, "<b>Config File Updated</b>")
