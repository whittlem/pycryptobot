import os
import json
from re import S
from models.PyCryptoBot import PyCryptoBot


class TelegramBotHelper:

    def __init__(self, app: PyCryptoBot) -> None:
        self.app = app
        self.market = app.getMarket()
        self.exchange = app.getExchange()
        self.botfolder = "telegram_data"
        self.botpath = os.path.join(os.path.curdir, self.botfolder, self.market)

        if not os.path.exists(self.botfolder):
            os.makedirs(self.botfolder)

        self.data = {}

        if not os.path.exists(os.path.join(os.curdir, "telegram_data")):
            os.mkdir(os.path.join(os.curdir, "telegram_data"))

        if os.path.isfile(os.path.join(os.curdir, "telegram_data", "data.json")):
            self.data = self._read_data()
        else:
            ds = {"margins" : {}, "trades" : {}, "sell" : {}}
            self.data = ds
            self._write_data()

    def _read_data(self) -> None:
        with open(os.path.join(os.curdir, 'telegram_data', 'data.json'), 'r') as json_file:
            self.data = json.load(json_file)

    def _write_data(self) -> None:
        with open(os.path.join(os.curdir, 'telegram_data', 'data.json'), 'w') as outfile:
            json.dump(self.data, outfile, indent=4)

    def addmargin(self, margin: str = "", delta: str = ""):

        marketFound = False
        self._read_data()

        for m in self.data['margins']:
            if m == self.market:
                marketFound = True
                self.data["margins"][self.market]["margin"] = margin
                self.data["margins"][self.market]["delta"] = delta

        if not marketFound:
            addmarket = {self.market : {'exchange' : self.exchange, 'margin' : margin, 'delta' : delta}}
            self.data['margins'].update(addmarket)

        self._write_data()

    def deletemargin(self):
        self._read_data()

        self.data["margins"].pop(self.market)

        self._write_data()

    def closetrade(self, ts, price, margin):

        self._read_data

        self.data['trades'].update({self.market : {"timestamp" : ts, "price" : price, "margin" : margin}})

        self._write_data

    def checkmanualsell(self) -> bool:

        self._read_data()

        result = False
        for s in self.data:
            if s == "sell":
                for ps in self.data["sell"]:
                    if ps == self.market:
                        result = self.data["sell"][self.market]
                        break
        
        if result:
            self.data["sell"].pop(self.market)


        self._write_data()

        return result

