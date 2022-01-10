''' Telegram Bot Config Editor '''
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from models.telegram.helper import TelegramHelper


from models.exchange.ExchangesEnum import Exchange


class ConfigEditor:
    ''' Telegram Bot Config Editor '''
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder
        self.helper = tg_helper

        self.normal_properties = {
            "live": "live Mode",
            "sellatloss": "Sell at Loss",
            "sellatresistance": "Sell at Resistance",
            "autorestart": "Auto Restart",
            "graphs": "Graphs",
            "verbose": "Verbose Logging",
            "websocket": "WebSockets",
        }

        self.disable_properties = {
            "disablebullonly": "Bull Only Mode",
            "disablebuynearhigh": "Buy Near High",
            "disablebuyema": "Buy EMA",
            "disablebuymacd": "Buy MACD",
            "disablebuyobv": "Buy OBV",
            "disablebuyelderray": "Buy Elder Ray",
            "disablefailsafefibonaccilow": "Fibonacci Low",
            "disableprofitbankreversal": "Profit Bank Reversal",
        }

        self.float_properties = {
            "trailingstoplosstrigger": "Trailing Stop Loss Trigger",
            "trailingstoploss": "Trailing Stop Loss",
            "selllowerpcnt": "Lowest Sell Point",
            "nosellminpcnt": "Dont Sell Above",
            "nosellmaxpcnt": "Dont Sell Below",
            "nobuynearhighpcnt": "Dont Buy Near High",
        }

        self.integer_properties = {
            "buymaxsize": "Max Buy Size",
            "buyminsize": "Min Buy Size",
        }

    def get_config_from_file(self, exchange: str = 'binance'):
        config = {
            "float": {},
            "int": {},
            "disabled": {},
            "normal": {}
        } 

        for param in self.helper.config[exchange]['config']:
            if type(self.helper.config[exchange]['config'][param]) is float:
                config["float"].update({param: self.helper.config[exchange]['config'][param]})
            elif param.__contains__("disable"):
                config["disabled"].update({param: self.helper.config[exchange]['config'][param]})
            elif type(self.helper.config[exchange]['config'][param]) is int \
                and (self.helper.config[exchange]['config'][param] > 1 or self.helper.config[exchange]['config'][param] < 0):
                config["int"].update({param: self.helper.config[exchange]['config'][param]})
            elif type(self.helper.config[exchange]['config'][param]) is int:
                config["normal"].update({param: self.helper.config[exchange]['config'][param]})
            # elif type(self.helper.config[exchange]['config'][param]) is not str:
            #     config["normal"].update({param: self.helper.config[exchange]['config'][param]})
            # else:
            #     config["normal"].update({param: self.helper.config[exchange]['config'][param]})

            print(param)
            print(type(self.helper.config[exchange]['config'][param]))

        print(config)
        return config
        
    def get_config_options(self, update: Update, context: CallbackContext, callback: str = ""):
        ''' Get Config Options '''
        # self.helper.load_config()
        query = update.callback_query
        if callback == "":
            if query.data.__contains__("edit_"):
                exchange = query.data.replace("edit_", "")
            elif (
                query.data.__contains__(Exchange.COINBASEPRO.value)
                or query.data.__contains__(Exchange.BINANCE.value)
                or query.data.__contains__(Exchange.KUCOIN.value)
            ):
                exchange = query.data[: query.data.find("_")]
        else:
            exchange = callback

        def check_property_exists(var) -> bool:
            if var in self.helper.config[exchange]["config"]:
                return True
            return False

        buttons = []
        config_properties = self.get_config_from_file()
        for prop in config_properties["normal"]:
            if check_property_exists(prop):
                config_value = bool(self.helper.config[exchange]['config'][prop])
                light_icon = "\U0001F7E2" if config_value == 1 else "\U0001F534"
            
                buttons.append(
                    InlineKeyboardButton(
                        f"{light_icon} {prop}",
                        callback_data=
                            f"{exchange}_{'disable' if config_value == 1 else 'enable' }_{prop}",
                    )
                )
        for prop in config_properties["disabled"]:
            if check_property_exists(prop):
                config_value = bool(self.helper.config[exchange]['config'][prop])
                light_icon = "\U0001F7E2" if config_value == 1 else "\U0001F534"
            
                buttons.append(
                    InlineKeyboardButton(
                        f"{light_icon} {prop}",
                        callback_data=
                            f"{exchange}_{'disable' if config_value == 1 else 'enable' }_{prop}",
                    )
                )

        for prop in config_properties["float"]:
            if check_property_exists(prop):
                config_value = float(self.helper.config[exchange]['config'][prop])
                buttons.append(
                    InlineKeyboardButton(
                        f"{prop}: {config_value}",
                        callback_data=f"{exchange}_float_{prop}",
                    )
                )

        for prop in config_properties["int"]:
            if check_property_exists(prop):
                if self.helper.config[exchange]['config'][prop] > 1 or self.helper.config[exchange]['config'][prop] < 0:
                    config_value = int(self.helper.config[exchange]['config'][prop])
                else:
                    config_value = bool(self.helper.config[exchange]['config'][prop])
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
            f"<b>{exchange.capitalize()} Config Options.</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
            context
        )

    def disable_option(self, exchange, parameter):
        ''' Dsiable option '''
        self.helper.config[exchange]["config"][parameter] = 0

    def enable_option(self, exchange, parameter):
        ''' Enable option '''
        self.helper.config[exchange]["config"][parameter] = 1

    def increase_value(self, exchange, parameter, unitsize):
        ''' Increase value '''
        self.helper.config[exchange]["config"][parameter] = round(
            self.helper.config[exchange]["config"][parameter] + unitsize, 1
        )

    def decrease_value(self, exchange, parameter, unitsize):
        ''' Decrease value '''
        self.helper.config[exchange]["config"][parameter] = round(
            self.helper.config[exchange]["config"][parameter] - unitsize, 1
        )

    def save_updated_config(self, update):
        ''' Save config file '''
        self.helper.write_config()
        self.helper.send_telegram_message(update, "<b>Config File Updated</b>")
