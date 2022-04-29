""" Telegram Bot Settings """
import os
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from models.telegram import callbacktags
from models.telegram.helper import TelegramHelper


class SettingsEditor:
    """Telegram Bot Notification Settings Class"""

    def __init__(self, tg_helper: TelegramHelper) -> None:
        # self.datafolder = datafolder
        self.helper = tg_helper

        if not os.path.isfile(
            os.path.join(self.helper.datafolder, "telegram_data", "settings.json")
        ):
            self.helper.settings.update(
                {
                    "notifications": {
                        "enable_scanner": 1,
                        "enable_screener": 1,
                        "enable_start": 1,
                        "enable_stop": 1,
                        "enable_pause": 1,
                        "enable_resume": 1,
                    }
                }
            )
            self._write_config()

        self._read_config()

    def _read_config(self):
        """Read Config File"""
        try:
            with open(
                os.path.join(self.helper.datafolder, "telegram_data", "settings.json"),
                "r",
                encoding="utf8",
            ) as json_file:
                self.helper.settings = json.load(json_file)
        except FileNotFoundError:
            return
        except json.decoder.JSONDecodeError:
            return

    def _write_config(self):
        """Write config file"""
        try:
            with open(
                os.path.join(self.helper.datafolder, "telegram_data", "settings.json"),
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.helper.settings, outfile, indent=4)
        except: #pylint: disable=try-except-raise
            return

    def get_notifications(self, update):
        """Get notification option buttons"""
        self._read_config()

        notifications = {
            "enable_screener": "Screener/Scanner",
            # "enable_scanner" : "Scanner",
            # "enable_start" : "Bot Start",
            # "enable_stop" : "Bot Stop",
            # "enable_pause" : "Bot Pause",
            # "enable_resume" : "Bot Resume"
        }

        buttons = []
        for prop in notifications.items():
            setting_value = bool(self.helper.settings["notifications"][prop[0]])
            light_icon = "\U0001F7E2" if setting_value == 1 else "\U0001F534"
            buttons.append(
                InlineKeyboardButton(
                    f"{light_icon} {prop[1]}",
                    callback_data=self.helper.create_callback_data(
                        callbacktags.NOTIFY[0],
                        callbacktags.DISABLE[0]
                        if setting_value is True
                        else callbacktags.ENABLE[0],
                        prop[0],
                    )
                    # f"notify_{'disable' if setting_value is True else 'enable' }_{prop[0]}",
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
                    "\U000025C0 Back",
                    callback_data=self.helper.create_callback_data(callbacktags.BACK[0]),
                )
            ]
        )

        self.helper.send_telegram_message(
            update,
            "<b>Notification Options:</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True), new_message=False
        )

    def disable_option(self, parameter):
        """Disable Option"""
        self.helper.settings["notifications"][f"{parameter}"] = 0
        self._write_config()
        self._read_config()

    def enable_option(self, parameter):
        """Enable Option"""
        self.helper.settings["notifications"][f"{parameter}"] = 1
        self._write_config()
        self._read_config()
