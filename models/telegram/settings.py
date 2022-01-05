import os, json
from models.telegram.helper import TelegramHelper
from telegram import ReplyKeyboardRemove, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CommandHandler, CallbackContext, CallbackQueryHandler

# BUTTON_REPLY, TYPING_RESPONSE = range(2)

class SettingsEditor():
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder
        self.helper = tg_helper
        self.settings = {}

    def _read_config(self):
        try:
            with open(os.path.join(self.datafolder, "telegram_data", "settings.json"), "r", encoding="utf8") as json_file:
                self.settings = json.load(json_file)
        except FileNotFoundError:
            return 
        except json.decoder.JSONDecodeError:
            return 


    def askSettings(self, update):
        query = update.callback_query

        keyboard = [
            [
                InlineKeyboardButton(
                    "Disable Screener", callback_data=f"stop_{query.data.replace('bot_', '')}"
                )
            ],
            [
                InlineKeyboardButton(
                    "Disable Scanner", callback_data=f"restart_{query.data.replace('bot_', '')}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Disable Bot Start", callback_data=f"pause_{query.data.replace('bot_', '')}"
                ),
                InlineKeyboardButton(
                    "Disable Bot Stop", callback_data=f"resume_{query.data.replace('bot_', '')}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Disable Bot Pause", callback_data=f"pause_{query.data.replace('bot_', '')}"
                ),
                InlineKeyboardButton(
                    "Disable Bot Resume", callback_data=f"resume_{query.data.replace('bot_', '')}"
                ),
            ],
            [InlineKeyboardButton("\U000025C0 Back", callback_data="back")],
        ]

        query.edit_message_text(
            "<b>Notifications:</b>",
            reply_markup=InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
            parse_mode="HTML",
        )