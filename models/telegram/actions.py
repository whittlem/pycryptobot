import os
import json
import subprocess
import logging

from time import sleep
from models.telegram.helper import TelegramHelper

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

helper = None

class TelegramActions():
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder

        global helper ; helper = tg_helper

    def startOpenOrders(self, update):
        logger.info("called startOpenOrders")
        helper.read_data()
        for market in helper.data["opentrades"]:
            if not helper.isBotRunning(market):
                update.effective_message.reply_html(f"<i>Starting {market} crypto bot</i>")
                helper.startProcess(market, helper.data["opentrades"][market]["exchange"], "", "scanner")
            sleep(10)

    def sellresponse(self, update):
        """create the manual sell order"""
        query = update.callback_query
        logger.info("called sellresponse - %s", query.data)
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
        logger.info("called buyresponse - %s", query.data)
        helper.read_data(query.data.replace("confirm_buy_", ""))
        if "botcontrol" in helper.data:
            helper.data["botcontrol"]["manualbuy"] = True
            # helper.write_data(query.data.replace("sell_", ""))
            query.edit_message_text(
                f"Buying: {query.data.replace('confirm_buy_', '').replace('.json','')}\n<i>Please wait for sale notification...</i>",
                parse_mode="HTML",
            )

    def showconfigresponse(self, update):
        """display config settings based on exchanged selected"""
        with open(os.path.join(helper.config_file), "r", encoding="utf8") as json_file:
            self.config = json.load(json_file)

        query = update.callback_query
        logger.info("called showconfigresponse - %s", query.data)

        if query.data == "ex_scanner":
            pbot = self.config[query.data.replace("ex_", "")]
        else:
            pbot = self.config[query.data.replace("ex_", "")]["config"]

        query.edit_message_text(query.data.replace("ex_", "") + "\n" + json.dumps(pbot, indent=4))

    def StartMarketScan(self, update, debug: bool = False, scanmarkets: bool = True):
        logger.info("called StartMarketScan")
        try:
            with open("scanner.json") as json_file:
                config = json.load(json_file)
        except IOError as err:
            update.message.reply_text(
                f"<i>scanner.json config error</i>\n{err}", parse_mode="HTML"
            )
            return

        if debug == False:
            if scanmarkets:
                update.effective_message.reply_html(
                    f"<i>Gathering market data\nThis can take some time depending on number of pairs\nplease wait...</i> \u23F3")
                try:
                    logger.info("Starting Market Scanner")
                    output = subprocess.getoutput("python3 scanner.py")
                except Exception as err:
                    update.effective_message.reply_html("<b>scanning failed.</b>")
                    logger.error(err)
                    raise
            update.effective_message.reply_html("<b>scan complete, stopping bots..</b>")
            for file in helper.getActiveBotList():
                helper.stopRunningBot(file)
                sleep(5)

        helper.read_data()
        botcounter = 0
        for ex in config:
            if helper.config["scanner"]["maxbotcount"] > 0 and botcounter >= helper.config["scanner"]["maxbotcount"]:
                break
            for quote in config[ex]["quote_currency"]:
                update.effective_message.reply_html(f"Starting {ex} ({quote}) bots...")
                logger.info("%s - (%s)", ex, quote)
                with open(
                    os.path.join(
                        self.datafolder, "telegram_data", f"{ex}_{quote}_output.json"
                        ), "r", encoding="utf8") as json_file:
                    data = json.load(json_file)

                outputmsg =  f"<b>{ex} ({quote})</b> \u23F3 \n"

                for row in data:
                    if debug:
                        logger.info("%s", row)

                    if helper.config["scanner"]["maxbotcount"] > 0 and botcounter >= helper.config["scanner"]["maxbotcount"]:
                        break
                    
                    if helper.config["scanner"]["enableleverage"] == False \
                            and (str(row).__contains__("DOWN") or str(row).__contains__("UP")):
                        continue

                    if row in helper.data["scannerexceptions"]:
                        outputmsg = outputmsg + f"*** {row} found on scanner exception list ***\n"
                    else:
                        if data[row]["atr72_pcnt"] != None:
                            if data[row]["atr72_pcnt"] >= helper.config["scanner"]["atr72_pcnt"]:
                                if helper.config["scanner"]["enable_buy_next"] and data[row]["buy_next"]:
                                    outputmsg = outputmsg + f"<i><b>{row}</b>  //--//  <b>atr72_pcnt:</b> {data[row]['atr72_pcnt']}%  //--//  <b>buy_next:</b> {data[row]['buy_next']}</i>\n"
                                    helper.startProcess(row, ex, "", "scanner")
                                    botcounter += 1
                                elif not helper.config["scanner"]["enable_buy_next"]:
                                    outputmsg = outputmsg + f"<i><b>{row}</b>  //--//  <b>atr72_pcnt:</b> {data[row]['atr72_pcnt']}%</i>\n"
                                    helper.startProcess(row, ex, "", "scanner")
                                    botcounter += 1
                                if debug == False:
                                    sleep(10)

                update.effective_message.reply_html(f"{outputmsg}")

        update.effective_message.reply_html(f"<i>Operation Complete.  ({botcounter} started)</i>")

    def deleteresponse(self, update):
        """delete selected bot"""
        helper.read_data()

        query = update.callback_query
        logger.info("called deleteresponse - %s", query.data)
        helper.data["markets"].pop(str(query.data).replace("delete_", ""))

        helper.write_data()

        query.edit_message_text(
            f"<i>Deleted {str(query.data).replace('delete_', '')} crypto bot</i>",
            parse_mode="HTML",
        )