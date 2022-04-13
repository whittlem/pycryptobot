from json.decoder import JSONDecodeError
import os
import json
from time import sleep
from datetime import datetime

from pandas.core.frame import DataFrame
from models.PyCryptoBot import PyCryptoBot
from models.helper.LogHelper import Logger


class TelegramBotHelper:
    """ Telegram Bot data helper """
    def __init__(self, app: PyCryptoBot, scanner: bool = False) -> None:
        self.app = app
        self.market = app.getMarket()
        self.exchange = app.getExchange()
        self.botfolder = "telegram_data"
        self.botpath = os.path.join(
            self.app.telegramdatafolder, self.botfolder, self.market
        )
        self.filename = self.market + ".json"

        if not self.app.isSimulation() and self.app.enableTelegramBotControl() and not scanner:
            if not os.path.exists(self.botfolder):
                os.makedirs(self.botfolder)

            self.data = {}

            if not os.path.exists(
                os.path.join(self.app.telegramdatafolder, "telegram_data")
            ):
                os.mkdir(os.path.join(self.app.telegramdatafolder, "telegram_data"))

            if os.path.isfile(
                os.path.join(
                    self.app.telegramdatafolder, "telegram_data", self.filename
                )
            ):
                if not self._read_data():
                    self.create_bot_data()
            else:
                self.create_bot_data()

            if os.path.isfile(
                os.path.join(self.app.telegramdatafolder, "telegram_data", "data.json")
            ):

                write_ok, try_count = False, 0
                while not write_ok and try_count <= 5:
                    try_count += 1
                    self._read_data("data.json")
                    write_ok = True
                    if "markets" not in self.data:
                        self.data.update({"markets": {}})
                        write_ok = self._write_data("data.json")
                    if "scannerexceptions" not in self.data:
                        self.data.update({"scannerexceptions": {}})
                        write_ok = self._write_data("data.json")
                    if "opentrades" not in self.data:
                        self.data.update({"opentrades": {}})
                        write_ok = self._write_data("data.json")
            else:
                write_ok, try_count = False, 0
                while not write_ok and try_count <= 5:
                    try_count += 1
                    ds = {"trades": {}, "markets": {}, "scannerexceptions": {}, "opentrades": {}}
                    self.data = ds
                    write_ok = self._write_data("data.json")

    def create_bot_data(self):
        """ Create pair.json file """
        ds = {
                "botcontrol": {
                    "status": "active",
                    "manualsell": False,
                    "manualbuy": False,
                    "started": datetime.now().isoformat(),
                    "startmethod" : self.app.startmethod,
                },
                "preventlosstriggered" : False,
                "exchange" : self.exchange.value,
                "margin": "",
                "delta": "",
                "price": 0.0,
                "df_high": " ",
                "from_df_high": " ",
                "trailingstoplosstriggered" : False,
                "change_pcnt_high" : 0.0
            }
        self.data = ds
        self._write_data()

    def _read_data(self, name: str = "") -> bool:
        file = self.filename if name == "" else name

        read_ok, try_count = False, 0
        while not read_ok and try_count <= 5:
            try_count += 1
            try:
                with open(
                    os.path.join(self.app.telegramdatafolder, "telegram_data", file),
                    "r",
                    encoding="utf8",
                ) as json_file:
                    self.data = json.load(json_file)
                read_ok = True
            except FileNotFoundError:
                Logger.warning("File Not Found:  Recreating File..")
                self.create_bot_data()
            except JSONDecodeError:
                if len(self.data) > 0:
                    Logger.warning("JSON Decode Error: Recreating File..")
                    if name == "":
                        self._write_data()
                else:
                    Logger.warning("JSON Decode Error: Removing File..")
                    if name == "":
                        self.removeactivebot()
        return read_ok

    def _write_data(self, name: str = "") -> bool:
        file = self.filename if name == "" else name
        try:
            with open(
                os.path.join(self.app.telegramdatafolder, "telegram_data", file),
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.data, outfile, indent=4)
            return True
        except JSONDecodeError as err:
            Logger.critical(str(err))
            return False

    def addmargin(self, margin: str = "", delta: str = "", price: str = "", change_pcnt_high: float = 0.0, signal = "WAIT"):
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            if self._read_data():
                addmarket = {
                    "exchange": self.exchange.value,
                    "signal": signal,
                    "margin": margin,
                    "delta": delta,
                    "price": price,
                    "df_high": " ",
                    "from_df_high": " ",
                    "trailingstoplosstriggered" : float(margin.replace("%", "")) > self.app.trailingStopLossTrigger() if "trailingstoplosstriggered" in self.data and self.data['trailingstoplosstriggered'] == False else True,
                    "change_pcnt_high" : change_pcnt_high if "trailingstoplosstriggered" in self.data and self.data['trailingstoplosstriggered'] == True else 0.0,
                    # "change_pcnt_low" : change_pcnt_high if "preventlosstriggered" in self.data and self.data['preventlosstriggered'] == True else 0.0
                }
                
                if self.app.preventLoss():
                    self.data.update({"preventlosstriggered" : float(margin.replace("%", "")) > self.app.preventLossTrigger() if "preventlosstriggered" in self.data and self.data['preventlosstriggered'] == False else True})

                self.data.update(addmarket)
                self._write_data()

    def updatewatchdogping(self):
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            if self._read_data() and "botcontrol" in self.data:
                self.data["botcontrol"]["watchdog_ping"] =  datetime.now().isoformat()
                self._write_data()
    
    def addinfo(
        self,
        message: str = "",
        price: str = "",
        df_high: str = "",
        from_df_high: str = "",
        signal ="WAIT"
    ) -> None:
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            if self._read_data():
                addmarket = {
                    "signal": signal,
                    "message": message,
                    "margin": " ",
                    "delta": " ",
                    "price": price,
                    "exchange": self.exchange.value,
                    "df_high": df_high,
                    "from_df_high": from_df_high,
                }
                self.data.update(addmarket)
                self._write_data()

    def addindicators(self, indicator, state) -> None:
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            if self._read_data():
                if not "indicators" in self.data:
                    self.data.update({"indicators": {}})

                self.data["indicators"].update({indicator: state})
                self._write_data()

    def deletemargin(self):
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            try:
                os.remove(
                    os.path.join(
                        self.app.telegramdatafolder, "telegram_data", self.filename
                    )
                )
            except FileNotFoundError:
                pass

    def closetrade(self, ts, price, margin):
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            write_ok, try_count = False, 0
            while not write_ok and try_count <= 5:
                try_count += 1
                self._read_data("data.json")
                self.data["trades"].update(
                    {ts: {"pair": self.market, "price": price, "margin": margin}}
                )
                write_ok = self._write_data("data.json")
                if not write_ok:
                    sleep(1)
                    continue
                self.remove_open_order()

    def checkmanualbuysell(self) -> str:
        result = "WAIT"

        if self._read_data() and "botcontrol" in self.data:
            if len(self.data["botcontrol"]) > 0:
                if self.data["botcontrol"]["manualsell"]:
                    self.data["botcontrol"]["manualsell"] = False
                    result = "SELL"
                    self._write_data()

            if len(self.data["botcontrol"]) > 0:
                if self.data["botcontrol"]["manualbuy"]:
                    self.data["botcontrol"]["manualbuy"] = False
                    result = "BUY"
                    self._write_data()

        return result

    def checkbotcontrolstatus(self) -> str:
        result = "active"
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            if self._read_data() and "botcontrol" in self.data:
                result = self.data["botcontrol"]["status"]

        return result

    def updatebotstatus(self, status) -> None:
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            if self._read_data() and "botcontrol" in self.data:
                if not self.data["botcontrol"]["status"] == status:
                    self.data["botcontrol"]["status"] = status
                    self._write_data()

    def removeactivebot(self) -> None:
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            self.deletemargin()

    def save_scanner_output(self, exchange, quote, output: DataFrame) -> None:
        try:
            os.remove(
                    os.path.join(
                        self.app.telegramdatafolder, "telegram_data", f"{exchange}_{quote}_output.json"
                    )
                )
        except FileNotFoundError:
            pass

        sort_columns = []
        ascend = []
        if self.app.enable_buy_next:
            sort_columns.append("buy_next")
            ascend.append(False)
        if self.app.enable_atr72_pcnt:
            sort_columns.append("atr72_pcnt")
            ascend.append(False)
        if self.app.enable_volume:
            sort_columns.append("volume")
            ascend.append(False)

        output = output.sort_values(by=sort_columns, ascending=ascend, inplace=False)

        output.to_json(
            os.path.join(
                self.app.telegramdatafolder,
                "telegram_data",
                f"{exchange}_{quote}_output.json",
            ),
            orient="index",
        )

    def add_open_order(self):
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            write_ok, try_count = False, 0
            while not write_ok and try_count <= 5:
                try_count += 1
                self._read_data("data.json")
                if self.market in self.data["opentrades"]:
                    if self.exchange != self.data["opentrades"][self.market]:
                        return
                self.data["opentrades"].update({self.market : {"exchange": self.exchange.value}})
                write_ok = self._write_data("data.json")
                if not write_ok:
                    sleep(1)

    def remove_open_order(self):
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            write_ok, try_count = False, 0
            while not write_ok and try_count <= 5:
                try_count += 1
                self._read_data("data.json")

                if self.market not in self.data["opentrades"]:
                    return

                self.data["opentrades"].pop(self.market)
                write_ok = self._write_data("data.json")
                if not write_ok:
                    sleep(1)

