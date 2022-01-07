import os, json
from models.telegram.helper import TelegramHelper
from telegram import ReplyKeyboardRemove, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CommandHandler, CallbackContext, CallbackQueryHandler

BUTTON_REPLY, TYPING_RESPONSE = range(2)

class ConfigEditor():
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder
        self.helper = tg_helper

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

    def getConfigOptions(self, update, callback: str = ''):
        query = update.callback_query

        if callback == '':
            if query.data.__contains__("edit_"):
                exchange = query.data.replace('edit_', '')
            elif query.data.__contains__("coinbasepro") or query.data.__contains__('binance') or query.data.__contains__('kucoin'):
                exchange = query.data[:query.data.find('_')]
        else:
            exchange = callback
        
        normalProperties = {
            "live": "live Mode",
            "sellatloss": "Sell at Loss",
            "sellatresistance": "Sell at Resistance",
            "autorestart": "Auto Restart",
            "graphs": "Graphs",
            "verbose": "Verbose Logging",
            "websocket": "WebSockets"
        }
        disableProperties = {
            "disablebullonly": "Bull Only Mode",
            "disablebuynearhigh": "Buy Near High",
            "disablebuyema": "Buy EMA",
            "disablebuymacd": "Buy MACD",
            "disablebuyobv": "Buy OBV",
            "disablebuyelderray": "Buy Elder Ray",
            "disablefailsafefibonaccilow": "Fibonacci Low",
            "disableprofitbankreversal": "Profit Bank Reversal",
        }

        buttons = []
        for prop in normalProperties:
            buttons.append(
                InlineKeyboardButton(
                        f"{'Disable' if self.helper.config[exchange]['config'][prop] == 1 else 'Enable'} {normalProperties[prop]}",
                        callback_data=f"{exchange}_{'disable' if self.helper.config[exchange]['config'][prop] == 1 else 'enable' }_{prop}")
            )
        for prop in disableProperties:
            buttons.append(
                InlineKeyboardButton(
                        f"{'Enable' if self.helper.config[exchange]['config'][prop] == 1 else 'Disable'} {disableProperties[prop]}",
                        callback_data=f"{exchange}_{'disable' if self.helper.config[exchange]['config'][prop] == 1 else 'enable' }_{prop}")
            )

        for prop in self.floatProperties:
            buttons.append(
                InlineKeyboardButton(
                        f"{self.floatProperties[prop]}: {self.helper.config[exchange]['config'][prop]}",
                        callback_data=f"{exchange}_float_{prop}")
            )

        for prop in self.integerProperties:
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

        keyboard.append([InlineKeyboardButton("\U000025C0 Back", callback_data="back")])

        self.helper.sendtelegramMsg(update,
            f"<b>{exchange} Config Options.</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        )

    def cancel(self, update: Update, context: CallbackContext) -> int:
        """Cancels and ends the conversation."""
        # user = update.message.from_user
        # logger.info("User %s canceled the conversation.", user.first_name)
        self.helper.sendtelegramMsg(update, 
            'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove()
        )

        return ConversationHandler.END

    def updateconfig(self, update, key, value):
        # if key == "buymaxsize":
        #     self.buy_max_size(value)
        self.helper.sendtelegramMsg(update, f"[{key}] Updated to: {value}")

    def ask_buy_max_size(self, update: Update, context):
        self.helper.sendtelegramMsg(update, "What is the new value?")

        return TYPING_RESPONSE
    
    def buy_max_size(self, update: Update, context):
        if update.message.text.lower() == "done":
            return None

        try:
            amount = float(update.message.text)
        
            self.helper.read_data(self.helper.config_file)

            with open(os.path.join(self.helper.config_file), "r", encoding="utf8") as json_file:
                self.helper.config = json.load(json_file)

            if amount > 0.0:
                for ex in self.helper.config:
                    if ex not in ("telegram", "scanner"):
                        self.helper.config[ex]["config"].update({"buymaxsize": amount})

            self.helper.write_data()
            with open(os.path.join(self.helper.config_file), "w", encoding="utf8") as outfile:
                json.dump(self.helper.config, outfile, indent=4)

        except:
            pass

        # update.message.reply_text("Config Updated")
    
    def disable_option(self, exchange, parameter):
        self.helper.loadConfig()
        self.helper.config[exchange]["config"][parameter] = 0
        self.helper.write_config()

    def enable_option(self, exchange, parameter):
        self.helper.loadConfig()
        self.helper.config[exchange]["config"][parameter] = 1
        self.helper.write_config()

    def increase_value(self, exchange, parameter, unitsize):
        self.helper.loadConfig()
        self.helper.config[exchange]["config"][parameter] = round(self.helper.config[exchange]["config"][parameter] + unitsize, 1)
        self.helper.write_config()

    def decrease_value(self, exchange, parameter, unitsize):
        self.helper.loadConfig()
        self.helper.config[exchange]["config"][parameter] = round(self.helper.config[exchange]["config"][parameter] - unitsize, 1)
        self.helper.write_config()
