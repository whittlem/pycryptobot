from json.decoder import JSONDecodeError
import os
import json
from datetime import datetime

from pandas.core.frame import DataFrame
from models.PyCryptoBot import PyCryptoBot
from models.helper.LogHelper import Logger


class TelegramBotHelper:
    def __init__(self, app: PyCryptoBot) -> None:
        self.app = app
        self.market = app.getMarket()
        self.exchange = app.getExchange()
        self.botfolder = "telegram_data"
        self.botpath = os.path.join(self.app.telegramdatafolder, self.botfolder, self.market)
        self.filename = self.market + ".json"

        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            if not os.path.exists(self.botfolder):
                os.makedirs(self.botfolder)

            self.data = {}

            if not os.path.exists(os.path.join(self.app.telegramdatafolder, "telegram_data")):
                os.mkdir(os.path.join(self.app.telegramdatafolder, "telegram_data"))

            if os.path.isfile(os.path.join(self.app.telegramdatafolder, "telegram_data", self.filename)):
                self._read_data()
            else:
                ds = {'botcontrol' : {"status":"active", "manualsell" : False, "manualbuy" : False, "started": datetime.now().isoformat()}}
                self.data = ds
                self._write_data()

            if os.path.isfile(os.path.join(self.app.telegramdatafolder, "telegram_data", "data.json")):
                self._read_data("data.json")
                if not "markets" in self.data:
                    self.data.update({"markets": {}})
                    self._write_data("data.json")
            else:
                ds = {"trades" : {}, "markets": {}}
                self.data = ds
                self._write_data("data.json")

    def _read_data(self, name: str = "") -> None:
        file = self.filename if name =="" else name
        with open(os.path.join(self.app.telegramdatafolder, 'telegram_data', file), 'r', encoding='utf8') as json_file:
            self.data = json.load(json_file)

    def _write_data(self, name: str = "") -> None:
        file = self.filename if name =="" else name
        try:
            with open(os.path.join(self.app.telegramdatafolder, 'telegram_data', file), 'w', encoding='utf8') as outfile:
                json.dump(self.data, outfile, indent=4)
        except (JSONDecodeError, Exception) as err:
            Logger.critical(str(err))
            with open(os.path.join(self.app.telegramdatafolder, 'telegram_data', file), 'w', encoding='utf8') as outfile:
                json.dump(self.data, outfile, indent=4)
        
    def addmargin(self, margin: str = "", delta: str = "", price: str = ""):
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            self._read_data()

            addmarket = {'exchange' : self.exchange, 'margin' : margin, 'delta' : delta, 'price' : price, "df_high": " ", "from_df_high": " "}
            self.data.update(addmarket)
            self._write_data()

    def addinfo(self, message: str = "", price: str = "", df_high: str="", from_df_high: str="") -> None:
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            self._read_data()
            addmarket = {"message": message, "margin": " ", "delta": " ", "price" : price, "exchange" : self.exchange, "df_high": df_high, "from_df_high": from_df_high}
            self.data.update(addmarket)
            self._write_data()

    def addindicators(self, indicator, state) -> None:
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            self._read_data()
            if not 'indicators' in self.data:
                self.data.update({"indicators": {}})

            self.data['indicators'].update({indicator : state})
            self._write_data()

    def deletemargin(self):
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            os.remove(os.path.join(self.app.telegramdatafolder, 'telegram_data', self.filename))

    def closetrade(self, ts, price, margin):
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            self._read_data("data.json")
            self.data['trades'].update({ts : {"pair" : self.market, "price" : price, "margin" : margin}})
            self._write_data("data.json")

    def checkmanualbuysell(self) -> str:
        result = "WAIT"
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            self._read_data()

            if len(self.data['botcontrol']) > 0:
                if self.data["botcontrol"]["manualsell"]:
                    self.data["botcontrol"]["manualsell"] = False
                    result = "SELL"
                    self._write_data()

            if len(self.data['botcontrol']) > 0:
                if self.data["botcontrol"]["manualbuy"]:
                    self.data["botcontrol"]["manualbuy"] = False
                    result = "BUY"
                    self._write_data()

        return result

    def checkbotcontrolstatus(self) -> str:
        result = "active"
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            self._read_data()
            result = self.data["botcontrol"]["status"]
            
        return result

    def updatebotstatus(self, status) -> None:
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            self._read_data()
            if not self.data["botcontrol"]["status"] == status:
                self.data["botcontrol"]["status"] = status
                self._write_data()

    def removeactivebot(self) -> None:
        if not self.app.isSimulation() and self.app.enableTelegramBotControl():
            self.deletemargin()

    def save_scanner_output(self, exchange, quote, output: DataFrame) -> None:

        output.to_json(os.path.join(self.app.telegramdatafolder, "telegram_data", f"{exchange}_{quote}_output.json"), orient='index')
