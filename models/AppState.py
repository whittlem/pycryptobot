"""Application state class"""
import sys
from datetime import datetime, timedelta
from numpy import array as np_array, min as np_min, ptp as np_ptp

from models.TradingAccount import TradingAccount
from models.exchange.ExchangesEnum import Exchange
from models.exchange.binance import AuthAPI as BAuthAPI
from models.exchange.coinbase import AuthAPI as CBAuthAPI
from models.exchange.coinbase_pro import AuthAPI as CAuthAPI
from models.exchange.kucoin import AuthAPI as KAuthAPI
from views.PyCryptoBot import RichText


class AppState:
    def __init__(self, app, account: TradingAccount) -> None:
        if app.exchange == Exchange.BINANCE:
            self.api = BAuthAPI(
                app.api_key,
                app.api_secret,
                app.api_url,
                recv_window=app.recv_window,
                app=app
            )
        elif app.exchange == Exchange.COINBASE:
            self.api = CBAuthAPI(
                app.api_key,
                app.api_secret,
                app.api_url,
                app=app
            )
        elif app.exchange == Exchange.COINBASEPRO:
            self.api = CAuthAPI(
                app.api_key,
                app.api_secret,
                app.api_passphrase,
                app.api_url,
                app=app
            )
        elif app.exchange == Exchange.KUCOIN:
            self.api = KAuthAPI(
                app.api_key,
                app.api_secret,
                app.api_passphrase,
                app.api_url,
                use_cache=app.usekucoincache,
                app=app
            )
        else:
            self.api = None

        self.app = app
        self.account = account

        self.action = "WAIT"
        self.buy_count = 0
        self.buy_state = ""
        self.buy_sum = 0
        self.eri_text = ""
        self.fib_high = 0
        self.fib_low = 0
        self.first_buy_size = 0
        self.iterations = 0
        self.last_action = "WAIT"
        self.last_buy_size = 0
        self.last_buy_price = 0
        self.last_buy_filled = 0
        self.last_buy_fee = 0
        self.last_buy_high = 0
        self.last_sell_size = 0

        self.previous_buy_size = 0
        self.open_trade_margin = 0
        self.open_trade_margin_float = 0
        self.in_open_trade = False
        self.last_df_index = ""
        self.sell_count = 0
        self.sell_sum = 0

        self.margintracker = 0
        self.profitlosstracker = 0
        self.feetracker = 0
        self.buy_tracker = 0
        self.trade_error_cnt = 0

        self.last_api_call_datetime = datetime.now() - timedelta(
            minutes=2
        )
        self.exchange_last_buy = None

        # setup variables from config that may change
        if app.trailing_stop_loss is not None:
            self.tsl_pcnt = float(app.trailing_stop_loss)
        else:
            self.tsl_pcnt = None
        self.tsl_trigger = app.trailing_stop_loss_trigger

        # automatic & trigger variables
        self.pandas_ta_enabled = False
        self.trading_myPta = False
        self.prevent_loss = False
        self.tsl_max = False
        self.tsl_triggered = False
        self.trailing_buy = False
        self.trailing_buy_immediate = False
        self.waiting_buy_price = 0
        self.trailing_sell = False
        self.trailing_sell_immediate = False
        self.waiting_sell_price = 0
        self.closed_candle_row = -1

    def minimum_order_base(self, base: float = 0.0, balancechk: bool = False):
        self.app.insufficientfunds = False
        if self.app.exchange == Exchange.BINANCE:
            df = self.api.get_market_info_filters(self.app.market)
            if len(df) > 0:
                sys.tracebacklimit = 0
                raise Exception(f"Market not found! ({self.app.market})")

            base = float(base)
            try:
                base_min = float(
                    df[df["filterType"] == "LOT_SIZE"][["minQty"]].values[0][0]
                )
            except Exception:
                base_min = 0.0

        elif self.app.exchange == Exchange.COINBASE:
            product = self.api.auth_api("GET", f"api/v3/brokerage/products/{self.app.market}")
            if len(product) == 0:
                sys.tracebacklimit = 0
                raise Exception(f"Market not found! ({self.app.market})")

            base = float(base)
            try:
                base_min = float(product[["base_min_size"]].values[0])
            except Exception:
                base_min = 0.0

        elif self.app.exchange == Exchange.COINBASEPRO:
            product = self.api.auth_api("GET", f"products/{self.app.market}")
            if len(product) == 0:
                sys.tracebacklimit = 0
                raise Exception(f"Market not found! ({self.app.market})")

            base = float(base)
            try:
                base_min = float(product[["base_min_size"]].values[0])
            except Exception:
                base_min = 0.0

        elif self.app.exchange == Exchange.KUCOIN:
            resp = self.api.auth_api("GET", "api/v1/symbols")
            product = resp[resp["symbol"] == self.app.market]
            if len(product) == 0:
                sys.tracebacklimit = 0
                raise Exception(f"Market not found! ({self.app.market})")

            base = float(base)
            try:
                base_min = float(product["baseMinSize"])
            except Exception:
                base_min = 0.0

        # additional check for last order type
        if balancechk:
            if base > base_min:
                return True
            else:
                return
        elif base < base_min:
            if self.app.enableinsufficientfundslogging:
                self.app.insufficientfunds = True
                RichText.notify(f"Insufficient Base Funds! (Actual: {base}, Minimum: {base_min})", self.app, "warning")
                return

            sys.tracebacklimit = 0
            raise Exception(
                f"Insufficient Base Funds! (Actual: {base}, Minimum: {base_min})"
            )
        else:
            return

    def minimum_order_quote(self, quote: float = 0.0, balancechk: bool = False):
        self.app.insufficientfunds = False
        if self.app.exchange == Exchange.BINANCE:
            df = self.api.get_market_info_filters(self.app.market)

            if len(df) > 0:
                try:
                    quote_min = float(
                        df[df["filterType"] == "NOTIONAL"][["minNotional"]].values[0][0]
                    )
                except Exception:
                    RichText.notify(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Failure detecting minNotional! Using fallback of 10.0", self.app, "error")
                    quote_min = 10.0
                quote = float(quote)

                if quote < quote_min:
                    if self.app.enableinsufficientfundslogging:
                        self.app.insufficientfunds = True

                        RichText.notify(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Insufficient Quote Funds! (Actual: {quote}, Minimum: {quote_min})", self.app, "warning")
                        return

                    sys.tracebacklimit = 0
                    raise Exception(
                        f"Insufficient Quote Funds! (Actual: {quote}, Minimum: {quote_min})"
                    )
                elif balancechk and quote > quote_min:
                    return True
                else:
                    return
            else:
                sys.tracebacklimit = 0
                raise Exception(f"Market not found! ({self.app.market})")

        elif self.app.exchange == Exchange.COINBASE:
            product = self.api.auth_api("GET", f"api/v3/brokerage/products/{self.app.market}")
            if len(product) == 0:
                sys.tracebacklimit = 0
                raise Exception(f"Market not found! ({self.app.market})")
            
            ticker = self.api.get_ticker(self.app.market, None)
            price = float(ticker[1])
            quote = float(quote)
            
            try:
                base_min = float(product[["base_min_size"]].values[0])
            except Exception:
                base_min = 0.0

        elif self.app.exchange == Exchange.COINBASEPRO:
            product = self.api.auth_api("GET", f"products/{self.app.market}")
            if len(product) == 0:
                sys.tracebacklimit = 0
                raise Exception(f"Market not found! ({self.app.market})")

            ticker = self.api.auth_api("GET", f"products/{self.app.market}/ticker")
            price = float(ticker["price"])

            quote = float(quote)
#            base_min = float(product["base_min_size"])
            base_min = float(0)

        elif self.app.exchange == Exchange.KUCOIN:
            resp = self.api.auth_api("GET", "api/v1/symbols")
            product = resp[resp["symbol"] == self.app.market]
            if len(product) == 0:
                sys.tracebacklimit = 0
                raise Exception(f"Market not found! ({self.app.market})")

            ticker = self.api.auth_api(
                "GET", f"api/v1/market/orderbook/level1?symbol={self.app.market}"
            )

            price = float(ticker["price"])
            quote = float(quote)
            base_min = float(product["baseMinSize"])

        # additional check for last order type
        if balancechk:
            if (quote / price) > base_min:
                return True
            else:
                return
        elif quote < self.app.buyminsize:
            if self.app.enableinsufficientfundslogging:
                self.app.insufficientfunds = True
        elif (quote / price) < base_min:
            if self.app.enableinsufficientfundslogging:
                self.app.insufficientfunds = True
                RichText.notify(f'Insufficient Quote Funds! (Actual: {"{:.8f}".format((quote / price))}, Minimum: {base_min})', self.app, "warning")
                return

            sys.tracebacklimit = 0
            raise Exception(
                f'Insufficient Quote Funds! (Actual: {"{:.8f}".format((quote / price))}, Minimum: {base_min})'
            )

    def get_last_order(self):
        # if not live
        if not self.app.is_live:
            self.last_action = "SELL"
            return

        base = 0.0
        quote = 0.0

        ac = self.account.get_balance()
        try:
            df_base = ac[ac["currency"] == self.app.base_currency]["available"]
            base = 0.0 if len(df_base) == 0 else float(df_base.values[0])

            df_quote = ac[ac["currency"] == self.app.quote_currency]["available"]
            quote = 0.0 if len(df_quote) == 0 else float(df_quote.values[0])
        except Exception:
            pass
        orders = self.account.get_orders(self.app.market, "", "done")
        if orders is not None and len(orders) > 0:
            last_order = orders[-1:]

            # if orders exist and last order is a buy
            if str(last_order.action.values[0]) == "buy" and base > 0.0:
                self.last_buy_size = float(
                    last_order[last_order.action == "buy"]["size"]
                )
                self.last_buy_filled = float(
                    last_order[last_order.action == "buy"]["filled"]
                )
                self.last_buy_price = float(
                    last_order[last_order.action == "buy"]["price"]
                )
                self.in_open_trade = True

                # binance orders do not show fees
                if (
                    self.app.exchange == Exchange.COINBASE
                    or self.app.exchange == Exchange.COINBASEPRO
                    or self.app.exchange == Exchange.KUCOIN
                ):
                    self.last_buy_fee = float(
                        last_order[last_order.action == "buy"]["fees"]
                    )

                self.last_action = "BUY"
                return
            else:
                # get last Sell order filled to use as next buy size
                if str(last_order.action.values[0]) == "sell" and quote > 0.0:
                    self.last_sell_size = float(
                        last_order[last_order.action == "sell"]["filled"]
                    ) * float(last_order[last_order.action == "sell"]["price"])
                self.minimum_order_quote(quote)
                self.last_action = "SELL"
                self.last_buy_price = 0.0
                self.in_open_trade = False
                return
        else:
            if quote > 0.0:
                self.minimum_order_quote(quote)
            # nil base or quote funds
            if base == 0.0 and quote == 0.0:
                if self.app.enableinsufficientfundslogging:
                    self.app.insufficientfunds = True
                    RichText.notify(f"Insufficient Funds! ({self.app.base_currency}={str(base)}, {self.app.quote_currency}={str(base)})", self.app, "warning")
                    self.last_action = "WAIT"
                    return

                sys.tracebacklimit = 0
                raise Exception(
                    f"Insufficient Funds! ({self.app.base_currency}={str(base)}, {self.app.quote_currency}={str(base)})"
                )

            # determine last action by comparing normalised [0,1] base and quote balances
            order_pairs = np_array([base, quote])
            order_pairs_normalised = (order_pairs - np_min(order_pairs)) / np_ptp(
                order_pairs
            )

            # If multi buy check enabled for pair, check balances to prevent multiple buys
            if (
                self.app.marketmultibuycheck
                and self.minimum_order_base(base, balancechk=True)
                and self.minimum_order_quote(quote, balancechk=True)
            ):
                self.last_action = "BUY"
                RichText.notify(f"Market - {self.app.market} did not return order info, but looks like there was a already a buy. Set last action to buy", self.app, "warning")
            elif order_pairs_normalised[0] < order_pairs_normalised[1]:
                self.minimum_order_quote(quote)
                self.last_action = "SELL"
            elif order_pairs_normalised[0] > order_pairs_normalised[1]:
                self.minimum_order_base(base)
                self.last_action = "BUY"
            else:
                self.last_action = "WAIT"

            return

    def init_last_action(self):
        # ignore if manually set
        if self.app.last_action is not None:
            self.last_action = self.app.last_action
            return

        self.get_last_order()

    def poll_last_action(self):
        self.get_last_order()
