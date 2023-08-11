import re
from enum import Enum
from datetime import datetime
from xmlrpc.client import Boolean
from os import get_terminal_size

from models.exchange.ExchangesEnum import Exchange
from models.exchange.Granularity import Granularity


def merge_config_and_args(exchange_config, args):
    new_config = {}
    if "config" in exchange_config and exchange_config["config"] is not None:
        new_config = {**exchange_config["config"]}
    for (key, value) in args.items():
        if value is not None and value is not False:
            new_config[key] = value
    return new_config


def is_currency_valid(currency):
    p = re.compile(r"^[0-9A-Z]{1,20}$")
    return p.match(currency)


def default_config_parse(app, config):
    """
    Requirements for bot options:
    - Update _generate_banner() in controllers/PyCryptoBot.py
    - Update the command line arguments below
    - Update the config parser in models/config/default_parser.py
    """

    def config_option_int(option_name: str = None, option_default: int = 0, store_name: str = None, value_min: int = None, value_max: int = None) -> bool:
        if option_name is None or store_name is None:
            return False

        if store_name in config:
            option_name = store_name  # prefer legacy config if it exists

        if option_name in config:
            if isinstance(config[option_name], int):
                if value_min is not None and value_max is not None:
                    if config[option_name] >= value_min and config[option_name] <= value_max:
                        setattr(app, store_name, int(config[option_name]))
                    else:
                        raise TypeError(f"{option_name} is out of bounds")
                else:
                    setattr(app, store_name, int(config[option_name]))
            else:
                raise TypeError(f"{option_name} must be a number")
        else:
            setattr(app, store_name, option_default)  # default

        return True

    def config_option_float(
        option_name: str = None, option_default: float = 0.0, store_name: str = None, value_min: float = None, value_max: float = None
    ) -> bool:
        if option_name is None or store_name is None:
            return False

        if store_name in config:
            option_name = store_name  # prefer legacy config if it exists

        if option_name in config:
            if isinstance(config[option_name], int) or isinstance(config[option_name], float):
                if value_min is not None and value_max is not None:
                    if config[option_name] >= value_min and config[option_name] <= value_max:
                        setattr(app, store_name, float(config[option_name]))
                    else:
                        raise TypeError(f"{option_name} is out of bounds")
                else:
                    setattr(app, store_name, float(config[option_name]))
            else:
                raise TypeError(f"{option_name} must be a number")
        else:
            setattr(app, store_name, option_default)  # default

        return True

    def config_option_bool(option_name: str = None, option_default: bool = True, store_name: str = None, store_invert: bool = False) -> bool:
        if option_name is None or store_name is None:
            return False

        if store_name in config:
            option_name = store_name  # prefer legacy config if it exists
            store_invert = False  # legacy config does not need to be inverted

        if option_name in config:
            if isinstance(config[option_name], int):
                if config[option_name] in [0, 1]:
                    if store_invert is True:
                        setattr(app, store_name, bool(not config[option_name]))
                    else:
                        setattr(app, store_name, bool(config[option_name]))
            else:
                raise TypeError(f"{option_name} must be of type int (0 or 1)")
        else:
            if store_invert is True:
                setattr(app, store_name, (not option_default))  # default (if inverted - disabled)
            else:
                setattr(app, store_name, option_default)  # default

        return True

    import sys

    def config_option_list(option_name: str = None, option_default: str = "", store_name: str = None) -> bool:
        if option_name is None or store_name is None:
            return False

        if store_name in config:
            option_name = store_name  # prefer legacy config if it exists

        if option_name in config:
            if isinstance(config[option_name], list):
                setattr(app, store_name, config[option_name])
            else:
                raise TypeError(f"{option_name} must be a list")
        else:
            setattr(app, store_name, option_default)  # default

        return True

    def config_option_str(option_name: str = None, option_default: str = "", store_name: str = None, valid_options: list = [], disable_variable=None) -> bool:
        if option_name is None or store_name is None:
            return False

        if store_name in config:
            option_name = store_name  # prefer legacy config if it exists

        if option_name in config:
            if isinstance(config[option_name], str):
                if config[option_name] in valid_options:
                    setattr(app, store_name, config[option_name])

                    if disable_variable is not None:
                        setattr(app, disable_variable, 0)
                else:
                    raise TypeError(f"{option_name} is not a valid option")
            else:
                raise TypeError(f"{option_name} must be a string")
        else:
            setattr(app, store_name, option_default)  # default

        return True

    def config_option_date(
        option_name: str = None, option_default: str = "", store_name: str = None, date_format: str = "%Y-%m-%d", allow_now: bool = False
    ) -> bool:
        if option_name is None or store_name is None:
            return False

        if store_name in config:
            option_name = store_name  # prefer legacy config if it exists

        if option_name in config:
            if isinstance(config[option_name], str):
                if allow_now is True and config[option_name] == "now":
                    setattr(app, store_name, str(datetime.today().strftime("%Y-%m-%d")))
                else:
                    try:
                        datetime.strptime(config[option_name], date_format)
                    except ValueError:
                        raise ValueError(f"Incorrect data format, should be {date_format}")

                    setattr(app, store_name, str(config[option_name]))
            else:
                raise TypeError(f"{option_name} must be a date: {date_format}")
        else:
            setattr(app, store_name, option_default)  # default

        return True

    # bespoke options with non-standard logic

    if "market" in config and config["market"] is not None:
        if app.exchange == Exchange.BINANCE:
            p = re.compile(r"^[0-9A-Z]{4,25}$")
            if p.match(config["market"]):
                app.market = config["market"]
            else:
                # default market for Binance
                app.market = "BTCGBP"
        else:
            if app.exchange != Exchange.COINBASE and app.exchange != Exchange.COINBASEPRO and app.exchange != Exchange.KUCOIN:
                # default if no exchange set
                app.exchange = Exchange.COINBASEPRO

            # binance and kucoin
            p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
            if p.match(config["market"]):
                app.market = config["market"]
            else:
                # default for coinbase pro and binance
                app.market = "BTC-GBP"

    if "granularity" in config and config["granularity"] is not None:
        app.smart_switch = 0
        if isinstance(config["granularity"], str) and not config["granularity"].isnumeric() is True:
            app.granularity = Granularity.convert_to_enum(config["granularity"])
        else:
            app.granularity = Granularity.convert_to_enum(int(config["granularity"]))

    # standard options

    try:
        term_width = get_terminal_size().columns
    except OSError:
        term_width = 180

    config_option_bool(option_name="debug", option_default=False, store_name="debug", store_invert=False)

    config_option_bool(option_name="termcolor", option_default=True, store_name="term_color", store_invert=False)
    config_option_int(option_name="termwidth", option_default=term_width, store_name="term_width", value_min=60, value_max=420)
    config_option_int(option_name="logwidth", option_default=180, store_name="log_width", value_min=60, value_max=420)

    config_option_bool(option_name="live", option_default=False, store_name="is_live", store_invert=False)
    config_option_bool(option_name="graphs", option_default=False, store_name="save_graphs", store_invert=False)

    config_option_str(
        option_name="sim", option_default=0, store_name="is_sim", valid_options=["slow", "fast", "slow-sample", "fast-sample"], disable_variable="is_live"
    )
    config_option_date(option_name="simstartdate", option_default=None, store_name="simstartdate", date_format="%Y-%m-%d", allow_now=False)
    config_option_date(option_name="simenddate", option_default=None, store_name="simenddate", date_format="%Y-%m-%d", allow_now=True)
    config_option_bool(option_name="simresultonly", option_default=False, store_name="simresultonly", store_invert=False)

    config_option_bool(option_name="telegram", option_default=False, store_name="disabletelegram", store_invert=True)
    config_option_bool(option_name="telegrambotcontrol", option_default=False, store_name="telegrambotcontrol", store_invert=False)
    config_option_bool(option_name="telegramtradesonly", option_default=False, store_name="telegramtradesonly", store_invert=False)
    config_option_bool(option_name="telegramerrormsgs", option_default=False, store_name="disabletelegramerrormsgs", store_invert=True)

    config_option_bool(option_name="stats", option_default=False, store_name="stats", store_invert=False)
    config_option_list(option_name="statgroup", option_default="", store_name="statgroup")
    config_option_date(option_name="statstartdate", option_default=None, store_name="statstartdate", date_format="%Y-%m-%d", allow_now=False)
    config_option_bool(option_name="statdetail", option_default=False, store_name="statdetail", store_invert=False)

    config_option_bool(option_name="log", option_default=True, store_name="disablelog", store_invert=True)
    config_option_bool(option_name="smartswitch", option_default=False, store_name="smart_switch", store_invert=False)
    config_option_bool(option_name="tradetracker", option_default=False, store_name="disabletracker", store_invert=True)
    config_option_bool(option_name="autorestart", option_default=False, store_name="autorestart", store_invert=False)
    config_option_bool(option_name="websocket", option_default=False, store_name="websocket", store_invert=False)
    config_option_bool(option_name="insufficientfundslogging", option_default=False, store_name="enableinsufficientfundslogging", store_invert=False)
    config_option_bool(option_name="logbuysellinjson", option_default=False, store_name="logbuysellinjson", store_invert=False)
    config_option_bool(option_name="manualtradesonly", option_default=False, store_name="manual_trades_only", store_invert=False)
    config_option_str(option_name="startmethod", option_default="standard", store_name="startmethod", valid_options=["scanner", "standard", "telegram"])
    config_option_int(option_name="recvwindow", option_default=5000, store_name="recv_window", value_min=5000, value_max=60000)
    config_option_str(option_name="lastaction", option_default=None, store_name="last_action", valid_options=["BUY", "SELL"])
    config_option_bool(option_name="kucoincache", option_default=False, store_name="usekucoincache", store_invert=False)
    config_option_bool(option_name="exitaftersell", option_default=False, store_name="exitaftersell", store_invert=False)

    config_option_int(option_name="adjusttotalperiods", option_default=300, store_name="adjusttotalperiods", value_min=200, value_max=500)

    config_option_float(option_name="buypercent", option_default=100, store_name="buypercent", value_min=0, value_max=100)
    config_option_float(option_name="sellpercent", option_default=100, store_name="sellpercent", value_min=0, value_max=100)

    config_option_float(option_name="sellupperpcnt", option_default=None, store_name="sell_upper_pcnt", value_min=0, value_max=100)
    config_option_float(option_name="selllowerpcnt", option_default=None, store_name="sell_lower_pcnt", value_min=-100, value_max=0)
    config_option_float(option_name="nosellmaxpcnt", option_default=None, store_name="nosellmaxpcnt", value_min=0, value_max=100)
    config_option_float(option_name="nosellminpcnt", option_default=None, store_name="nosellminpcnt", value_min=-100, value_max=0)

    config_option_bool(option_name="preventloss", option_default=False, store_name="preventloss", store_invert=False)
    config_option_float(option_name="preventlosstrigger", option_default=1.0, store_name="preventlosstrigger", value_min=0, value_max=100)
    config_option_float(option_name="preventlossmargin", option_default=0.1, store_name="preventlossmargin", value_min=0, value_max=100)
    config_option_bool(option_name="sellatloss", option_default=True, store_name="sellatloss", store_invert=False)

    config_option_bool(option_name="sellatresistance", option_default=False, store_name="sellatresistance", store_invert=False)
    config_option_bool(option_name="sellatfibonaccilow", option_default=False, store_name="disablefailsafefibonaccilow", store_invert=True)
    config_option_bool(option_name="bullonly", option_default=False, store_name="disablebullonly", store_invert=True)
    config_option_bool(option_name="profitbankreversal", option_default=False, store_name="disableprofitbankreversal", store_invert=True)

    config_option_float(option_name="trailingstoploss", option_default=0.0, store_name="trailing_stop_loss", value_min=-100, value_max=0)
    config_option_float(option_name="trailingstoplosstrigger", option_default=0.0, store_name="trailing_stop_loss_trigger", value_min=0, value_max=100)
    config_option_float(option_name="trailingsellpcnt", option_default=0.0, store_name="trailingsellpcnt", value_min=-100, value_max=0)
    config_option_bool(option_name="trailingimmediatesell", option_default=False, store_name="trailingimmediatesell", store_invert=False)
    config_option_float(option_name="trailingsellimmediatepcnt", option_default=0.0, store_name="trailingsellimmediatepcnt", value_min=-100, value_max=0)
    config_option_float(option_name="trailingsellbailoutpcnt", option_default=0.0, store_name="trailingsellbailoutpcnt", value_min=-100, value_max=100)

    config_option_bool(option_name="dynamictsl", option_default=False, store_name="dynamic_tsl", store_invert=False)
    config_option_float(option_name="tslmultiplier", option_default=1.1, store_name="tsl_multiplier", value_min=0, value_max=100)
    config_option_float(option_name="tsltriggermultiplier", option_default=1.1, store_name="tsl_trigger_multiplier", value_min=0, value_max=100)
    config_option_float(option_name="tslmaxpcnt", option_default=-5.0, store_name="tsl_max_pcnt", value_min=-100, value_max=0)

    config_option_float(option_name="buyminsize", option_default=0.0, store_name="buyminsize")
    config_option_float(option_name="buymaxsize", option_default=0.0, store_name="buymaxsize")
    config_option_bool(option_name="buylastsellsize", option_default=False, store_name="buylastsellsize", store_invert=False)
    config_option_bool(option_name="marketmultibuycheck", option_default=False, store_name="marketmultibuycheck", store_invert=False)
    config_option_bool(option_name="buynearhigh", option_default=True, store_name="disablebuynearhigh", store_invert=True)
    config_option_float(option_name="buynearhighpcnt", option_default=3.0, store_name="nobuynearhighpcnt", value_min=0, value_max=100)

    config_option_float(option_name="trailingbuypcnt", option_default=0.0, store_name="trailingbuypcnt", value_min=0, value_max=100)
    config_option_bool(option_name="trailingimmediatebuy", option_default=False, store_name="trailingimmediatebuy", store_invert=False)
    config_option_float(option_name="trailingbuyimmediatepcnt", option_default=0.0, store_name="trailingbuyimmediatepcnt", value_min=0, value_max=100)

    config_option_bool(option_name="selltriggeroverride", option_default=False, store_name="selltriggeroverride", store_invert=False)

    config_option_bool(option_name="ema1226", option_default=True, store_name="disablebuyema", store_invert=True)
    config_option_bool(option_name="macdsignal", option_default=True, store_name="disablebuymacd", store_invert=True)
    config_option_bool(option_name="obv", option_default=False, store_name="disablebuyobv", store_invert=True)
    config_option_bool(option_name="elderray", option_default=False, store_name="disablebuyelderray", store_invert=True)
    config_option_bool(option_name="bbands_s1", option_default=False, store_name="disablebuybbands_s1", store_invert=True)
    config_option_bool(option_name="bbands_s2", option_default=False, store_name="disablebuybbands_s2", store_invert=True)
