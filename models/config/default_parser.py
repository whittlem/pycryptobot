import re

from models.exchange.Granularity import Granularity


def merge_config_and_args(exchange_config, args):
    new_config = {}
    if "config" in exchange_config and exchange_config["config"] is not None:
        new_config = {**exchange_config["config"]}
    for (key, value) in args.items():
        if value is not None and value is not False:
            new_config[key] = value
    return new_config


def isCurrencyValid(currency):
    p = re.compile(r"^[0-9A-Z]{1,20}$")
    return p.match(currency)


def defaultConfigParse(app, config):
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

    if "nobuynearhighpcnt" in config:
        if isinstance(config["nobuynearhighpcnt"], (int, float, str)):
            p = re.compile(r"^\-*[0-9\.]{1,5}$")
            if isinstance(config["nobuynearhighpcnt"], str) and p.match(
                config["nobuynearhighpcnt"]
            ):
                if float(config["nobuynearhighpcnt"]) > 0:
                    app.nobuynearhighpcnt = float(config["nobuynearhighpcnt"])
                else:
                    raise ValueError("nobuynearhighpcnt must be positive")
            elif (
                isinstance(config["nobuynearhighpcnt"], (int, float))
                and config["nobuynearhighpcnt"] >= 0
                and config["nobuynearhighpcnt"] <= 100
            ):
                if float(config["nobuynearhighpcnt"]) > 0:
                    app.nobuynearhighpcnt = float(config["nobuynearhighpcnt"])
                else:
                    raise ValueError("nobuynearhighpcnt must be positive")
            elif (
                isinstance(config["nobuynearhighpcnt"], (int, float))
                and config["nobuynearhighpcnt"] < 0
            ):
                raise ValueError("nobuynearhighpcnt must be positive")
        else:
            raise TypeError("nobuynearhighpcnt must be of type int or str")

    if "sellupperpcnt" in config:
        if isinstance(config["sellupperpcnt"], (int, float, str)):
            p = re.compile(r"^\-*[0-9\.]{1,5}$")
            if isinstance(config["sellupperpcnt"], str) and p.match(
                config["sellupperpcnt"]
            ):
                if float(config["sellupperpcnt"]) > 0:
                    app.sell_upper_pcnt = float(config["sellupperpcnt"])
                else:
                    raise ValueError("sellupperpcnt must be positive")
            elif (
                isinstance(config["sellupperpcnt"], (int, float))
                and config["sellupperpcnt"] >= 0
                and config["sellupperpcnt"] <= 100
            ):
                if float(config["sellupperpcnt"]) > 0:
                    app.sell_upper_pcnt = float(config["sellupperpcnt"])
                else:
                    raise ValueError("sellupperpcnt must be positive")
            elif (
                isinstance(config["sellupperpcnt"], (int, float))
                and config["sellupperpcnt"] < 0
            ):
                raise ValueError("sellupperpcnt must be positive")
        else:
            raise TypeError("sellupperpcnt must be of type int or str")

    if "selllowerpcnt" in config:
        if isinstance(config["selllowerpcnt"], (int, float, str)):
            p = re.compile(r"^\-*[0-9\.]{1,5}$")
            if isinstance(config["selllowerpcnt"], str) and p.match(
                config["selllowerpcnt"]
            ):
                if float(config["selllowerpcnt"]) < 0:
                    app.sell_lower_pcnt = float(config["selllowerpcnt"])
                else:
                    raise ValueError("selllowerpcnt must be negative")
            elif (
                isinstance(config["selllowerpcnt"], (int, float))
                and config["selllowerpcnt"] >= -100
                and config["selllowerpcnt"] <= 0
            ):
                if float(config["selllowerpcnt"]) < 0:
                    app.sell_lower_pcnt = float(config["selllowerpcnt"])
                else:
                    raise ValueError("selllowerpcnt must be negative")
            elif (
                isinstance(config["selllowerpcnt"], (int, float))
                and config["selllowerpcnt"] >= 0
            ):
                raise ValueError("selllowerpcnt must be negative")
        else:
            raise TypeError("selllowerpcnt must be of type int or str")

    if "nosellmaxpcnt" in config:
        if isinstance(config["nosellmaxpcnt"], (int, float, str)):
            p = re.compile(r"^\-*[0-9\.]{1,5}$")
            if isinstance(config["nosellmaxpcnt"], str) and p.match(
                config["nosellmaxpcnt"]
            ):
                if float(config["nosellmaxpcnt"]) > 0:
                    app.nosellmaxpcnt = float(config["nosellmaxpcnt"])
                else:
                    raise ValueError("nosellmaxpcnt must be positive")
            elif (
                isinstance(config["nosellmaxpcnt"], (int, float))
                and config["nosellmaxpcnt"] >= 0
                and config["nosellmaxpcnt"] <= 100
            ):
                if float(config["nosellmaxpcnt"]) > 0:
                    app.nosellmaxpcnt = float(config["nosellmaxpcnt"])
                else:
                    raise ValueError("nosellmaxpcnt must be positive")
            elif (
                isinstance(config["nosellmaxpcnt"], (int, float))
                and config["nosellmaxpcnt"] < 0
            ):
                raise ValueError("nosellmaxpcnt must be positive")
        else:
            raise TypeError("nosellmaxpcnt must be of type int or str")

    if "nosellminpcnt" in config:
        if isinstance(config["nosellminpcnt"], (int, float, str)):
            p = re.compile(r"^\-*[0-9\.]{1,5}$")
            if isinstance(config["nosellminpcnt"], str) and p.match(
                config["nosellminpcnt"]
            ):
                if float(config["nosellminpcnt"]) < 0:
                    app.nosellminpcnt = float(config["nosellminpcnt"])
                else:
                    raise ValueError("nosellminpcnt must be negative")
            elif (
                isinstance(config["nosellminpcnt"], (int, float))
                and config["nosellminpcnt"] >= -100
                and config["nosellminpcnt"] <= 0
            ):
                if float(config["nosellminpcnt"]) < 0:
                    app.nosellminpcnt = float(config["nosellminpcnt"])
                else:
                    raise ValueError("nosellminpcnt must be negative")
            elif (
                isinstance(config["nosellminpcnt"], (int, float))
                and config["nosellminpcnt"] >= 0
            ):
                raise ValueError("nosellminpcnt must be negative")
        else:
            raise TypeError("nosellminpcnt must be of type int or str")

    if "trailingstoploss" in config:
        if isinstance(config["trailingstoploss"], (int, float, str)):
            p = re.compile(r"^\-*[0-9\.]{1,5}$")
            if isinstance(config["trailingstoploss"], str) and p.match(
                config["trailingstoploss"]
            ):
                if float(config["trailingstoploss"]) < 0:
                    app.trailing_stop_loss = float(config["trailingstoploss"])
                else:
                    raise ValueError("trailingstoploss must be negative")
            elif (
                isinstance(config["trailingstoploss"], (int, float))
                and config["trailingstoploss"] >= -100
                and config["trailingstoploss"] <= 0
            ):
                if float(config["trailingstoploss"]) < 0:
                    app.trailing_stop_loss = float(config["trailingstoploss"])
                else:
                    raise ValueError("trailingstoploss must be negative")
            elif (
                isinstance(config["trailingstoploss"], (int, float))
                and config["trailingstoploss"] >= 0
            ):
                raise ValueError("trailingstoploss must be negative")
        else:
            raise TypeError("trailingstoploss must be of type int or str")

    if "trailingstoplosstrigger" in config:
        if isinstance(config["trailingstoplosstrigger"], (int, float, str)):
            p = re.compile(r"^\-*[0-9\.]{1,5}$")
            if isinstance(config["trailingstoplosstrigger"], str) and p.match(
                config["trailingstoplosstrigger"]
            ):
                if float(config["trailingstoplosstrigger"]) >= 0:
                    app.trailing_stop_loss_trigger = float(
                        config["trailingstoplosstrigger"]
                    )
                else:
                    raise ValueError("trailingstoplosstrigger must be positive")
            elif (
                isinstance(config["trailingstoplosstrigger"], (int, float))
                and config["trailingstoplosstrigger"] >= 0
                and config["trailingstoplosstrigger"] <= 100
            ):
                if float(config["trailingstoplosstrigger"]) >= 0:
                    app.trailing_stop_loss_trigger = float(
                        config["trailingstoplosstrigger"]
                    )
                else:
                    raise ValueError("trailingstoplosstrigger must be positive")
            elif (
                isinstance(config["trailingstoplosstrigger"], (int, float))
                and config["trailingstoplosstrigger"] <= 0
            ):
                raise ValueError("trailingstoplosstrigger must be positive")
        else:
            raise TypeError("trailingstoplosstrigger must be of type int or str")

    if "autorestart" in config:
        if isinstance(config["autorestart"], int):
            if config["autorestart"] in [0, 1]:
                app.autorestart = bool(config["autorestart"])
        else:
            raise TypeError("autorestart must be of type int")

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

    if "sellatloss" in config:
        if isinstance(config["sellatloss"], int):
            if config["sellatloss"] in [0, 1]:
                app.sell_at_loss = config["sellatloss"]
                if app.sell_at_loss == 0:
                    app.sell_lower_pcnt = None
        else:
            raise TypeError("sellatloss must be of type int")

    if "simresultonly" in config:
        if isinstance(config["simresultonly"], int):
            if bool(config["simresultonly"]):
                app.simresultonly = True
        else:
            raise TypeError("simresultonly must be of type int")

    if "sellatresistance" in config:
        if isinstance(config["sellatresistance"], int):
            if config["sellatresistance"] in [0, 1]:
                app.sellatresistance = bool(config["sellatresistance"])
        else:
            raise TypeError("sellatresistance must be of type int")

    if "disablebullonly" in config:
        if isinstance(config["disablebullonly"], int):
            if bool(config["disablebullonly"]):
                app.disablebullonly = True
        else:
            raise TypeError("disablebullonly must be of type int")

    if "disablebuynearhigh" in config:
        if isinstance(config["disablebuynearhigh"], int):
            if bool(config["disablebuynearhigh"]):
                app.disablebuynearhigh = True
        else:
            raise TypeError("disablebuynearhigh must be of type int")

    if "disablebuymacd" in config:
        if isinstance(config["disablebuymacd"], int):
            if bool(config["disablebuymacd"]):
                app.disablebuymacd = True
        else:
            raise TypeError("disablebuymacd must be of type int")

    if "disablebuyema" in config:
        if isinstance(config["disablebuyema"], int):
            if bool(config["disablebuyema"]):
                app.disablebuyema = True
        else:
            raise TypeError("disablebuyema must be of type int")

    if "disablebuyobv" in config:
        if isinstance(config["disablebuyobv"], int):
            if bool(config["disablebuyobv"]):
                app.disablebuyobv = True
        else:
            raise TypeError("disablebuyobv must be of type int")

    if "disablebuyelderray" in config:
        if isinstance(config["disablebuyelderray"], int):
            if bool(config["disablebuyelderray"]):
                app.disablebuyelderray = True
        else:
            raise TypeError("disablebuyelderray must be of type int")

    if "disablefailsafefibonaccilow" in config:
        if isinstance(config["disablefailsafefibonaccilow"], int):
            if bool(config["disablefailsafefibonaccilow"]):
                app.disablefailsafefibonaccilow = True
        else:
            raise TypeError("disablefailsafefibonaccilow must be of type int")

    if "disablefailsafelowerpcnt" in config:
        if isinstance(config["disablefailsafelowerpcnt"], int):
            if bool(config["disablefailsafelowerpcnt"]):
                app.disablefailsafelowerpcnt = True
        else:
            raise TypeError("disablefailsafelowerpcnt must be of type int")

    if "disableprofitbankupperpcnt" in config:
        if isinstance(config["disableprofitbankupperpcnt"], int):
            if bool(config["disableprofitbankupperpcnt"]):
                app.disableprofitbankupperpcnt = True
        else:
            raise TypeError("disableprofitbankupperpcnt must be of type int")

    if "disableprofitbankreversal" in config:
        if isinstance(config["disableprofitbankreversal"], int):
            if bool(config["disableprofitbankreversal"]):
                app.disableprofitbankreversal = True
        else:
            raise TypeError("disableprofitbankreversal must be of type int")

    if "disabletelegram" in config:
        if isinstance(config["disabletelegram"], int):
            if bool(config["disabletelegram"]):
                app.disabletelegram = True
        else:
            raise TypeError("disabletelegram must be of type int")

    if "telegramtradesonly" in config:
        if isinstance(config["telegramtradesonly"], int):
            if bool(config["telegramtradesonly"]):
                app.telegramtradesonly = True
        else:
            raise TypeError("telegramtradesonly must be of type int")

    if "disabletelegramerrormsgs" in config:
        if isinstance(config["disabletelegramerrormsgs"], int):
            if bool(config["disabletelegramerrormsgs"]):
                app.disabletelegramerrormsgs = True
        else:
            raise TypeError("disabletelegramerrormsgs must be of type int")

    if "disablelog" in config:
        if isinstance(config["disablelog"], int):
            if bool(config["disablelog"]):
                app.disablelog = True
        else:
            raise TypeError("disablelog must be of type int")

    if "disabletracker" in config:
        if isinstance(config["disabletracker"], int):
            if bool(config["disabletracker"]):
                app.disabletracker = True
        else:
            raise TypeError("disabletracker must be of type int")

    if "enableml" in config:
        if isinstance(config["enableml"], int):
            if bool(config["enableml"]):
                app.enableml = True
        else:
            raise TypeError("enableml must be of type int")

    if "websocket" in config:
        if isinstance(config["websocket"], int):
            if bool(config["websocket"]):
                app.websocket = True
        else:
            raise TypeError("websocket must be of type int")

    if "enableinsufficientfundslogging" in config:
        if isinstance(config["enableinsufficientfundslogging"], int):
            if bool(config["enableinsufficientfundslogging"]):
                app.enableinsufficientfundslogging = True
        else:
            raise TypeError("enableinsufficientfundslogging must be of type int")

    if "enabletelegrambotcontrol" in config:
        if isinstance(config["enabletelegrambotcontrol"], int):
            if bool(config["enabletelegrambotcontrol"]):
                app.enabletelegrambotcontrol = True
        else:
            raise TypeError("enabletelegrambotcontrol must be of type int")

    if "enableimmediatebuy" in config:
        if isinstance(config["enableimmediatebuy"], int):
            if bool(config["enableimmediatebuy"]):
                app.enableimmediatebuy = True
        else:
            raise TypeError("enableimmediatebuy must be of type int")

    if "sellsmartswitch" in config:
        if isinstance(config["sellsmartswitch"], int):
            if config["sellsmartswitch"] in [0, 1]:
                app.sell_smart_switch = config["sellsmartswitch"]
                if app.sell_smart_switch == 1:
                    app.sell_smart_switch = 1
                else:
                    app.sell_smart_switch = 0
        else:
            raise TypeError("sellsmartswitch must be of type int")

    # backward compatibility
    if "nosellatloss" in config:
        if isinstance(config["nosellatloss"], int):
            if config["nosellatloss"] in [0, 1]:
                app.sell_at_loss = int(not config["nosellatloss"])
                if app.sell_at_loss == 0:
                    app.sell_lower_pcnt = None
                    app.trailing_stop_loss = None
        else:
            raise TypeError("nosellatloss must be of type int")

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

    if "buymaxsize" in config:
        if isinstance(config["buymaxsize"], (int, float)):
            if config["buymaxsize"] > 0:
                app.buymaxsize = config["buymaxsize"]
        else:
            raise TypeError("buymaxsize must be of type int or float")

    if "buyminsize" in config:
        if isinstance(config["buyminsize"], (int, float)):
            if config["buyminsize"] > 0:
                app.buyminsize = config["buyminsize"]
        else:
            raise TypeError("buyminsize must be of type int or float")

    if "buylastsellsize" in config:
        if isinstance(config["buylastsellsize"], int):
            if bool(config["buylastsellsize"]):
                app.buylastsellsize = True
        else:
            raise TypeError("buylastsellsize must be of type int")

    if "trailingbuypcnt" in config:
        if isinstance(config["trailingbuypcnt"], (int, float)):
            if config["trailingbuypcnt"] > 0:
                app.trailingbuypcnt = config["trailingbuypcnt"]
        else:
            raise TypeError("trailingbuypcnt must be of type int or float")

    if "marketmultibuycheck" in config:
        if isinstance(config["marketmultibuycheck"], int):
            if bool(config["marketmultibuycheck"]):
                app.marketmultibuycheck = True
        else:
            raise TypeError("marketmultibuycheck must be of type int")

    if "logbuysellinjson" in config:
        if isinstance(config["logbuysellinjson"], int):
            if bool(config["logbuysellinjson"]):
                app.logbuysellinjson = True
        else:
            raise TypeError("logbuysellinjson must be of type int")

    if 'granularity' in config and config['granularity'] is not None:
        app.smart_switch = 0
        if isinstance(config['granularity'], str) and not config['granularity'].isnumeric() is True:
            app.granularity = Granularity.convert_to_enum(config['granularity'])
        else:
            app.granularity = Granularity.convert_to_enum(int(config['granularity']))
