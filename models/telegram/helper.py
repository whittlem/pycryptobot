""" Telegram Bot Helper """
import os
import platform
import subprocess
import json
import logging

# from time import sleep
from json.decoder import JSONDecodeError

# from time import sleep
from datetime import datetime
from typing import List
from telegram import InlineKeyboardMarkup, Update
import telegram
from telegram.ext import Updater
from telegram.ext.callbackcontext import CallbackContext

if not os.path.exists(os.path.join(os.curdir, "telegram_logs")):
    os.mkdir(os.path.join(os.curdir, "telegram_logs"))

# logging.basicConfig(
#     filename=os.path.join(
#         os.curdir,
#         "telegram_logs",
#         f"telegrambot {datetime.now().strftime('%Y-%m-%d')}.log",
#     ),
#     filemode="w",
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#     level=logging.INFO,
# )

# logger = logging.getLogger(__name__)


class TelegramHelper:
    """Telegram Bot Helper"""

    def __init__(self, configfile = 'config.json', logfileprefix = 'telegrambot', test_run: bool = False) -> None:
        self.data = {}
        self.config_file = configfile
        self.screener = {}
        self.settings = {}

        logging.basicConfig(
        filename=os.path.join(
            os.curdir,
            "telegram_logs",
            f"{logfileprefix} {datetime.now().strftime('%Y-%m-%d')}.log",
        ),
        filemode="w",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

        # self.logger = None
        self.logger = logging.getLogger("telegram.helper")

        with open(os.path.join(configfile), "r", encoding="utf8") as json_file:
            self.config = json.load(json_file)

        self.load_config()
        self.read_screener_config(test_run)

        if len(self.logger.handlers) == 0:
            self.logger.setLevel(self.get_level(self.logger_level))
            # set a format which is simpler for console use
            consoleHandlerFormatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            # define a Handler which writes sys.stdout
            consoleHandler = logging.StreamHandler()
            # Set log level
            consoleHandler.setLevel(self.get_level(self.logger_level))
            # tell the handler to use this format
            consoleHandler.setFormatter(consoleHandlerFormatter)
            # add the handler to the root logger
            self.logger.addHandler(consoleHandler)

        # self.updater = Updater(
        #     self.config["telegram"]["token"],
        #     use_context=True,
        # )

    def get_uptime(self):
        """Get uptime"""
        date = self.data['botcontrol']['started']
        now = str(datetime.now())
        # If date passed from datetime.now() remove milliseconds
        if date.find(".") != -1:
            date_time = date.split(".")[0]
            date = date_time
        if now.find(".") != -1:
            date_time = now.split(".", maxsplit=1)[0]
            now = date_time

        now = now.replace("T", " ")
        now = f"{now}"
        # Add time in case only a date is passed in
        # new_date_str = f"{date} 00:00:00" if len(date) == 10 else date
        date = date.replace("T", " ") if date.find("T") != -1 else date
        # Add time in case only a date is passed in
        new_date_str = f"{date} 00:00:00" if len(date) == 10 else date

        started = datetime.strptime(new_date_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        duration = now - started
        duration_in_s = duration.total_seconds()
        hours = divmod(duration_in_s, 3600)[0]
        duration_in_s -= 3600 * hours
        minutes = divmod(duration_in_s, 60)[0]
        return f"{round(hours)}h {round(minutes)}m"

    @classmethod
    def get_level(cls, level):  # pylint: disable=missing-function-docstring
        if level == "CRITICAL":
            return logging.CRITICAL
        if level == "ERROR":
            return logging.ERROR
        if level == "WARNING":
            return logging.WARNING
        if level == "INFO":
            return logging.INFO
        if level == "DEBUG":
            return logging.DEBUG
        return logging.NOTSET

    def load_config(self):
        """Load/Reread scanner config file from file"""
        self.read_config()

        self.atr72pcnt = 2.0
        self.enableleverage = False
        self.use_default_scanner = True
        self.maxbotcount = 0
        self.exchange_bot_count = 0
        self.terminal_start_process = ""
        self.autoscandelay = 0
        self.enable_buy_next = True
        self.autostart = False

        self.atr72pcnt = 2.0
        self.enableleverage = False
        self.use_default_scanner = True
        self.maxbotcount = 0
        self.exchange_bot_count = 0
        self.terminal_start_process = ""
        self.autoscandelay = 0
        self.enable_buy_next = True
        self.autostart = False

        if "scanner" in self.config:
            self.atr72pcnt = (
                self.config["scanner"]["atr72_pcnt"]
                if "atr72_pcnt" in self.config["scanner"]
                else 2.0
            )
            self.enableleverage = (
                bool(self.config["scanner"]["enableleverage"])
                if "enableleverage" in self.config["scanner"]
                else False
            )
            self.use_default_scanner = (
                bool(self.config["scanner"]["use_default_scanner"])
                if "use_default_scanner" in self.config["scanner"]
                else True
            )
            self.maxbotcount = (
                self.config["scanner"]["maxbotcount"]
                if "maxbotcount" in self.config["scanner"]
                else 0
            )
            self.exchange_bot_count = (
                self.config["scanner"]["exchange_bot_count"]
                if "exchange_bot_count" in self.config["scanner"]
                else 0
            )
            self.terminal_start_process = (
                self.config["scanner"]["terminal_start_process"]
                if "terminal_start_process" in self.config["scanner"]
                else ""
            )
            self.autoscandelay = (
                self.config["scanner"]["autoscandelay"]
                if "autoscandelay" in self.config["scanner"]
                else 0
            )
            self.enable_buy_next = (
                bool(self.config["scanner"]["enable_buy_next"])
                if "enable_buy_next" in self.config["scanner"]
                else True
            )
            self.autostart = (
                bool(self.config["scanner"]["autostart"])
                if "autostart" in self.config["scanner"]
                else False
            )

        self.datafolder = os.curdir
        self.logger_level = "INFO"

        if "telegram" in self.config:
            self.datafolder = (
                self.config["telegram"]["datafolder"]
                if "datafolder" in self.config["telegram"]
                else os.curdir
            )
            self.logger_level = (
                self.config["telegram"]["logger_level"]
                if "logger_level" in self.config["telegram"]
                else "INFO"
            )
            

    def send_telegram_message(
        self,
        update: Update,
        reply,
        markup: InlineKeyboardMarkup = None,
        context: CallbackContext = None,
        new_message: bool = True,
    ):
        """Send telegram messages"""
        if context is None:
            context = telegram.CallbackQuery(
            id=2,
            from_user=self.config["telegram"]["user_id"],
            bot=Updater(self.config["telegram"]["token"],
            use_context=True).bot,
            chat_instance="",
        )

        if new_message or update == None:
            context.bot.send_message(
                chat_id=self.config["telegram"]["user_id"],
                text=reply,
                reply_markup=markup,
                parse_mode="HTML",
            )
        else:
            context.bot.edit_message_text(
                chat_id=update.effective_message.chat_id,
                message_id=update.effective_message.message_id,
                text=reply,
                reply_markup=markup,
                parse_mode="HTML",
            )

    def read_data(self, name: str = "data.json") -> bool:
        """Read data from json file"""
        fname = name if name.__contains__(".json") else f"{name}.json"
        # self.logger.debug("METHOD(read_data) - DATA(%s)", fname)
        read_ok, try_count = False, 0
        while not read_ok and try_count <= 20:
            try_count += 1
            try:
                self.data = {}
                with open(
                    os.path.join(self.datafolder, "telegram_data", fname),
                    "r",
                    encoding="utf8",
                ) as json_file:
                    self.data = json.load(json_file)
                read_ok = True
            except FileNotFoundError:
                if try_count == 20:
                    self.logger.error("File Not Found {%s}", fname)
            except JSONDecodeError:
                if try_count == 20:
                    self.logger.error("Unable to read file {%s}", fname)

        return read_ok

    def write_data(self, name: str = "data.json") -> None:
        """Write data to json file"""
        fname = name if name.__contains__(".json") else f"{name}.json"
        self.logger.debug("METHOD(write_data) - DATA(%s)", fname)
        try:
            with open(
                os.path.join(self.datafolder, "telegram_data", fname),
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.data, outfile, indent=4)
                return True
        except JSONDecodeError as err:
            self.logger.error(err)
            return False

    def read_config(self):
        """Read config file"""
        self.logger.debug("METHOD(read_config)")
        try:
            with open(
                os.path.join(self.config_file), "r", encoding="utf8"
            ) as json_file:
                self.config = json.load(json_file)
        except FileNotFoundError:
            return
        except json.decoder.JSONDecodeError:
            return

    def write_config(self) -> bool:
        """Write config file"""
        self.logger.debug("METHOD(write_config)")
        try:
            with open(
                os.path.join(self.config_file),
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.config, outfile, indent=4)
            return True
        except:  # pylint: disable=bare-except
            return False

    def read_screener_config(self, test_run: bool = False):
        """Read screener config file"""
        self.logger.debug("METHOD(read_screener_config)")
        try:
            with open("screener.json" if not test_run else "screener.json.sample", "r", encoding="utf8") as json_file:
                self.screener = json.load(json_file)
        except FileNotFoundError:
            return
        except json.decoder.JSONDecodeError:
            return

    def write_screener_config(self):
        """Write screener config file"""
        self.logger.debug("METHOD(write_screener_config)")
        try:
            with open(
                "screener.json",
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.screener, outfile, indent=4)
        except:  # pylint: disable=bare-except
            return

    def get_all_bot_list(self) -> List[str]:
        """Return ALL contents of telegram_data folder"""
        self.logger.debug("METHOD(get_all_bot_list)")
        jsonfiles = sorted(os.listdir(os.path.join(self.datafolder, "telegram_data")))

        i = len(jsonfiles) - 1
        while i >= 0:
            if (
                jsonfiles[i] == "data.json"
                or jsonfiles[i].__contains__("output.json")
                or jsonfiles[i].__contains__(".csv")
                or jsonfiles[i] == "settings.json"
            ):
                jsonfiles.pop(i)
            else:
                read_ok = self.read_data(jsonfiles[i])
                if not read_ok:
                    jsonfiles.pop(i)
            i -= 1
        jsonfiles.sort()
        return [
            x.replace(".json", "") if x.__contains__(".json") else x for x in jsonfiles
        ]

    def get_active_bot_list(self, state: str = "active") -> List[str]:
        """Return contents of telegram_data folder"""
        self.logger.debug("METHOD(get_active_bot_list) - DATA(%s)", state)
        jsonfiles = self.get_all_bot_list()

        i = len(jsonfiles) - 1
        while i >= 0:
            read_ok = self.read_data(jsonfiles[i])
            if not read_ok:
                jsonfiles.pop(i)
                i -= 1
                continue
            if "botcontrol" in self.data:
                if not self.data["botcontrol"]["status"] == state:
                    jsonfiles.pop(i)
            i -= 1
        jsonfiles.sort()
        return [
            x.replace(".json", "") if x.__contains__(".json") else x for x in jsonfiles
        ]

    def get_active_bot_list_with_open_orders(self, state: str = "active") -> List[str]:
        """Return contents of telegram_data folder active bots with an open order"""
        self.logger.debug(
            "METHOD(get_active_bot_list_with_open_orders) - DATA(%s)", state
        )
        jsonfiles = self.get_all_bot_list()

        i = len(jsonfiles) - 1
        while i >= 0:
            read_ok = self.read_data(jsonfiles[i])
            if not read_ok:
                jsonfiles.pop(i)
                i -= 1
                continue
            if "botcontrol" in self.data:
                if self.data["margin"] == " ":
                    jsonfiles.pop(i)
            i -= 1
        jsonfiles.sort()
        return [
            x.replace(".json", "") if x.__contains__(".json") else x for x in jsonfiles
        ]

    def get_hung_bot_list(self, state: str = "active") -> List[str]:
        """Return contents of telegram_data folder - working out which are hung bots"""
        self.logger.debug("METHOD(get_hung_bot_list) - DATA(%s)", state)
        jsonfiles = self.get_all_bot_list()

        i = len(jsonfiles) - 1
        while i >= 0:
            read_ok = self.read_data(jsonfiles[i])
            if not read_ok:
                jsonfiles.pop(i)
                i -= 1
                continue
            elif "botcontrol" in self.data:
                if "watchdog_ping" in self.data["botcontrol"]:
                    last_ping = datetime.strptime(
                        self.data["botcontrol"]["watchdog_ping"], "%Y-%m-%dT%H:%M:%S.%f"
                    )
                    current_dt = datetime.now()
                    ping_delta = int((current_dt - last_ping).total_seconds())
                    if self.data["botcontrol"]["status"] == state and ping_delta < 600:
                        jsonfiles.pop(i)
                else:
                    start_time = datetime.strptime(
                        self.data["botcontrol"]["started"], "%Y-%m-%dT%H:%M:%S.%f"
                    )
                    current_dt = datetime.now()
                    start_delta = int((current_dt - start_time).total_seconds())
                    if self.data["botcontrol"]["status"] == state and start_delta < 300:
                        jsonfiles.pop(i)
            i -= 1
        jsonfiles.sort()
        return [
            x.replace(".json", "") if x.__contains__(".json") else x for x in jsonfiles
        ]

    def get_manual_started_bot_list(self, startMethod: str = "telegram") -> List[str]:
        """Return contents of telegram_data folder"""
        self.logger.debug("METHOD(get_manual_started_bot_list) - DATA(%s)", startMethod)
        jsonfiles = self.get_all_bot_list()

        i = len(jsonfiles) - 1
        while i >= 0:
            read_ok = self.read_data(jsonfiles[i])
            if not read_ok:
                jsonfiles.pop(i)
                i -= 1
                continue
            if "botcontrol" in self.data:
                if not self.data["botcontrol"]["startmethod"] == startMethod:
                    jsonfiles.pop(i)
            i -= 1
        jsonfiles.sort()
        return [
            x.replace(".json", "") if x.__contains__(".json") else x for x in jsonfiles
        ]

    def get_exchange_bot_ruuning_count(self, exchange):
        """Return contents of telegram_data folder"""
        self.logger.debug("METHOD(get_exchange_bot_ruuning_count) - DATA(%s)", exchange)
        jsonfiles = self.get_all_bot_list()

        i = len(jsonfiles) - 1
        while i >= 0:
            read_ok = self.read_data(jsonfiles[i])
            if not read_ok:
                jsonfiles.pop(i)
                i -= 1
                continue
            if "exchange" in self.data:
                if not self.data["exchange"] == exchange:
                    jsonfiles.pop(i)
            i -= 1
        # jsonfiles.sort()
        # jsonfiles.count()
        self.logger.debug(
            "METHOD(get_exchange_bot_ruuning_count) - RETURN(%s)", len(jsonfiles)
        )
        return len(jsonfiles)

    def is_bot_running(self, pair) -> bool:
        """Check is bot running (pair.json file exists)"""
        self.logger.debug("METHOD(is_bot_running) - DATA(%s)", pair)
        if os.path.isfile(
            os.path.join(self.datafolder, "telegram_data", f"{pair}.json")
        ):
            return True

        return False

    def get_running_bot_exchange(self, pair) -> str:
        """Get bots exchange"""
        self.logger.debug("METHOD(get_running_bot_exchange) - DATA(%s)", pair)
        if self.read_data(f"{pair}.json") is True:
            return self.data["exchange"]
        return "None"

    def start_process(
        self,
        pair,
        exchange,
        overrides,
        startmethod: str = "telegram",
        return_output: bool = False,
    ):
        """Start a new subprocess"""
        self.logger.debug(
            "METHOD(start_process) - DATA(%s, %s, %s, %s)",
            pair,
            exchange,
            overrides,
            startmethod,
        )
        if self.is_bot_running(pair):
            return False

        if return_output is True:
            return subprocess.getoutput(
                f"python3 pycryptobot.py --exchange {exchange} --market {pair} {overrides}"
            )

        command = "python3 pycryptobot.py"
        command = f"{command} --startmethod {startmethod}"

        if pair != "":
            command = f"{command} --market {pair}"
        if exchange != "":
            command = f"{command} --exchange {exchange}"

        if platform.system() == "Windows":
            os.system(
                f"start powershell -Command $host.UI.RawUI.WindowTitle = '{pair}' ; "
                f"{command} --logfile './logs/{exchange}-{pair}-{datetime.now().date()}.log' "
                f"{overrides}"
            )
        else:
            if self.terminal_start_process != "":
                command = f"{self.terminal_start_process.replace('{pair}', pair)} {command}"
            subprocess.Popen(
                f"{command} --logfile './logs/{exchange}-{pair}-{datetime.now().date()}.log' "
                f"{overrides}",
                shell=True,
            )

        return True

    def update_bot_control(self, pair, status) -> bool:
        """used to update bot json files for controlling state"""
        self.logger.debug("METHOD(update_bot_control) - DATA(%s, %s)", pair, status)
        read_ok = self.read_data(pair)
        if not read_ok:
            self.logger.warning("update_bot_control for %s unable to read file", pair)
        elif "botcontrol" in self.data:
            self.data["botcontrol"]["status"] = status
            self.write_data(pair)
            return True

        return False

    def stop_running_bot(self, pair, state, is_open: bool = False) -> bool:
        """Stop current running bots"""
        self.logger.debug("METHOD(stop_running_bot) - DATA(%s, %s)", pair, state)
        if self.is_bot_running(pair):
            read_ok = self.read_data(pair)
            if not read_ok:
                self.logger.warning("stop_running_bot for %s unable to read file", pair)
            if is_open:
                return self.update_bot_control(pair, state)
            elif "margin" in self.data and self.data["margin"] == " ":
                return self.update_bot_control(pair, state)

    def create_callback_data(
        self, callback_tag, exchange: str = "", parameter: str = ""
    ):
        return json.dumps({"c": callback_tag, "e": exchange, "p": parameter})

    def clean_data_folder(self):
        """ check market files in data folder """
        self.logger.debug("cleandata started")
        jsonfiles = self.get_active_bot_list()
        for i in range(len(jsonfiles), 0, -1):
            jfile = jsonfiles[i - 1]

            self.logger.info("checking %s", jfile)

            self.read_data(jfile)

            last_modified = datetime.now() - datetime.fromtimestamp(
                os.path.getmtime(
                    os.path.join(
                        self.datafolder, "telegram_data", f"{jfile}.json"
                    )
                )
            )
            if "margin" not in self.data:
                self.logger.info("deleting %s", jfile)
                os.remove(
                    os.path.join(
                        self.datafolder, "telegram_data", f"{jfile}.json"
                    )
                )
                continue
            if (
                self.data["botcontrol"]["status"] == "active"
                and last_modified.seconds > 120
                and (last_modified.seconds != 86399 and last_modified.days != -1)
            ):
                self.logger.info("deleting %s %s", jfile, str(last_modified))
                os.remove(
                    os.path.join(
                        self.datafolder, "telegram_data", f"{jfile}.json"
                    )
                )
                continue
            elif (
                self.data["botcontrol"]["status"] == "exit"
                and last_modified.seconds > 120
                and last_modified.seconds != 86399
            ):
                self.logger.info(
                    "deleting %s %s", jfile, str(last_modified.seconds)
                )
                os.remove(
                    os.path.join(
                        self.datafolder, "telegram_data", f"{jfile}.json"
                    )
                )
        self.logger.debug("cleandata complete")
