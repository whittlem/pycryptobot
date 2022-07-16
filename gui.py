""" Pycrypto GUI """
import json
import os
import argparse

from time import sleep
from guizero import App, Text, TextBox, MenuBar, info

### Setting initial values for color variables ###
bgvalue = ""
txvalue = ''
posvalue = ''
txtbox_pos = "#38BC38"
txtbox_neg = "#BC3838"
### Menu bar for display options###

def about():
        self.info("info",        "Pycryptobot GUI by              Mark H. & Jared S.")
def main_bg():
        bgvalue = self.question("Background", "Enter Hex Color Value.")
        if bgvalue is not None:
            self.bg = bgvalue

def text_clr():
        txvalue = self.question("Text", "Enter Hex Color Value.")
        if txvalue is not None:
            self.text_color = txvalue
### this feature not working at this time
##def pos_clr():
##        posvalue = self.question("Text", "Enter Hex Color Value.")
##        if txvalue is not None:
##            txtbox.bg = posvalue
##        print("Positive Color")
##
##def neg_clr():
##        print("Negative Color")
##
### updates via telegram_data/data.json for the selected trading pair,

class GuiSetup:
    def __init__(self) -> None:
        self.datafolder = ""

        parser = argparse.ArgumentParser(description="PyCryptoBot Telegram Bot")
        parser.add_argument(
            "--config",
            type=str,
            dest="config_file",
            help="pycryptobot config file",
            default="config.json",
        )
        parser.add_argument(
            "--datafolder",
            type=str,
            help="Use the datafolder at the given location, useful for multi bots running in different folders",
            default="",
        )

        args = parser.parse_args()

        self.config_file = args.config_file

        with open(os.path.join(self.config_file), "r", encoding="utf8") as json_file:
            self.config = json.load(json_file)

        if "datafolder" in self.config["telegram"]:
            self.datafolder = self.config["telegram"]["datafolder"]

        if not args.datafolder == "":
            self.datafolder = args.datafolder
### json reading  ###
    def read_file(self, file):
        read = False
        while read is False:
            try:
                with open(
                    os.path.join(self.datafolder, "telegram_data", file),
                    "r",
                    encoding="utf8",
                ) as message:
                    data = json.load(message)
                    read = True
            except:
                read = False

        return data
### Reads data.json and adds the correct amount of display boxes ###
    def add_pairs(self):

        jsonfiles = os.listdir(os.path.join(self.datafolder, "telegram_data"))
        while len(jsonfiles) <= 1:
            sleep(300)
        row = 2
        for file in jsonfiles:
            if not "data.json" in file:
                data = self.read_file(file)

                tpair = TextBox(app, grid=[0, row], width=15, align="top")
                exchange = TextBox(app, grid=[1, row], width=15)
                lastaction = TextBox(app, grid=[2, row], width=15)
                curprice = TextBox(app, grid=[3, row], width=15)
                margin = TextBox(app, grid=[4, row], width=15)
                delta = TextBox(app, grid=[5, row], width=15)
                ERI = TextBox(app, grid=[6, row])
                BULL = TextBox(app, grid=[7, row])
                EMA = TextBox(app, grid=[8, row])
                MACD = TextBox(app, grid=[9, row])
                OBV = TextBox(app, grid=[10, row])

                tpair.value = file.replace(".json", "")
                exchange.value = data["exchange"] if "exchange" in data else "waiting to buy"

                margin.repeat(5100, self.update_textbox, args=[margin, file, "margin"])
                delta.repeat(5100, self.update_textbox, args=[delta, file, "delta"])
                curprice.repeat(5100, self.update_textbox, args=[curprice, file, "price"])
                lastaction.repeat(5100, self.update_lastaction, args=[lastaction, file])
                ERI.repeat(5100, self.update_indicator, args=[ERI, file, "ERI"])
                BULL.repeat(5100, self.update_indicator, args=[BULL, file, "BULL"])
                EMA.repeat(5100, self.update_indicator, args=[EMA, file, "EMA"])
                MACD.repeat(5100, self.update_indicator, args=[MACD, file, "MACD"])
                OBV.repeat(5100, self.update_indicator, args=[OBV, file, "EMA"])

                row += 1
### updates the margin and delta boxes ###

    def update_textbox(self, txtbox, file, key) -> None:
        data = self.read_file(file)

        last_price = txtbox.value if txtbox.value != "" else data[key]

        txtbox.value = data[key] if not data[key] == " " else "N/A"
### this line causes the self.price tickers to flash instead of stay a constant state   ###
### originally added to turn the margin and delta boxes back to an inactive state after a sale ###
        txtbox.bg = self.bg

        if key in ("margin", "delta") and txtbox.value != "N/A":
            txtbox.bg = (
                "#38BC38" if float(txtbox.value.replace("%", "")) > 0 else "#BC3838"
            )

### Tickers change state with self.price change ###
        if key == "price":
            if float(last_price) < float(txtbox.value):
                txtbox.bg = "#38BC38"
            elif float(last_price) > float(txtbox.value):
                txtbox.bg = "#BC3838"
### Changes indicator background states ###
    def update_indicator(self, txtbox, file, key) -> None:
        data = self.read_file(file)
        txtbox.value = data["indicators"][key] if key in data["indicators"] else False
        txtbox.bg = "#38BC38" if txtbox.value == "True" else "#BC3838"
### Changes last action text and background states ###
    def update_lastaction(self, txtbox, file) -> None:
        data = self.read_file(file)
        txtbox.value = "BUY" if not data["margin"] == " " else "SELL"
        txtbox.bg =  "#38BC38" if not data["margin"] == " " else self.bg


### Size, Color, and Title can be modified here ###

app = App(layout="grid", height=730, width=1320)
app.title = "Pycryptobot SimpleGUI V0.2"
app.bg = "black"
app.text_color = "white"

### menu bar ###
menu = MenuBar(app,
               toplevel=["Display Options"],
               options=[
                   [["Background Color", main_bg],["Text Color", text_clr], ["About", about]]
                   ])
###labels for the top of the display###
tpair_label = Text(app, text=" Trading Pair", grid=[0, 1])
exchange_label = Text(app, text="Exchange", grid=[1, 1])
action_label = Text(app, text="Last Action", grid=[2, 1])
curprice = Text(app, text="Current self.price", grid=[3, 1])
margin_label = Text(app, text="Margin", grid=[4, 1])
profit_label = Text(app, text="Delta", grid=[5, 1])
ERI_label = Text(app, text="ERI", grid=[6, 1])
BULL_label = Text(app, text="BULL", grid=[7, 1])
EMA_label = Text(app, text="EMA", grid=[8, 1])
MACD_label = Text(app, text="MACD", grid=[9, 1])
OBV_label = Text(app, text="OBV", grid=[10, 1])

###making boxes for the display###

GuiSetup().add_pairs()

app.display()
