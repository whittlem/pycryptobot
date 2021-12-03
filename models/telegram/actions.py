import os
import json
import subprocess
import logging
from datetime import datetime

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
        query = update.callback_query
        query.edit_message_text(
                "<b>Starting markets with open trades..</b>",
                parse_mode="HTML")
        helper.read_data()
        # startbotinfo
        for market in helper.data["opentrades"]:
            if not helper.isBotRunning(market):
                # update.effective_message.reply_html(f"<i>Starting {market} crypto bot</i>")
                helper.startProcess(market, helper.data["opentrades"][market]["exchange"], "", "scanner")
            sleep(10)
        update.effective_message.reply_html(f"<i>Markets have been started</i>")
        self.getBotInfo(update)

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

    def _getUptime(self, date: str):
        now = str(datetime.now())
        # If date passed from datetime.now() remove milliseconds
        if date.find(".") != -1:
            dt = date.split(".")[0]
            date = dt
        if now.find(".") != -1:
            dt = now.split(".", maxsplit=1)[0]
            now = dt

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

    def getBotInfo(self, update):
        query = update.callback_query
        try:
            query.answer()
        except:
            pass
        count = 0
        for file in helper.getActiveBotList():
            output = ""
            count += 1
            helper.read_data(file)

            output = output + f"\U0001F4C8 <b>{file}</b> "

            last_modified = datetime.now() - datetime.fromtimestamp(
                os.path.getmtime(
                    os.path.join(self.datafolder, "telegram_data", f"{file}.json")
                )
            )

            icon = "\U0001F6D1" # red dot
            if last_modified.seconds > 90 and last_modified.seconds != 86399:
                output = f"{output} {icon} <b>Status</b>: <i>defaulted</i>"
            elif "botcontrol" in helper.data and "status" in helper.data["botcontrol"]:
                if helper.data["botcontrol"]["status"] == "active":
                    icon = "\U00002705" # green tick
                if helper.data["botcontrol"]["status"] == "paused":
                    icon = "\U000023F8" # pause icon
                if helper.data["botcontrol"]["status"] == "exit":
                    icon = "\U0000274C" # stop icon
                output = f"{output} {icon} <b>Status</b>: <i>{helper.data['botcontrol']['status']}</i>"
                output = f"{output} \u23F1 <b>Uptime</b>: <i>{self._getUptime(helper.data['botcontrol']['started'])}</i>\n"
            else:
                output = f"{output} {icon} <b>Status</b>: <i>stopped</i> "

            if count == 1:
                try:
                    query.edit_message_text(f"{output}", parse_mode="HTML")
                except:
                    update.effective_message.reply_html(f"{output}")
            else:
                update.effective_message.reply_html(f"{output}")
            sleep(0.2)

        update.effective_message.reply_html(f"<b>Bot Count ({count})</b>")

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
                helper.stopRunningBot(file, "exit")
                sleep(5)

        botcounter = len(helper.getActiveBotList())
        helper.read_data()
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