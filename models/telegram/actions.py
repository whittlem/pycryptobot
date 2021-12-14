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

class TelegramActions():
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder

        self.helper = tg_helper

    def _getMarginText(self, market):
        light_icon, margin_icon = ("\U0001F7E2" if "-" not in self.helper.data["margin"] else "\U0001F534", "\U0001F973" if "-" not in self.helper.data["margin"] else "\U0001F97A")
        # result = f"\U0001F4C8 <b>{market}</b> {margin_icon}  <i>Current Margin: {self.helper.data['margin']} \U0001F4B0 (P/L): {self.helper.data['delta']}\n" \
        # f"\U0001F4B0 (P/L): {self.helper.data['delta']}\n(TSL Trg): {self.helper.data['trailingstoplosstriggered']}  --  (TSL Change): {self.helper.data['change_pcnt_high']}</i>\n"
        result = f"{light_icon} <b>{market}</b>\n" \
                    f"{margin_icon} Margin: {self.helper.data['margin']}  " \
                    f"\U0001F4B0 P/L: {self.helper.data['delta']}\n" \
                    f"TSL Trg: {self.helper.data['trailingstoplosstriggered']}\n" \
                    f"TSL Change: {float(self.helper.data['change_pcnt_high']).__round__(4)}\n"
        return result

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

    def startOpenOrders(self, update):
        logger.info("called startOpenOrders")
        query = update.callback_query
        if query != None:
            query.answer()
            query.edit_message_text(
                "<b>Starting markets with open trades..</b>",
                parse_mode="HTML")
        else:
            update.effective_message.reply_html("<b>Starting markets with open trades..</b>")

        self.helper.read_data()
        for market in self.helper.data["opentrades"]:
            if not self.helper.isBotRunning(market):
                # update.effective_message.reply_html(f"<i>Starting {market} crypto bot</i>")
                self.helper.startProcess(market, self.helper.data["opentrades"][market]["exchange"], "", "scanner")
            sleep(10)
        update.effective_message.reply_html("<i>Markets have been started</i>")
        sleep(1)
        self.getBotInfo(update)

    def sellresponse(self, update):
        """create the manual sell order"""
        query = update.callback_query
        logger.info("called sellresponse - %s", query.data)
        while self.helper.read_data(query.data.replace("confirm_sell_", "")) == False:
            sleep(0.2)

        if "botcontrol" in self.helper.data:
            self.helper.data["botcontrol"]["manualsell"] = True
            self.helper.write_data(query.data.replace("confirm_sell_", ""))
            query.edit_message_text(
                f"Selling: {query.data.replace('confirm_sell_', '').replace('.json','')}\n<i>Please wait for sale notification...</i>",
                parse_mode="HTML",
            )

    def buyresponse(self, update):
        """create the manual buy order"""
        query = update.callback_query
        logger.info("called buyresponse - %s", query.data)
        # if self.helper.read_data(query.data.replace("confirm_buy_", "")):
        while self.helper.read_data(query.data.replace("confirm_buy_", "")) == False:
            sleep(0.2)
        if "botcontrol" in self.helper.data:
            self.helper.data["botcontrol"]["manualbuy"] = True
            self.helper.write_data(query.data.replace("confirm_buy_", ""))
            query.edit_message_text(
                f"Buying: {query.data.replace('confirm_buy_', '').replace('.json','')}\n<i>Please wait for sale notification...</i>",
                parse_mode="HTML",
            )

    def showconfigresponse(self, update):
        """display config settings based on exchanged selected"""
        with open(os.path.join(self.helper.config_file), "r", encoding="utf8") as json_file:
            self.helper.config = json.load(json_file)

        query = update.callback_query
        logger.info("called showconfigresponse - %s", query.data)

        if query.data == "ex_scanner":
            pbot = self.helper.config[query.data.replace("ex_", "")]
        else:
            pbot = self.helper.config[query.data.replace("ex_", "")]["config"]

        query.edit_message_text(query.data.replace("ex_", "") + "\n" + json.dumps(pbot, indent=4))

    def getBotInfo(self, update):
        try:
            query = update.callback_query
            query.answer()
        except:
            pass
        count = 0
        for file in self.helper.getActiveBotList():
            output = ""
            count += 1
            
            while self.helper.read_data(file) == False:
                sleep(0.2)

            output = output + f"\U0001F4C8 <b>{file}</b> "

            last_modified = datetime.now() - datetime.fromtimestamp(
                os.path.getmtime(
                    os.path.join(self.datafolder, "telegram_data", f"{file}.json")
                )
            )

            icon = "\U0001F6D1" # red dot
            if last_modified.seconds > 90 and last_modified.seconds != 86399:
                output = f"{output} {icon} <b>Status</b>: <i>defaulted</i>"
            elif "botcontrol" in self.helper.data and "status" in self.helper.data["botcontrol"]:
                if self.helper.data["botcontrol"]["status"] == "active":
                    icon = "\U00002705" # green tick
                if self.helper.data["botcontrol"]["status"] == "paused":
                    icon = "\U000023F8" # pause icon
                if self.helper.data["botcontrol"]["status"] == "exit":
                    icon = "\U0000274C" # stop icon
                output = f"{output} {icon} <b>Status</b>: <i>{self.helper.data['botcontrol']['status']}</i>"
                output = f"{output} \u23F1 <b>Uptime</b>: <i>{self._getUptime(self.helper.data['botcontrol']['started'])}</i>\n"
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

        if count == 0:
            query.edit_message_text(f"<b>Bot Count ({count})</b>", parse_mode="HTML")
        else:
            update.effective_message.reply_html(f"<b>Bot Count ({count})</b>")

    def getMargins(self, response):

        query = response.callback_query
        query.answer()
        query.edit_message_text("<i>Getting Margins..</i>", parse_mode="HTML")
        cOutput = []
        oOutput = []
        closedbotCount = 0
        openbotCount = 0
        print(self.helper.getActiveBotList())
        for market in self.helper.getActiveBotList():
            while self.helper.read_data(market) == False:
                sleep(0.2)

            closedoutput = "" 
            openoutput = ""
            if "margin" in self.helper.data:
                if "margin" in self.helper.data and self.helper.data["margin"] == " ":
                    closedoutput = (closedoutput + f"<b>{market}</b>")
                    closedoutput = closedoutput + f"\n<i>{self.helper.data['message']}</i>\n"
                    cOutput.append(closedoutput)
                    closedbotCount += 1
                elif len(self.helper.data) > 2:
                    openoutput = openoutput + self._getMarginText(market)
                    oOutput.append(openoutput)
                    openbotCount += 1

        if (query.data.__contains__("orders") or query.data.__contains__("all")) and openbotCount > 0:
            for output in oOutput:
                response.effective_message.reply_html(f"{output}")
                sleep(0.5)

        elif (query.data.__contains__("orders") or query.data.__contains__("all")) and openbotCount == 0:
            response.effective_message.reply_html("<b>No open orders found.</b>")

        if (query.data.__contains__("pairs") or query.data.__contains__("all")) and closedbotCount > 0:
            for output in cOutput:
                response.effective_message.reply_html(f"{output}")
                sleep(1)

        elif (query.data.__contains__("pairs") or query.data.__contains__("all")) and closedbotCount == 0:
            response.effective_message.reply_html("<b>No active pairs found.</b>")

    def StartMarketScan(self, update, scanmarkets: bool = True, startbots: bool = True, debug: bool = False):
        logger.info("called StartMarketScan")
        try:
            with open("scanner.json") as json_file:
                config = json.load(json_file)
        except IOError as err:
            update.message.reply_text(
                f"<i>scanner.json config error</i>\n{err}", parse_mode="HTML"
            )
            return

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

            update.effective_message.reply_html("<b>Scan Complete.</b>")
        
        if not startbots:
            update.effective_message.reply_html("<b>Operation Complete  (0 started)</b>")
            return

        update.effective_message.reply_html("<i>stopping bots..</i>")
        for file in self.helper.getActiveBotList():
            self.helper.stopRunningBot(file, "exit")
            sleep(5)

        botcounter = len(self.helper.getActiveBotList())
        maxbotcount = self.helper.config["scanner"]["maxbotcount"] if "maxbotcount" in self.helper.config["scanner"] else 0

        self.helper.read_data()
        for ex in config:
            if maxbotcount > 0 and botcounter >= maxbotcount:
                break
            for quote in config[ex]["quote_currency"]:
                update.effective_message.reply_html(f"Starting {ex} ({quote}) bots...")
                logger.info("%s - (%s)", ex, quote)
                if not os.path.isfile(os.path.join(self.datafolder, "telegram_data", f"{ex}_{quote}_output.json")):
                    continue

                with open(
                    os.path.join(
                        self.datafolder, "telegram_data", f"{ex}_{quote}_output.json"
                        ), "r", encoding="utf8") as json_file:
                    data = json.load(json_file)

                outputmsg =  f"<b>{ex} ({quote})</b> \u23F3 \n"

                for row in data:
                    if debug:
                        logger.info("%s", row)

                    if self.helper.config["scanner"]["maxbotcount"] > 0 and botcounter >= self.helper.config["scanner"]["maxbotcount"]:
                        break
                    
                    if self.helper.config["scanner"]["enableleverage"] == False \
                            and (str(row).__contains__(f"DOWN{quote}") or str(row).__contains__(f"UP{quote}") or str(row).__contains__(f"3L{quote}") or str(row).__contains__(f"3S{quote}")):
                        continue

                    if row in self.helper.data["scannerexceptions"]:
                        outputmsg = outputmsg + f"*** {row} found on scanner exception list ***\n"
                    else:
                        if data[row]["atr72_pcnt"] != None:
                            if data[row]["atr72_pcnt"] >= self.helper.config["scanner"]["atr72_pcnt"]:
                                if self.helper.config["scanner"]["enable_buy_next"] and data[row]["buy_next"]:
                                    outputmsg = outputmsg + f"<i><b>{row}</b>  //--//  <b>atr72_pcnt:</b> {data[row]['atr72_pcnt']}%  //--//  <b>buy_next:</b> {data[row]['buy_next']}</i>\n"
                                    self.helper.startProcess(row, ex, "", "scanner")
                                    botcounter += 1
                                elif not self.helper.config["scanner"]["enable_buy_next"]:
                                    outputmsg = outputmsg + f"<i><b>{row}</b>  //--//  <b>atr72_pcnt:</b> {data[row]['atr72_pcnt']}%</i>\n"
                                    self.helper.startProcess(row, ex, "", "scanner")
                                    botcounter += 1
                                if debug == False:
                                    sleep(10)

                update.effective_message.reply_html(f"{outputmsg}")

        update.effective_message.reply_html(f"<i>Operation Complete.  ({botcounter} started)</i>")

    def deleteresponse(self, update):
        """delete selected bot"""
        self.helper.read_data()

        query = update.callback_query
        logger.info("called deleteresponse - %s", query.data)
        self.helper.data["markets"].pop(str(query.data).replace("delete_", ""))

        self.helper.write_data()

        query.edit_message_text(
            f"<i>Deleted {str(query.data).replace('delete_', '')} crypto bot</i>",
            parse_mode="HTML",
        )

    def RemoveExceptionCallBack(self, update):
        """delete selected bot"""
        self.helper.read_data()

        query = update.callback_query
        query.answer()

        self.helper.data["scannerexceptions"].pop(str(query.data).replace("delexcep_", ""))

        self.helper.write_data()

        query.edit_message_text(
            f"<i>Removed {str(query.data).replace('delexcep_', '')} from exception list. bot</i>",
            parse_mode="HTML",
        )