from models.telegram.helper import TelegramHelper
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from models.exchange.ExchangesEnum import Exchange

class ConfigEditor():
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder
        self.helper = tg_helper

        self.normalProperties = {
            "live": "live Mode",
            "sellatloss": "Sell at Loss",
            "sellatresistance": "Sell at Resistance",
            "autorestart": "Auto Restart",
            "graphs": "Graphs",
            "verbose": "Verbose Logging",
            "websocket": "WebSockets"
        }

        self.disableProperties = {
            "disablebullonly": "Bull Only Mode",
            "disablebuynearhigh": "Buy Near High",
            "disablebuyema": "Buy EMA",
            "disablebuymacd": "Buy MACD",
            "disablebuyobv": "Buy OBV",
            "disablebuyelderray": "Buy Elder Ray",
            "disablefailsafefibonaccilow": "Fibonacci Low",
            "disableprofitbankreversal": "Profit Bank Reversal",
        }

        self.floatProperties = {
            "trailingstoplosstrigger" : "Trailing Stop Loss Trigger",
            "trailingstoploss" : "Trailing Stop Loss",
            "selllowerpcnt" : "Lowest Sell Point",
            "nosellminpcnt" : "Dont Sell Above",
            "nosellmaxpcnt" : "Dont Sell Below",
            "nobuynearhighpcnt" : "Dont Buy Near High"
        }

        self.integerProperties = {
            "buymaxsize": "Max Buy Size",
            "buyminsize" : "Min Buy Size"
        }

    def getConfigOptions(self, update: Update, callback: str = ''):
        self.helper.loadConfig()
        query = update.callback_query
        if callback == '':
            if query.data.__contains__("edit_"):
                exchange = query.data.replace('edit_', '')
            elif query.data.__contains__(Exchange.COINBASEPRO.value) \
                or query.data.__contains__(Exchange.BINANCE.value) \
                or query.data.__contains__(Exchange.KUCOIN.value):
                    exchange = query.data[:query.data.find('_')]
        else:
            exchange = callback
        
        def checkPropertyExists(var) -> bool:
            if var in self.helper.config[exchange]['config']:
                return True
            return False

        buttons = []
        for prop in self.normalProperties:
            if checkPropertyExists(prop):
                buttons.append(
                    InlineKeyboardButton(
                            f"{'Disable' if self.helper.config[exchange]['config'][prop] == 1 else 'Enable'} {self.normalProperties[prop]}",
                            callback_data=f"{exchange}_{'disable' if self.helper.config[exchange]['config'][prop] == 1 else 'enable' }_{prop}")
                )
        for prop in self.disableProperties:
            if checkPropertyExists(prop):
                buttons.append(
                    InlineKeyboardButton(
                            f"{'Enable' if self.helper.config[exchange]['config'][prop] == 1 else 'Disable'} {self.disableProperties[prop]}",
                            callback_data=f"{exchange}_{'disable' if self.helper.config[exchange]['config'][prop] == 1 else 'enable' }_{prop}")
                )

        for prop in self.floatProperties:
            if checkPropertyExists(prop):
                buttons.append(
                    InlineKeyboardButton(
                            f"{self.floatProperties[prop]}: {self.helper.config[exchange]['config'][prop]}",
                            callback_data=f"{exchange}_float_{prop}")
                )

        for prop in self.integerProperties:
            if checkPropertyExists(prop):
                buttons.append(
                    InlineKeyboardButton(
                            f"{self.integerProperties[prop]}: {self.helper.config[exchange]['config'][prop]}",
                            callback_data=f"{exchange}_integer_{prop}")
                )

        keyboard = []
        i = 0
        while i <= len(buttons) - 1:
            if len(buttons) - 1 >= i + 1:
                keyboard.append([buttons[i], buttons[i + 1]])
            else:
                keyboard.append([buttons[i]])
            i += 2

        keyboard.append([InlineKeyboardButton("\U0001F4BE Save", callback_data="save_config")])
        keyboard.append([InlineKeyboardButton("Reload all running bots", callback_data="reload_config")])
        keyboard.append([InlineKeyboardButton("\U000025C0 Back", callback_data="back")])

        self.helper.sendtelegramMsg(update,
            f"<b>{exchange.capitalize()} Config Options.</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        )

    def disable_option(self, exchange, parameter):
        self.helper.config[exchange]["config"][parameter] = 0

    def enable_option(self, exchange, parameter):
        self.helper.config[exchange]["config"][parameter] = 1

    def increase_value(self, exchange, parameter, unitsize):
        self.helper.config[exchange]["config"][parameter] = round(self.helper.config[exchange]["config"][parameter] + unitsize, 1)

    def decrease_value(self, exchange, parameter, unitsize):
        self.helper.config[exchange]["config"][parameter] = round(self.helper.config[exchange]["config"][parameter] - unitsize, 1)


    def save_updated_config(self, update):
        self.helper.write_config()
        self.helper.sendtelegramMsg(update,"<b>Config File Updated</b>")
