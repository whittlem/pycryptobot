""" Telegram Bot Actions """
import os
import json
import subprocess

# import logging
import csv
from datetime import datetime, timedelta

from time import sleep
from models.telegram.helper import TelegramHelper
from models.telegram.settings import SettingsEditor

class TelegramActions:
    """Telegram Bot Action Class"""

    def __init__(self, tg_helper: TelegramHelper) -> None:
        self.helper = tg_helper
        self.settings = SettingsEditor(tg_helper)

    def _get_margin_text(self, market):
        """Get marin text"""
        light_icon, margin_icon = (
            "\U0001F7E2" if "-" not in self.helper.data["margin"] else "\U0001F534",
            "\U0001F973" if "-" not in self.helper.data["margin"] else "\U0001F97A",
        )

        result = (
            f"{light_icon} <b>{market}</b> (<i>{self.helper.data['exchange']}</i>)\n"
            f"{margin_icon} Margin: {self.helper.data['margin']}  "
            f"\U0001F4B0 P/L: {self.helper.data['delta']}\n"
            f"TSL Trg: {self.helper.data['trailingstoplosstriggered']}  "
            f"TSL Change: {float(self.helper.data['change_pcnt_high']).__round__(4)}\n"
            # f"TPL Trg: {self.helper.data['preventlosstriggered']}  "
            # f"TPL Change: {float(self.helper.data['change_pcnt_high']).__round__(4)}\n"
        )
        return result

    @staticmethod
    def _get_uptime(date: str):
        """Get uptime"""
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

    def start_open_orders(self, update, context):
        """Start bots for open trades (data.json)"""
        self.helper.logger.info("called start_open_orders")
        self.helper.send_telegram_message(
            update, "<b>Starting markets with open trades..</b>", context=context, new_message=False
        )
        self.helper.read_data()
        for market in self.helper.data["opentrades"]:
            if not self.helper.is_bot_running(market):
                self.helper.start_process(
                    market,
                    self.helper.data["opentrades"][market]["exchange"],
                    "",
                    "telegram-open",
                )
            sleep(10)
        self.helper.send_telegram_message(
            update, "<i>Markets have been started</i>", context=context
        )
        sleep(1)
        self.get_bot_info(None, None)

    def sell_response(self, update, context, market_override = ""):
        """create the manual sell order"""
        if market_override != "":
            read_ok = self.helper.read_data(market_override)
            if read_ok and "botcontrol" in self.helper.data:
                self.helper.data["botcontrol"]["manualsell"] = True
                self.helper.write_data(market_override)
                self.helper.send_telegram_message(
                    update,
                    f"Selling: {market_override.replace('.json','')}"
                    "\n<i>Please wait for sale notification...</i>",
                    context=context, new_message=False,
                )
            return

        query = update.callback_query
        self.helper.logger.info("called sell_response - %s", query.data)

        if query.data.__contains__("all"):
            self.helper.send_telegram_message(
                update, "<b><i>Initiating sell orders..</i></b>", context=context, new_message=False
            )
            tg_message = ""
            for market in self.helper.get_active_bot_list("active"):
                if not self.helper.read_data(market):
                    continue
                if "margin" in self.helper.data and self.helper.data["margin"] != " ":
                    if "botcontrol" in self.helper.data:
                        self.helper.data["botcontrol"]["manualsell"] = True
                        self.helper.write_data(market)
                        tg_message = f"{tg_message} {market},"
                sleep(0.2)
            self.helper.send_telegram_message(
                update,
                f"<b>{tg_message}</b>\n<i>Please wait for sale notification...</i>",
                context=context,
            )
        else:
            read_ok = self.helper.read_data(query.data.replace("confirm_sell_", ""))
            if read_ok and "botcontrol" in self.helper.data:
                self.helper.data["botcontrol"]["manualsell"] = True
                self.helper.write_data(query.data.replace("confirm_sell_", ""))
                self.helper.send_telegram_message(
                    update,
                    f"Selling: {query.data.replace('confirm_sell_', '').replace('.json','')}"
                    "\n<i>Please wait for sale notification...</i>",
                    context=context, new_message=False
                )

    def buy_response(self, update, context, market_override = ""):
        """create the manual buy order"""

        if market_override != "":
            read_ok = self.helper.read_data(market_override)
            if read_ok and "botcontrol" in self.helper.data:
                self.helper.data["botcontrol"]["manualbuy"] = True
                self.helper.write_data(market_override)
                self.helper.send_telegram_message(
                    update,
                    f"Buying: {market_override.replace('.json','')}"
                    "\n<i>Please wait for buy notification...</i>",
                    context=context, new_message=False,
                )
            return

        query = update.callback_query
        self.helper.logger.info("called buy_response - %s", query.data)

        if query.data == "all":
            self.helper.send_telegram_message(
                update, "<b><i>Initiating buy orders..</i></b>", context=context, new_message=False
            )
            tg_message = ""
            for market in self.helper.get_active_bot_list("active"):
                if not self.helper.read_data(market):
                    continue
                if "margin" in self.helper.data and self.helper.data["margin"] == " ":
                    if "botcontrol" in self.helper.data:
                        self.helper.data["botcontrol"]["manualbuy"] = True
                        self.helper.write_data(market)
                        tg_message = f"{tg_message} {market},"
                sleep(0.2)
            self.helper.send_telegram_message(
                update,
                f"<b>{tg_message}</b>\n<i>Please wait for buy notification...</i>",
                context=context,
            )
        else:
            read_ok = self.helper.read_data(query.data.replace("confirm_buy_", ""))
            if read_ok and "botcontrol" in self.helper.data:
                self.helper.data["botcontrol"]["manualbuy"] = True
                self.helper.write_data(query.data.replace("confirm_buy_", ""))
                self.helper.send_telegram_message(
                    update,
                    f"Buying: {query.data.replace('confirm_buy_', '').replace('.json','')}"
                    "\n<i>Please wait for buy notification...</i>",
                    context=context, new_message=False,
                )

    def show_config_response(self, update):
        """display config settings based on exchanged selected"""
        self.helper.read_config()

        query = update.callback_query
        self.helper.logger.info("called show_config_response - %s", query.data)

        if query.data == "scanner":
            pbot = self.helper.config[query.data]
        else:
            pbot = self.helper.config[query.data]["config"]

        self.helper.send_telegram_message(
            update, query.data + "\n" + json.dumps(pbot, indent=4), new_message=False
        )

    def get_bot_info(self, update=None, context=None):
        """Get running bot information"""
        count = 0
        for file in self.helper.get_active_bot_list():
            output = ""
            count += 1

            if not self.helper.read_data(file):
                continue

            output = (
                output + f"\U0001F4C8 <b>{file} ({self.helper.data['exchange']})</b> "
            )

            last_modified = datetime.now() - datetime.fromtimestamp(
                os.path.getmtime(
                    os.path.join(
                        self.helper.datafolder, "telegram_data", f"{file}.json"
                    )
                )
            )
            icon = "\U0001F6D1"  # red dot
            if last_modified.seconds > 90 and last_modified.seconds != 86399:
                output = f"{output} {icon} <b>Status</b>: <i>defaulted</i>"
            elif (
                "botcontrol" in self.helper.data
                and "status" in self.helper.data["botcontrol"]
            ):
                if self.helper.data["botcontrol"]["status"] == "active":
                    icon = "\U00002705"  # green tick
                if self.helper.data["botcontrol"]["status"] == "paused":
                    icon = "\U000023F8"  # pause icon
                if self.helper.data["botcontrol"]["status"] == "exit":
                    icon = "\U0000274C"  # stop icon
                output = f"{output} {icon} <b>Status</b>: <i> {self.helper.data['botcontrol']['status']}</i>"
                output = f"{output} \u23F1 <b>Uptime</b>: <i> {self.helper.get_uptime()}</i>\n"
            else:
                output = f"{output} {icon} <b>Status</b>: <i>stopped</i> "

            if count == 1:
                # if update is not None or context is not None:
                self.helper.send_telegram_message(
                    update, output, context=context, new_message=False
                )
            else:
                # if update is not None:
                self.helper.send_telegram_message(update, f"{output}")
            sleep(0.2)

        if count == 0:
            self.helper.send_telegram_message(
                update,
                f"<b>Bot Count ({count})</b>",
                context=context,
                new_message=False,
            )
        else:
            self.helper.send_telegram_message(
                update, f"<b>Bot Count ({count})</b>", context=context
            )

        return f"Bot Count ({count})"

    def get_margins(self, update, option):
        """Get margins"""
        self.helper.send_telegram_message(update, f"<i>Getting current {'margins' if option == 'orders' else 'active pairs' if option == 'pairs' else 'margins and active pairs'}..</i>", new_message=False)
        closed_output = []
        open_output = []
        closed_count = 0
        open_count = 0

        for market in self.helper.get_active_bot_list():
            if not self.helper.read_data(market):
                continue
            closed_output_text = ""
            open_output_text = ""
            if "margin" in self.helper.data:
                if "margin" in self.helper.data and self.helper.data["margin"] == " ":
                    closed_output_text = closed_output_text + f"<b>{market}</b>"
                    closed_output_text = (
                        closed_output_text + f"\n<i>{self.helper.data['message']}</i>\n"
                    )
                    closed_output.append(closed_output_text)
                    closed_count += 1
                elif len(self.helper.data) > 2:
                    open_output_text = open_output_text + self._get_margin_text(market)
                    open_output.append(open_output_text)
                    open_count += 1

        if option in ("orders", "all") and open_count > 0:
            for output in open_output:
                self.helper.send_telegram_message(update, output)
                sleep(0.5)
        elif option in ("orders", "all") and open_count == 0:
            self.helper.send_telegram_message(
                update, "<b>No open orders found.</b>"
            )

        if option in ("pairs", "all") and closed_count > 0:
            for output in closed_output:
                self.helper.send_telegram_message(update, output)
                sleep(1)
        elif option in ("pairs", "all") and closed_count == 0:
            self.helper.send_telegram_message(
                update, "<b>No active pairs found.</b>"
            )

    def start_market_scan(
        self,
        update,
        context,
        use_default_scanner: bool = True,
        scanmarkets: bool = True,
        startbots: bool = True,
    )-> bool:
        """Start market scanner/screener"""
        # Check whether using the scanner or the screener - use correct config file etc
        if use_default_scanner is True:
            scanner_config_file = "scanner.json"
            scanner_script_file = "scanner.py"
        elif use_default_scanner is False:
            scanner_config_file = "screener.json"
            scanner_script_file = "screener.py"

        self.helper.logger.info("called start_market_scan - %s", scanner_script_file)

        try:
            self.helper.load_config()
            with open(f"{scanner_config_file}", encoding="utf8") as json_file:
                config = json.load(json_file)
        except IOError as err:
            self.helper.send_telegram_message(
                update,
                f"<i>{scanner_config_file} config error</i>\n{err}",
                context=context,
                new_message=False,
            )
            return False

        # If a bulk load file for the exchange exists - start up all the bulk bots for this
        for ex in config:
            for quote in config[ex]["quote_currency"]:
                if os.path.exists(
                    os.path.join(
                        self.helper.datafolder, "telegram_data", f"{ex}_bulkstart.csv"
                    )
                ):
                    self.helper.send_telegram_message(
                        update,
                        f"<i>Found bulk load CSV file for {ex}... Loading pairs</i>",
                        context=context,
                    )
                    try:
                        with open(
                            os.path.join(
                                self.helper.datafolder,
                                "telegram_data",
                                f"{ex}_bulkstart.csv",
                            ),
                            newline="",
                            encoding="utf-8",
                        ) as csv_obj:
                            csv_file = csv.DictReader(csv_obj)
                            for row in csv_file:
                                if (
                                    "market" in row
                                    and row["market"] is not None
                                    and quote in row["market"]
                                ):
                                    # Start the process disregarding bot limits for the moment
                                    self.helper.send_telegram_message(
                                        update,
                                        f"Bulk Starting {row['market']} on {ex}...",
                                        context=context,
                                    )
                                    self.helper.start_process(
                                        row["market"], ex, "", "scanner"
                                    )
                                    sleep(7)
                    except IOError:
                        pass
                else:
                    # No Bulk Start File Found
                    pass

        if scanmarkets:
            if bool(self.helper.settings["notifications"]["enable_screener"]):
                reply = "<i>Gathering market data\nplease wait...</i> \u23F3"
                self.helper.send_telegram_message(update, reply, context=context)
            try:
                self.helper.logger.info("Starting Market Scan")
                subprocess.getoutput(f"python3 {scanner_script_file}")
            except Exception as err:
                self.helper.send_telegram_message(
                    update, "<b>scanning failed.</b>", context=context
                )
                self.helper.logger.error(err)
                raise

            if bool(self.helper.settings["notifications"]["enable_screener"]):
                self.helper.send_telegram_message(
                    update, "<b>Scan Complete.</b>", context=context
                )

        # Watchdog process - check for hung bots and force restart them
        if bool(self.helper.settings["notifications"]["enable_screener"]):
            self.helper.send_telegram_message(
                update, "<i>Fido checking for hung bots..</i>", context=context
            )

        self.helper.logger.debug("Fido checking for hung bots..")

        for file in self.helper.get_hung_bot_list():
            ex = self.helper.get_running_bot_exchange(file)
            self.helper.stop_running_bot(file, "exit", True)
            sleep(3)
            os.remove(
                os.path.join(self.helper.datafolder, "telegram_data", f"{file}.json")
            )
            sleep(1)

            if bool(self.helper.settings["notifications"]["enable_screener"]):
                self.helper.send_telegram_message(
                    update,
                    f"Restarting {file} as it appears to have hung...",
                    context=context,
                )

            if startbots:
                self.helper.start_process(file, ex, "", "scanner")
                sleep(1)

        if not startbots:
            if bool(self.helper.settings["notifications"]["enable_screener"]):
                self.helper.send_telegram_message(
                    update, "<b>Operation Complete (0 started)</b>", context=context
                )
            return True

        # Check to see if the bot would be restarted anyways from the scanner
        # and dont stop to maintain trailingbuypcnt etc
        scanned_bots = []

        for ex in config:
            for quote in config[ex]["quote_currency"]:
                try:
                    with open(
                        os.path.join(
                            self.helper.datafolder,
                            "telegram_data",
                            f"{ex}_{quote}_output.json",
                        ),
                        "r",
                        encoding="utf8",
                    ) as json_file:
                        data = json.load(json_file)
                    for row in data:
                        if data[row]["atr72_pcnt"] is not None:
                            if (
                                data[row]["atr72_pcnt"]
                                >= self.helper.config["scanner"]["atr72_pcnt"]
                            ):
                                scanned_bots.append(row)
                except:  # pylint: disable=bare-except
                    pass
        if bool(self.helper.settings["notifications"]["enable_screener"]):
            self.helper.send_telegram_message(
                update, "<i>stopping bots..</i>", context=context
            )

        self.helper.logger.debug("stopping bots")
        active_bots_list = self.helper.get_active_bot_list()
        open_order_bot_list = self.helper.get_active_bot_list_with_open_orders()
        manual_started_bots = self.helper.get_manual_started_bot_list()
        self.helper.read_data()
        market_exceptions = self.helper.data["scannerexceptions"]

        for file in active_bots_list:
            if (
                (file not in scanned_bots)
                and (file not in open_order_bot_list)
                and (file not in manual_started_bots)
                and (file not in market_exceptions)
            ):
                self.helper.stop_running_bot(file, "exit")
                sleep(3)
            else:
                if bool(self.helper.settings["notifications"]["enable_screener"]):
                    self.helper.send_telegram_message(
                        update,
                        f"Not stopping {file} - in scanner list, or has open order...",
                        context=context,
                    )

        total_bots_started = 0
        exchange_bots_started = 0
        active_at_start = len(self.helper.get_active_bot_list())
        maxbotcount = self.helper.maxbotcount
        bots_per_exchange = self.helper.exchange_bot_count

        self.helper.read_data()
        for ex in config:
            if (
                maxbotcount > 0
                and (total_bots_started + active_at_start) >= maxbotcount
            ):
                break
            exchange_bots_started = self.helper.get_exchange_bot_ruuning_count(ex)
            for quote in config[ex]["quote_currency"]:
                if bool(self.helper.settings["notifications"]["enable_screener"]):
                    self.helper.send_telegram_message(
                        update, f"Starting {ex} ({quote}) bots...", context=context
                    )

                self.helper.logger.info("starting %s - (%s) bots", ex, quote)
                if not os.path.isfile(
                    os.path.join(
                        self.helper.datafolder,
                        "telegram_data",
                        f"{ex}_{quote}_output.json",
                    )
                ):
                    continue

                with open(
                    os.path.join(
                        self.helper.datafolder,
                        "telegram_data",
                        f"{ex}_{quote}_output.json",
                    ),
                    "r",
                    encoding="utf8",
                ) as json_file:
                    data = json.load(json_file)

                outputmsg = f"<b>{ex} ({quote})</b> \u23F3 \n"

                msg_cnt = 1

                for row in data:
                    if (
                        maxbotcount > 0
                        and (total_bots_started + active_at_start) >= maxbotcount
                    ):
                        break
                    if (
                        bots_per_exchange > 0
                        and exchange_bots_started >= bots_per_exchange
                    ):
                        exchange_bots_started = 0
                        break
                    if self.helper.enableleverage is False and (
                        str(row).__contains__(f"DOWN{quote}")
                        or str(row).__contains__(f"UP{quote}")
                        or str(row).__contains__(f"3L-{quote}")
                        or str(row).__contains__(f"3S-{quote}")
                    ):
                        if msg_cnt == 1:
                            if bool(
                                self.helper.settings["notifications"]["enable_screener"]
                            ):
                                self.helper.send_telegram_message(
                                    update,
                                    f"Ignoring {row} {ex} ({quote}) "
                                    "Leverage Pairs (enableleverage is disabled)...",
                                    context=context,
                                )
                            msg_cnt += 1
                            self.helper.logger.debug(
                                f"Ignoring ({row}) Leverage Pairs (enableleverage is disabled)..."
                            )
                        continue

                    if row in market_exceptions:
                        outputmsg = (
                            outputmsg
                            + f"*** {row} found on scanner exception list ***\n"
                        )
                    else:
                        if data[row]["atr72_pcnt"] is not None:
                            if (
                                data[row]["atr72_pcnt"]
                                >= self.helper.config["scanner"]["atr72_pcnt"]
                            ):
                                if (
                                    self.helper.config["scanner"]["enable_buy_next"]
                                    and data[row]["buy_next"]
                                ):
                                    outputmsg = (
                                        outputmsg + f"<i><b>{row}</b>  //--//  "
                                        f"<b>atr72_pcnt:</b> {data[row]['atr72_pcnt']}%  //--//"
                                        f"  <b>buy_next:</b> {data[row]['buy_next']}</i>\n"
                                    )
                                    if self.helper.is_bot_running(row):
                                        exchange_bots_started += 1
                                    if self.helper.start_process(
                                        row, ex, "", "scanner"
                                    ):
                                        total_bots_started += 1
                                        exchange_bots_started += 1
                                elif not self.helper.config["scanner"][
                                    "enable_buy_next"
                                ]:
                                    outputmsg = (
                                        outputmsg + f"<i><b>{row}</b>  //--//  "
                                        f"<b>atr72_pcnt:</b> {data[row]['atr72_pcnt']}%</i>\n"
                                    )
                                    if self.helper.is_bot_running(row):
                                        exchange_bots_started += 1
                                    if self.helper.start_process(
                                        row, ex, "", "scanner"
                                    ):
                                        total_bots_started += 1
                                        exchange_bots_started += 1
                                sleep(6)

                if bool(self.helper.settings["notifications"]["enable_screener"]):
                    self.helper.send_telegram_message(
                        update, outputmsg, context=context
                    )

        self.helper.send_telegram_message(
            update,
            f"<b>{scanner_config_file.replace('.json', '').capitalize()} "
            f"Operation Complete.</b><i>\n- {total_bots_started} started"
            f"\n- {active_at_start + total_bots_started} running</i>",
            context=context,
        )

        self.helper.logger.info("Market Scan Complete")
        return True

    def delete_response(self, update):
        """delete selected bot"""
        query = update.callback_query
        self.helper.logger.info("called delete_response - %s", query.data)
        write_ok, try_count = False, 0
        while not write_ok and try_count <= 5:
            try_count += 1
            self.helper.read_data()
            self.helper.data["markets"].pop(str(query.data).replace("delete_", ""))

            write_ok = self.helper.write_data()
            if not write_ok:
                sleep(1)

        self.helper.send_telegram_message(
            update,
            f"<i>Deleted {str(query.data).replace('delete_', '')} crypto bot</i>",
        )

    def remove_exception_callback(self, update):
        """remove bot exception"""
        query = update.callback_query
        self.helper.logger.info("called remove_exception_callback")
        write_ok, try_count = False, 0
        while not write_ok and try_count <= 5:
            try_count += 1
            self.helper.read_data()
            self.helper.data["scannerexceptions"].pop(
                str(query.data).replace("delexcep_", "")
            )

            write_ok = self.helper.write_data()
            if not write_ok:
                sleep(1)

        self.helper.send_telegram_message(
            update,
            f"<i>Removed {str(query.data).replace('delexcep_', '')} from exception list. bot</i>",
        )

    def get_closed_trades(self, update, days):
        """Read closed trades from data.json file"""
        if self.helper.read_data():
            now = datetime.now()
            now -= timedelta(days=days)
            trade_count = 0

            trade_counter = 0
            margin_calculation = 0.0
            margin_positive = 0.0
            positive_counter = 0
            margin_negative = 0.0
            negative_counter = 0

            if days == 99:
                self.helper.send_telegram_message(
                    update, "<i>Getting all trades summary..</i>", new_message=False
                )
            else:
                self.helper.send_telegram_message(
                    update, f"<i>Getting summary of trades for last {days} day(s)..</i>", new_message=False
                )

            for trade_datetime in self.helper.data["trades"]:
                if (
                    datetime.strptime(trade_datetime, "%Y-%m-%d %H:%M:%S").isoformat()
                    < now.isoformat()
                ):
                    continue
                if days > 0:
                    trade_counter += 1
                    margin = float(
                        self.helper.data["trades"][trade_datetime]["margin"][
                            : self.helper.data["trades"][trade_datetime]["margin"].find(
                                "%"
                            )
                        ]
                    )
                    margin_calculation += margin
                    if margin > 0.0:
                        positive_counter += 1
                        margin_positive += margin
                    else:
                        negative_counter += 1
                        margin_negative += margin
                    if trade_counter == 1:
                        first_trade_date = trade_datetime
                    last_trade_date = trade_datetime
                else:
                    trade_count += 1
                    output = ""
                    output = (
                        output
                        + f"<b>{self.helper.data['trades'][trade_datetime]['pair']}</b>\n{trade_datetime}"
                    )
                    output = (
                        output
                        + f"\n<i>Sold at: {self.helper.data['trades'][trade_datetime]['price']}   Margin: {self.helper.data['trades'][trade_datetime]['margin']}</i>\n"
                    )
                    if days != 99:
                        if output != "":
                            self.helper.send_telegram_message(update, output)
                        if trade_count == 10:
                            trade_count = 1
                            sleep(3)
                        else:
                            sleep(0.5)

            if trade_count == 0 and trade_counter == 0:
                self.helper.send_telegram_message(
                    update, "<b>No closed trades found</b>", new_message=False
                )
                return "No closed trades found"

            if days > 0:
                summary = (
                    f"First Recorded Date: <b>{first_trade_date}</b>\n"
                    f"Last Recorded Date: <b>{last_trade_date}</b>\n\n"
                    f"Profit: <b>{round(margin_positive,2)}%</b>  from (<b>{positive_counter}</b>) trades\n"
                    f"Loss: <b>{round(margin_negative,2)}%</b>  from (<b>{negative_counter}</b>) trades\n"
                    f"Total: <b>{round(margin_calculation,2)}%</b>  from (<b>{trade_counter}</b>) trades\n"
                    f"Average: <b>{round((margin_calculation/trade_counter),2)}%</b>  per trade"
                )

                self.helper.send_telegram_message(update, summary)

            if update is None:
                return summary
