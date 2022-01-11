""" Telegram Bot Settings """
import os
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from models.telegram.helper import TelegramHelper


class SettingsEditor:
    """Telegram Bot Notification Settings Class"""

    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder
        self.helper = tg_helper

        if not os.path.isfile(
            os.path.join(self.datafolder, "telegram_data", "settings.json")
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
                os.path.join(self.datafolder, "telegram_data", "settings.json"),
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
                os.path.join(self.datafolder, "telegram_data", "settings.json"),
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.helper.settings, outfile, indent=4)
        except:
            raise

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
            setting_value = bool(self.helper.settings['notifications'][prop[0]])
            buttons.append(
                InlineKeyboardButton(
                    f"{prop[1]} {'Disabled' if setting_value is False else 'Enabled'}",
                    callback_data=
                        f"notify_{'disable' if setting_value is True else 'enable' }_{prop[0]}",
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

        keyboard.append([InlineKeyboardButton("\U000025C0 Back", callback_data="back")])

        self.helper.send_telegram_message(
            update,
            "<b>Notification Options:</b>",
            InlineKeyboardMarkup(keyboard, one_time_keyboard=True),
        )

    def disable_option(self, parameter):
        """Disable Option"""
        self.helper.settings["notifications"][f"enable_{parameter}"] = 0
        self._write_config()
        self._read_config()

    def enable_option(self, parameter):
        """Enable Option"""
        self.helper.settings["notifications"][f"enable_{parameter}"] = 1
        self._write_config()
        self._read_config()
