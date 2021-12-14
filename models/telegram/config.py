import os, json
from models.telegram.helper import TelegramHelper
from telegram import ReplyKeyboardRemove, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CommandHandler, CallbackContext, CallbackQueryHandler

BUTTON_REPLY, TYPING_RESPONSE = range(2)

class ConfigEditor():
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder
        
        self.helper = tg_helper

    def get_conversation_handler(self):
        return ConversationHandler(entry_points=[CallbackQueryHandler(self.ask_buy_max_size, pattern='edit_buymaxsize')],
        states={
            TYPING_RESPONSE: [CallbackQueryHandler(self.buy_max_size)],
            },
        fallbacks=[CommandHandler('cancel', self.cancel)],
        )
        # return ConversationHandler(entry_points=[CommandHandler("buymax", self.ask_buy_max_size)],
        # states={
        #     TYPING_RESPONSE: [
        #         MessageHandler(
        #             Filters.text, self.buy_max_size
        #         )],
        #     },
        # fallbacks=[CommandHandler('cancel', self.cancel)],
        # )

    def getConfigOptions(self):
        keyboard = [
            [
                InlineKeyboardButton("BuyMaxSize", callback_data="edit_buymaxsize"),
            ],
            [InlineKeyboardButton("\U000025C0 Back", callback_data="back")],
        ]

        return InlineKeyboardMarkup(keyboard, one_time_keyboard=True)

    def cancel(self, update: Update, context: CallbackContext) -> int:
        """Cancels and ends the conversation."""
        # user = update.message.from_user
        # logger.info("User %s canceled the conversation.", user.first_name)
        update.message.reply_text(
            'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove()
        )

        return ConversationHandler.END

    def updateconfig(self, update, key, value):
        # if key == "buymaxsize":
        #     self.buy_max_size(value)


        update.message.reply_text(f"[{key}] Updated to: {value}")

    def ask_buy_max_size(self, update: Update, context):
        try:
            update.message.reply_text("What is the new value?")
        except:
            query = update.callback_query
            query.answer()
            query.edit_message_text(
                "What is the new value?")

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