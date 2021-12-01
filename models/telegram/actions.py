import os
import json
from time import sleep
from models.telegram.helper import TelegramHelper

helper = None

class TelegramActions():
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder

        global helper ; helper = tg_helper

    def startOpenOrders(self, update):
        helper.read_data()
        for market in helper.data["opentrades"]:
            if not helper.isBotRunning(market):
                update.effective_message.reply_html(f"<i>Starting {market} crypto bot</i>")
                helper.startProcess(market, helper.data["opentrades"][market]["exchange"], "", "scanner")
            sleep(10)

    def sellresponse(self, update):
        """create the manual sell order"""
        query = update.callback_query

        helper.read_data(query.data.replace("sell_", ""))
        if "botcontrol" in helper.data:
            helper.data["botcontrol"]["manualsell"] = True
            # helper.write_data(query.data.replace("sell_", ""))
            query.edit_message_text(
                f"Selling: {query.data.replace('sell_', '').replace('.json','')}\n<i>Please wait for sale notification...</i>",
                parse_mode="HTML",
            )

    def buyresponse(self, update):
        """create the manual buy order"""
        query = update.callback_query

        helper.read_data(query.data.replace("buy_", ""))
        if "botcontrol" in helper.data:
            helper.data["botcontrol"]["manualbuy"] = True
            # helper.write_data(query.data.replace("sell_", ""))
            query.edit_message_text(
                f"Buying: {query.data.replace('buy_', '').replace('.json','')}\n<i>Please wait for sale notification...</i>",
                parse_mode="HTML",
            )

    def showconfigresponse(self, update):
        """display config settings based on exchanged selected"""
        with open(os.path.join(helper.config_file), "r", encoding="utf8") as json_file:
            self.config = json.load(json_file)

        query = update.callback_query

        if query.data == "ex_scanner":
            pbot = self.config[query.data.replace("ex_", "")]
        else:
            pbot = self.config[query.data.replace("ex_", "")]["config"]

        query.edit_message_text(query.data.replace("ex_", "") + "\n" + json.dumps(pbot, indent=4))