import os, json
from models.telegram.helper import TelegramHelper
from telegram import  InlineKeyboardButton, InlineKeyboardMarkup

# BUTTON_REPLY, TYPING_RESPONSE = range(2)

class SettingsEditor():
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder
        self.helper = tg_helper
        # self.config = {}

        if not os.path.isfile(os.path.join(self.datafolder, "telegram_data", "settings.json")):
            self.helper.settings.update({"notifications": {"enable_scanner": 1, "enable_screener": 1,"enable_start": 1,"enable_stop": 1,"enable_pause": 1,"enable_resume": 1,}})
            self._write_config()

        self._read_config()

    def _read_config(self):
        try:
            with open(os.path.join(self.datafolder, "telegram_data", "settings.json"), "r", encoding="utf8") as json_file:
                self.helper.settings = json.load(json_file)
        except FileNotFoundError:
            return 
        except json.decoder.JSONDecodeError:
            return 

    def _write_config(self):
        try:
            with open(
                os.path.join(self.datafolder, "telegram_data", "settings.json"),
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.helper.settings, outfile, indent=4)
        except:
            raise

    def getNotifications(self, update):
        self._read_config()

        notifications = {
            "enable_screener" : "Screener",
            "enable_scanner" : "Scanner",
            "enable_start" : "Bot Start",
            "enable_stop" : "Bot Stop",
            "enable_pause" : "Bot Pause",
            "enable_resume" : "Bot Resume"
        }

        buttons = []
        for prop in notifications:
            buttons.append(
                InlineKeyboardButton(
                        f"{notifications[prop]} {'Disabled' if self.helper.settings['notifications'][prop] == 0 else 'Enabled'}",
                        callback_data=f"notify_{'disable' if self.helper.settings['notifications'][prop] == 1 else 'enable' }_{prop}")
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
            "<b>Notification Options:</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
        )

    def disable_option(self, parameter):
        self.helper.settings["notifications"][f"enable_{parameter}"] = 0
        self._write_config()
        self._read_config()

    def enable_option(self, parameter):
        self.helper.settings["notifications"][f"enable_{parameter}"] = 1
        self._write_config()
        self._read_config()