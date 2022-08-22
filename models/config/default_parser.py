import re
from enum import Enum
from datetime import datetime
from xmlrpc.client import Boolean

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
    if "live" in config:
        if isinstance(config["live"], int):
            if config["live"] in [0, 1]:
                app.is_live = config["live"]
        else:
            raise TypeError("live must be of type int")

    if "verbose" in config:
        if isinstance(config["verbose"], int):
            if config["verbose"] in [0, 1]:
                app.is_verbose = config["verbose"]
        else:
            raise TypeError("verbose must be of type int")

    if "graphs" in config:
        if isinstance(config["graphs"], int):
            if config["graphs"] in [0, 1]:
                app.save_graphs = config["graphs"]
        else:
            raise TypeError("graphs must be of type int")

    if "sim" in config:
        if isinstance(config["sim"], str):
            if config["sim"] in ["slow", "fast"]:
                app.is_live = 0
                app.is_sim = 1
                app.sim_speed = config["sim"]

            if config["sim"] in ["slow-sample", "fast-sample"]:
                app.is_live = 0
                app.is_sim = 1
                app.sim_speed = config["sim"]
                if "simstartdate" in config:
                    app.simstartdate = config["simstartdate"]
                if "simenddate" in config:
                    app.simenddate = config["simenddate"]
        else:
            raise TypeError("sim must be of type str")

    if "stats" in config:
        if isinstance(config["stats"], int):
            if bool(config["stats"]):
                app.stats = True
                if "statgroup" in config:
                    app.statgroup = config["statgroup"]
                if "statstartdate" in config:
                    app.statstartdate = config["statstartdate"]
                if "statdetail" in config:
                    app.statdetail = config["statdetail"]
        else:
            raise TypeError("stats must be of type int")

    if "simresultonly" in config:
        if isinstance(config["simresultonly"], int):
            if bool(config["simresultonly"]):
                app.simresultonly = True
        else:
            raise TypeError("simresultonly must be of type int")

    if "enable_telegram_bot_control" in config:
        if isinstance(config["enable_telegram_bot_control"], int):
            if config["enable_telegram_bot_control"] in [0, 1]:
                app.enable_telegram_bot_control = bool(config["enable_telegram_bot_control"])
        else:
            raise TypeError("enable_telegram_bot_control must be of type int")

    if "smartswitch" in config:
        if isinstance(config["smartswitch"], int):
            if config["smartswitch"] in [0, 1]:
                app.smart_switch = config["smartswitch"]
                if app.smart_switch == 1:
                    app.smart_switch = 1
                else:
                    app.smart_switch = 0
        else:
            raise TypeError("smartswitch must be of type int")

    if "buypercent" in config:
        if isinstance(config["buypercent"], int):
            if config["buypercent"] > 0 and config["buypercent"] <= 100:
                app.buypercent = config["buypercent"]
        else:
            raise TypeError("buypercent must be of type int")

    if "sellpercent" in config:
        if isinstance(config["sellpercent"], int):
            if config["sellpercent"] > 0 and config["sellpercent"] <= 100:
                app.sellpercent = config["sellpercent"]
        else:
            raise TypeError("sellpercent must be of type int")

    if "lastaction" in config:
        if isinstance(config["lastaction"], str):
            if config["lastaction"] in ["BUY", "SELL"]:
                app.last_action = config["lastaction"]
        else:
            raise TypeError("lastaction must be of type str")

    if "granularity" in config and config["granularity"] is not None:
        app.smart_switch = 0
        if isinstance(config["granularity"], str) and not config["granularity"].isnumeric() is True:
            app.granularity = Granularity.convert_to_enum(config["granularity"])
        else:
            app.granularity = Granularity.convert_to_enum(int(config["granularity"]))

    if "usekucoincache" in config:
        if isinstance(config["usekucoincache"], int):
            if bool(config["usekucoincache"]):
                app.usekucoincache = True
        else:
            raise TypeError("usekucoincache must be of type int")

    def config_option_int(
        option_name: str = None, option_default: int = 0, store_name: str = None, value_min: int = None, value_max: int = None
    ) -> bool:
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

    def config_option_str(
        option_name: str = None, option_default: str = "", store_name: str = None, valid_options: list = []
    ) -> bool:
        if option_name is None or store_name is None:
            return False

        if store_name in config:
            option_name = store_name  # prefer legacy config if it exists

        if option_name in config:
            if isinstance(config[option_name], str):
                if config[option_name] in valid_options:
                    setattr(app, store_name, config[option_name])
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
                    setattr(app, store_name, str(datetime.today().strftime('%Y-%m-%d')))
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

    config_option_int(option_name="live", option_default=0, store_name="is_live", value_min=0, value_max=1)

    config_option_date(option_name="simstartdate", option_default=None, store_name="simstartdate", date_format="%Y-%m-%d", allow_now=False)
    config_option_date(option_name="simenddate", option_default=None, store_name="simenddate", date_format="%Y-%m-%d", allow_now=True)

    config_option_bool(option_name="telegram", option_default=False, store_name="disabletelegram", store_invert=True)
    config_option_bool(option_name="telegramtradesonly", option_default=False, store_name="telegramtradesonly", store_invert=False)
    config_option_bool(option_name="telegramerrormsgs", option_default=False, store_name="disabletelegramerrormsgs", store_invert=True)

    config_option_bool(option_name="log", option_default=True, store_name="disablelog", store_invert=True)
    config_option_bool(option_name="tradetracker", option_default=False, store_name="disabletracker", store_invert=True)
    config_option_bool(option_name="autorestart", option_default=False, store_name="autorestart", store_invert=False)
    config_option_bool(option_name="websocket", option_default=False, store_name="websocket", store_invert=False)
    config_option_bool(option_name="insufficientfundslogging", option_default=False, store_name="enableinsufficientfundslogging", store_invert=False)
    config_option_bool(option_name="logbuysellinjson", option_default=False, store_name="logbuysellinjson", store_invert=False)
    config_option_bool(option_name="manualtradesonly", option_default=False, store_name="manual_trades_only", store_invert=False)
    config_option_bool(option_name="predictions", option_default=False, store_name="enableml", store_invert=False)
    config_option_str(option_name="startmethod", option_default="standard", store_name="startmethod", valid_options=["standard", "telegram"])
    config_option_int(option_name="recvwindow", option_default=5000, store_name="recv_window", value_min=5000, value_max=60000)

    config_option_int(option_name="adjusttotalperiods", option_default=300, store_name="adjusttotalperiods", value_min=200, value_max=500)

    config_option_float(option_name="sellupperpcnt", option_default=None, store_name="sell_upper_pcnt", value_min=0, value_max=100)
    config_option_float(option_name="selllowerpcnt", option_default=None, store_name="sell_lower_pcnt", value_min=-100, value_max=0)
    config_option_float(option_name="nosellmaxpcnt", option_default=None, store_name="nosellmaxpcnt", value_min=0, value_max=100)
    config_option_float(option_name="nosellminpcnt", option_default=None, store_name="nosellminpcnt", value_min=-100, value_max=0)

    config_option_bool(option_name="preventloss", option_default=False, store_name="preventloss", store_invert=False)
    config_option_float(option_name="preventlosstrigger", option_default=1.0, store_name="nobuynearhighpcnt", value_min=0, value_max=100)
    config_option_float(option_name="preventlossmargin", option_default=0.1, store_name="nobuynearhighpcnt", value_min=0, value_max=100)
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
