import sys
from time import sleep
from datetime import datetime, timedelta
from models.TradingAccount import TradingAccount
from models.exchange.ExchangesEnum import Exchange
from views.PyCryptoBot import RichText


class Stats:
    def __init__(self, app, account: TradingAccount = None) -> None:
        self.app = app
        self.account = account
        self.order_pairs = []
        self.fiat_currency = None

    def get_data(self, market):
        # get completed live orders
        self.app.is_live = 1
        self.orders = self.account.get_orders(market, "", "done")
        self.app.market = market
        if self.fiat_currency is not None:
            if self.app.quote_currency != self.fiat_currency:
                raise ValueError("all currency pairs in statgroup must use the same quote currency")
        else:
            self.fiat_currency = self.app.quote_currency

        # get buy/sell pairs (merge as necessary)
        last_order = None
        # pylint: disable=unused-variable
        for index, row in self.orders.iterrows():
            time = row["created_at"].to_pydatetime()

            if row["action"] == "buy":
                if self.app.exchange == Exchange.COINBASE or self.app.exchange == Exchange.COINBASEPRO:
                    amount = row["filled"] * row["price"] + row["fees"]
                else:
                    amount = row["size"]
                if last_order in ["sell", None]:
                    last_order = "buy"
                    self.order_pairs.append(
                        {
                            "buy": {"time": time, "size": float(amount)},
                            "sell": None,
                            "market": self.app.market,
                        }
                    )
                else:
                    self.order_pairs[-1]["buy"]["size"] += float(amount)
            else:
                if self.app.exchange == Exchange.COINBASE or self.app.exchange == Exchange.COINBASEPRO:
                    amount = (row["filled"] * row["price"]) - row["fees"]
                else:
                    amount = (float(row["filled"]) * float(row["price"])) - row["fees"]
                if last_order is None:  # first order is a sell (no pair)
                    continue
                if last_order == "buy":
                    last_order = "sell"
                    if float(amount) > 0:
                        self.order_pairs[-1]["sell"] = {
                            "time": time,
                            "size": float(amount),
                        }
                else:
                    if float(amount) > 0:
                        self.order_pairs[-1]["sell"]["size"] += float(amount)
        # remove open trade
        if len(self.order_pairs) > 0:
            if self.order_pairs[-1]["sell"] is None:
                s = []
                for order in self.order_pairs:
                    if order["sell"] is not None:
                        s.append(order)
                self.order_pairs = s

        # return [x.replace(".json", "") if x.__contains__(".json") else x for x in jsonfiles]

    def show(self):
        if self.app.stats:
            if self.app.statgroup:
                for currency in self.app.statgroup:
                    self.get_data(currency)
                    sleep(5)
            else:
                self.get_data(self.app.market)
            self.data_display()

    def data_display(self):
        # get % gains and delta
        for pair in self.order_pairs:
            try:  # return 0 if unexpected exception
                pair["delta"] = float(pair["sell"]["size"]) - float(pair["buy"]["size"])
                if self.app.debug:
                    RichText.notify(str(pair["sell"]["size"]), self.app, "debug")
            except Exception as err:
                if self.app.debug:
                    RichText.notify(err, self.app, "debug")
                RichText.notify("unexpected error calculating delta, returning 0", self.app, "warning")
                if self.app.debug:
                    RichText.notify(pair, self.app, "debug")
                pair["delta"] = 0

            try:  # return 0 if unexpected exception
                pair["gain"] = (float(pair["delta"]) / float(pair["buy"]["size"])) * 100
            except Exception as err:
                if self.app.debug:
                    RichText.notify(err, self.app, "debug")
                RichText.notify("unexpected error calculating gain, returning 0", self.app, "warning")
                if self.app.debug:
                    RichText.notify(pair, self.app, "debug")
                pair["gain"] = 0

        # get day/week/month/all time totals
        totals = {"today": [], "week": [], "month": [], "all_time": []}
        today = datetime.today().date()
        lastweek = today - timedelta(days=7)
        lastmonth = today - timedelta(days=30)
        if self.app.statstartdate:
            try:
                start = datetime.strptime(self.app.statstartdate, "%Y-%m-%d").date()
            except Exception:
                raise ValueError("format of --statstartdate must be yyyy-mm-dd")
        else:
            start = None

        # popular currencies
        symbol = self.app.quote_currency
        if symbol in ["USD", "AUD", "CAD", "SGD", "NZD"]:
            symbol = "$"
        if symbol == "EUR":
            symbol = "€"
        if symbol == "GBP":
            symbol = "£"

        if self.app.statdetail:
            headers = [
                "| Num  ",
                "| Market     ",
                "| Date of Sell ",
                "| Price bought ",
                "| Price sold  ",
                "| Delta     ",
                "| Gain/Loss  |",
            ]
            border = "+"
            for header in headers:
                border += "-" * (len(header) - 1) + "+"
            border = border[:-2] + "+"
            print(border + "\n" + "".join([x for x in headers]) + "\n" + border)
            for i, pair in enumerate(self.order_pairs):
                if start:
                    if pair["sell"]["time"].date() < start:
                        continue
                d_num = "| " + str(i + 1)
                d_num = d_num + " " * (len(headers[0]) - len(d_num))
                d_date = "| " + str(pair["sell"]["time"].date())
                d_market = "| " + pair["market"]
                d_market = d_market + " " * (len(headers[1]) - len(d_market))
                d_date = d_date + " " * (len(headers[2]) - len(d_date))
                d_buy_size = "| " + symbol + " " + "{:.2f}".format(pair["buy"]["size"])
                d_buy_size = d_buy_size + " " * (len(headers[3]) - len(d_buy_size))
                d_sell_size = "| " + symbol + " " + "{:.2f}".format(pair["sell"]["size"])
                d_sell_size = d_sell_size + " " * (len(headers[4]) - len(d_sell_size))
                if pair["delta"] > 0:
                    d_delta = "| " + symbol + " {:.2f}".format(pair["delta"])
                else:
                    d_delta = "| " + symbol + "{:.2f}".format(pair["delta"])
                d_delta = d_delta + " " * (len(headers[5]) - len(d_delta))
                if pair["gain"] > 0:
                    d_gain = "|  " + "{:.2f}".format(pair["gain"]) + " %"
                else:
                    d_gain = "| " + "{:.2f}".format(pair["gain"]) + " %"
                d_gain = d_gain + " " * (len(headers[6]) - len(d_gain) - 1) + "|"
                print(f"{d_num}{d_market}{d_date}{d_buy_size}{d_sell_size}{d_delta}{d_gain}")

            print(border)
            print("")
            sys.exit()

        for pair in self.order_pairs:
            if start:
                if pair["sell"]["time"].date() < start:
                    continue
            totals["all_time"].append(pair)
            if pair["sell"]["time"].date() == today:
                totals["today"].append(pair)
            if pair["sell"]["time"].date() > lastweek:
                totals["week"].append(pair)
            if pair["sell"]["time"].date() > lastmonth:
                totals["month"].append(pair)

        # prepare data for output
        today_per = [x["gain"] for x in totals["today"]]
        week_per = [x["gain"] for x in totals["week"]]
        month_per = [x["gain"] for x in totals["month"]]
        all_time_per = [x["gain"] for x in totals["all_time"]]
        today_gain = [x["delta"] for x in totals["today"]]
        week_gain = [x["delta"] for x in totals["week"]]
        month_gain = [x["delta"] for x in totals["month"]]
        all_time_gain = [x["delta"] for x in totals["all_time"]]

        if len(today_per) > 0:
            today_delta = [(x["sell"]["time"] - x["buy"]["time"]).total_seconds() for x in totals["today"]]
            today_delta = timedelta(seconds=int(sum(today_delta) / len(today_delta)))
        else:
            today_delta = "0:0:0"
        if len(week_per) > 0:
            week_delta = [(x["sell"]["time"] - x["buy"]["time"]).total_seconds() for x in totals["week"]]
            week_delta = timedelta(seconds=int(sum(week_delta) / len(week_delta)))
        else:
            week_delta = "0:0:0"
        if len(month_per) > 0:
            month_delta = [(x["sell"]["time"] - x["buy"]["time"]).total_seconds() for x in totals["month"]]
            month_delta = timedelta(seconds=int(sum(month_delta) / len(month_delta)))
        else:
            month_delta = "0:0:0"
        if len(all_time_per) > 0:
            all_time_delta = [(x["sell"]["time"] - x["buy"]["time"]).total_seconds() for x in totals["all_time"]]
            all_time_delta = timedelta(seconds=int(sum(all_time_delta) / len(all_time_delta)))
        else:
            all_time_delta = "0:0:0"

        today_sum = symbol + " {:.2f}".format(round(sum(today_gain), 2)) if len(today_gain) > 0 else symbol + " 0.00"
        week_sum = symbol + " {:.2f}".format(round(sum(week_gain), 2)) if len(week_gain) > 0 else symbol + " 0.00"
        month_sum = symbol + " {:.2f}".format(round(sum(month_gain), 2)) if len(month_gain) > 0 else symbol + " 0.00"
        all_time_sum = symbol + " {:.2f}".format(round(sum(all_time_gain), 2)) if len(all_time_gain) > 0 else symbol + " 0.00"
        today_percent = str(round(sum(today_per), 4)) + "%" if len(today_per) > 0 else "0.0000%"
        week_percent = str(round(sum(week_per), 4)) + "%" if len(week_per) > 0 else "0.0000%"
        month_percent = str(round(sum(month_per), 4)) + "%" if len(month_per) > 0 else "0.0000%"
        all_time_percent = str(round(sum(all_time_per), 4)) + "%" if len(all_time_per) > 0 else "0.0000%"

        trades = "Number of Completed Trades:"
        gains = "Percentage Gains:"
        aver = "Average Time Held (H:M:S):"
        success = "Total Profit/Loss:"
        width = 30

        if self.app.statgroup:
            header = "MERGE"
        else:
            header = self.app.market

        print(f"------------- TODAY : {header} --------------")
        print(trades + " " * (width - len(trades)) + str(len(today_per)))
        print(gains + " " * (width - len(gains)) + today_percent)
        print(aver + " " * (width - len(aver)) + str(today_delta))
        print(success + " " * (width - len(success)) + today_sum)
        print(f"\n-------------- WEEK : {header} --------------")
        print(trades + " " * (width - len(trades)) + str(len(week_per)))
        print(gains + " " * (width - len(gains)) + week_percent)
        print(aver + " " * (width - len(aver)) + str(week_delta))
        print(success + " " * (width - len(success)) + week_sum)
        print(f"\n------------- MONTH : {header} --------------")
        print(trades + " " * (width - len(trades)) + str(len(month_per)))
        print(gains + " " * (width - len(gains)) + month_percent)
        print(aver + " " * (width - len(aver)) + str(month_delta))
        print(success + " " * (width - len(success)) + month_sum)
        print(f"\n------------ ALL TIME : {header} ------------")
        print(trades + " " * (width - len(trades)) + str(len(all_time_per)))
        print(gains + " " * (width - len(gains)) + all_time_percent)
        print(aver + " " * (width - len(aver)) + str(all_time_delta))
        print(success + " " * (width - len(success)) + all_time_sum)
        print("")
        sys.exit()
