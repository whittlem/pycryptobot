import os, json
from models.telegram.Helper import TelegramHelper
from telegram.replykeyboardremove import ReplyKeyboardRemove
from telegram.ext import Updater

helper = None
TYPING_RESPONSE = range(1)

class Editor():
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder
        global helper ; helper = tg_helper

    def updateconfig(self, update, key, value):
        # if key == "buymaxsize":
        #     self.buy_max_size(value)


        update.message.reply_text(f"[{key}] Updated to: {value}")

    def ask_buy_max_size(self, update, context):
        query = update.callback_query
        # query.answer()
        update.message.reply_text(
            "What is the new value?")

        return TYPING_RESPONSE
    
    def buy_max_size(self, update, context):
        if update.message.text.lower() == "done":
            return None

        try:
            amount = float(update.message.text)
        
            helper.read_data(helper.config_file)

            with open(os.path.join(helper.config_file), "r", encoding="utf8") as json_file:
                helper.config = json.load(json_file)

            if amount > 0.0:
                for ex in helper.config:
                    if ex not in ("telegram", "scanner"):
                        helper.config[ex]["config"].update({"buymaxsize": amount})

            helper.write_data()
            with open(os.path.join(helper.config_file), "w", encoding="utf8") as outfile:
                    json.dump(helper.config, outfile, indent=4)

        except:
            pass

        # update.message.reply_text("Config Updated")