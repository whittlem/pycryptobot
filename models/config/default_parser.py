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

    if "dynamictsl" in config:
        if isinstance(config["dynamictsl"], int):
            if config["dynamictsl"] in [0, 1]:
                app.dynamic_tsl = bool(config["dynamictsl"])
        else:
            raise TypeError("dynamictsl must be of type int")

    if "tslmultiplier" in config:
        if isinstance(config["tslmultiplier"], (int, float)):
            if config["tslmultiplier"] > 0:
                app.tsl_multiplier = float(config["tslmultiplier"])
        else:
            raise TypeError("tslmultiplier must be of type int or float")

    if "tsltriggermultiplier" in config:
        if isinstance(config["tsltriggermultiplier"], (int, float)):
            if config["tsltriggermultiplier"] > 0:
                app.tsl_trigger_multiplier = float(config["tsltriggermultiplier"])
        else:
            raise TypeError("tsltriggermultiplier must be of type int or float")

    if "tslmaxpcnt" in config:
        if isinstance(config["tslmaxpcnt"], (int, float)):
            if config["tslmaxpcnt"] <= 0:
                app.tsl_max_pcnt = float(config["tslmaxpcnt"])
        else:
            raise TypeError("tslmaxpcnt must be < 0 and of type int or float")

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

    if "preventloss" in config:
        if isinstance(config["preventloss"], int):
            if bool(config["preventloss"]):
                app.preventloss = True
        else:
            raise TypeError("preventloss must be of type int")

    if "preventlosstrigger" in config:
        if isinstance(config["preventlosstrigger"], (int, float)):
            if config["preventlosstrigger"] is not None:
                app.preventlosstrigger = float(config["preventlosstrigger"])
        else:
            raise TypeError("preventlossmargin must be of type int or float")
    elif app.preventloss:
        if app.nosellmaxpcnt is not None:
            app.preventlosstrigger = app.nosellmaxpcnt
        else:
            app.preventlosstrigger = 1

    if "preventlossmargin" in config:
        if isinstance(config["preventlossmargin"], (int, float)):
            if config["preventlossmargin"] is not None:
                app.preventlossmargin = config["preventlossmargin"]
        else:
            raise TypeError("preventlossmargin must be of type int or float")
    elif app.preventloss:
        app.preventlossmargin = 0.1

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
            if config["disablebullonly"] in [0, 1]:
                app.disablebullonly = bool(config["disablebullonly"])
        else:
            raise TypeError("disablebullonly must be of type int")

    if "disablebuynearhigh" in config:
        if isinstance(config["disablebuynearhigh"], int):
            if config["disablebuynearhigh"] in [0, 1]:
                app.disablebuynearhigh = bool(config["disablebuynearhigh"])
        else:
            raise TypeError("disablebuynearhigh must be of type int")

    if "disablebuymacd" in config:
        if isinstance(config["disablebuymacd"], int):
            if config["disablebuymacd"] in [0, 1]:
                app.disablebuymacd = bool(config["disablebuymacd"])
        else:
            raise TypeError("disablebuymacd must be of type int")

    if "disablebuyema" in config:
        if isinstance(config["disablebuyema"], int):
            if config["disablebuyema"] in [0, 1]:
                app.disablebuyema = bool(config["disablebuyema"])
        else:
            raise TypeError("disablebuyema must be of type int")

    if "disablebuyobv" in config:
        if isinstance(config["disablebuyobv"], int):
            if config["disablebuyobv"] in [0, 1]:
                app.disablebuyobv = bool(config["disablebuyobv"])
        else:
            raise TypeError("disablebuyobv must be of type int")

    if "disablebuyelderray" in config:
        if isinstance(config["disablebuyelderray"], int):
            if config["disablebuyelderray"] in [0, 1]:
                app.disablebuyelderray = bool(config["disablebuyelderray"])
        else:
            raise TypeError("disablebuyelderray must be of type int")

    if "disablefailsafefibonaccilow" in config:
        if isinstance(config["disablefailsafefibonaccilow"], int):
            if config["disablefailsafefibonaccilow"] in [0,1 ]:
                app.disablefailsafefibonaccilow = bool(config["disablefailsafefibonaccilow"])
        else:
            raise TypeError("disablefailsafefibonaccilow must be of type int")

    if "disablefailsafelowerpcnt" in config:
        if isinstance(config["disablefailsafelowerpcnt"], int):
            if config["disablefailsafelowerpcnt"] in [0, 1]:
                app.disablefailsafelowerpcnt = bool(config["disablefailsafelowerpcnt"])
        else:
            raise TypeError("disablefailsafelowerpcnt must be of type int")

    if "disableprofitbankupperpcnt" in config:
        if isinstance(config["disableprofitbankupperpcnt"], int):
            if config["disableprofitbankupperpcnt"] in [0, 1]:
                app.disableprofitbankupperpcnt = bool(config["disableprofitbankupperpcnt"])
        else:
            raise TypeError("disableprofitbankupperpcnt must be of type int")

    if "disableprofitbankreversal" in config:
        if isinstance(config["disableprofitbankreversal"], int):
            if config["disableprofitbankreversal"] in [0, 1]:
                app.disableprofitbankreversal = bool(config["disableprofitbankreversal"])
        else:
            raise TypeError("disableprofitbankreversal must be of type int")

    if "enable_pandas_ta" in config:
        if isinstance(config["enable_pandas_ta"], int):
            if config["enable_pandas_ta"] in [0, 1]:
                app.enable_pandas_ta = bool(config["enable_pandas_ta"])
        else:
            raise TypeError("enable_pandas_ta must be of type int")

    if "enable_custom_strategy" in config:
        if isinstance(config["enable_custom_strategy"], int):
            if config["enable_custom_strategy"] in [0, 1]:
                app.enable_custom_strategy = bool(config["enable_custom_strategy"])
        else:
            raise TypeError("enable_custom_strategy must be of type int")

    if "disabletelegram" in config:
        if isinstance(config["disabletelegram"], int):
            if config["disabletelegram"] in [0, 1]:
                app.disabletelegram = bool(config["disabletelegram"])
        else:
            raise TypeError("disabletelegram must be of type int")

    if "telegramtradesonly" in config:
        if isinstance(config["telegramtradesonly"], int):
            if config["telegramtradesonly"] in [0, 1]:
                app.telegramtradesonly = bool(config["telegramtradesonly"])
        else:
            raise TypeError("telegramtradesonly must be of type int")

    if "disabletelegramerrormsgs" in config:
        if isinstance(config["disabletelegramerrormsgs"], int):
            if config["disabletelegramerrormsgs"] in [0, 1]:
                app.disabletelegramerrormsgs = bool(config["disabletelegramerrormsgs"])
        else:
            raise TypeError("disabletelegramerrormsgs must be of type int")

    if "disablelog" in config:
        if isinstance(config["disablelog"], int):
            if config["disablelog"] in [0, 1]:
                app.disablelog = bool(config["disablelog"])
        else:
            raise TypeError("disablelog must be of type int")

    if "disabletracker" in config:
        if isinstance(config["disabletracker"], int):
            if config["disabletracker"] in [0, 1]:
                app.disabletracker = bool(config["disabletracker"])
        else:
            raise TypeError("disabletracker must be of type int")

    if "enableml" in config:
        if isinstance(config["enableml"], int):
            if config["enableml"] in [0, 1]:
                app.enableml = bool(config["enableml"])
        else:
            raise TypeError("enableml must be of type int")

    if "websocket" in config:
        if isinstance(config["websocket"], int):
            if config["websocket"] in [0, 1]:
                app.websocket = bool(config["websocket"])
        else:
            raise TypeError("websocket must be of type int")

    if "enableinsufficientfundslogging" in config:
        if isinstance(config["enableinsufficientfundslogging"], int):
            if config["enableinsufficientfundslogging"] in [0, 1]:
                app.enableinsufficientfundslogging = bool(config["enableinsufficientfundslogging"])
        else:
            raise TypeError("enableinsufficientfundslogging must be of type int")

    if "enabletelegrambotcontrol" in config:
        if isinstance(config["enabletelegrambotcontrol"], int):
            if config["enabletelegrambotcontrol"] in [0, 1]:
                app.enabletelegrambotcontrol = bool(config["enabletelegrambotcontrol"])
        else:
            raise TypeError("enabletelegrambotcontrol must be of type int")

    if "enableimmediatebuy" in config:
        if isinstance(config["enableimmediatebuy"], int):
            if config["enableimmediatebuy"] in [0, 1]:
                app.enableimmediatebuy = bool(config["enableimmediatebuy"])
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

    if "trailingimmediatebuy" in config:
        if isinstance(config["trailingimmediatebuy"], int):
            if config["trailingimmediatebuy"] in [0, 1]:
                app.trailingimmediatebuy = bool(config["trailingimmediatebuy"])
        else:
            raise TypeError("trailingimmediatebuy must be of type int")

    if "trailingbuyimmediatepcnt" in config:
        if isinstance(config["trailingbuyimmediatepcnt"], (int, float)):
            if config["trailingbuyimmediatepcnt"] > 0:
                app.trailingbuyimmediatepcnt = config["trailingbuyimmediatepcnt"]
        else:
            raise TypeError("trailingbuyimmediatepcnt must be of type int or float")

    if "trailingsellpcnt" in config:
        if isinstance(config["trailingsellpcnt"], (int, float)):
            if config["trailingsellpcnt"] <= 0:
                app.trailingsellpcnt = config["trailingsellpcnt"]
        else:
            raise TypeError("trailingsellpcnt must be < 0 and of type int or float")

    if "trailingimmediatesell" in config:
        if isinstance(config["trailingimmediatesell"], int):
            if config["trailingimmediatesell"] in [0, 1]:
                app.trailingimmediatesell = bool(config["trailingimmediatesell"])
        else:
            raise TypeError("trailingimmediatesell must be of type int")

    if "trailingsellimmediatepcnt" in config:
        if isinstance(config["trailingsellimmediatepcnt"], (int, float)):
            if config["trailingsellimmediatepcnt"] <= 0:
                app.trailingsellimmediatepcnt = config["trailingsellimmediatepcnt"]
        else:
            raise TypeError("trailingsellimmediatepcnt must be < 0 and of type int or float")

    if "trailingsellbailoutpcnt" in config:
        if isinstance(config["trailingsellbailoutpcnt"], (int, float)):
            if config["trailingsellbailoutpcnt"] <= 0:
                app.trailingsellbailoutpcnt = config["trailingsellbailoutpcnt"]
        else:
            raise TypeError("trailingsellbailoutpcnt must be < 0 and of type int or float")

    if "selltriggeroverride" in config:
        if isinstance(config["selltriggeroverride"], int):
            if config["selltriggeroverride"] in [0, 1]:
                app.sell_trigger_override = bool(config["selltriggeroverride"])
        else:
            raise TypeError("selltriggeroverride must be of type int")

    if "marketmultibuycheck" in config:
        if isinstance(config["marketmultibuycheck"], int):
            if config["marketmultibuycheck"] in [0, 1]:
                app.marketmultibuycheck = bool(config["marketmultibuycheck"])
        else:
            raise TypeError("marketmultibuycheck must be of type int")

    if "logbuysellinjson" in config:
        if isinstance(config["logbuysellinjson"], int):
            if config["logbuysellinjson"] in [0, 1]:
                app.logbuysellinjson = bool(config["logbuysellinjson"])
        else:
            raise TypeError("logbuysellinjson must be of type int")

    if 'granularity' in config and config['granularity'] is not None:
        app.smart_switch = 0
        if isinstance(config['granularity'], str) and not config['granularity'].isnumeric() is True:
            app.granularity = Granularity.convert_to_enum(config['granularity'])
        else:
            app.granularity = Granularity.convert_to_enum(int(config['granularity']))

    if "usekucoincache" in config:
        if isinstance(config["usekucoincache"], int):
            if bool(config["usekucoincache"]):
                app.usekucoincache = True
        else:
            raise TypeError("usekucoincache must be of type int")

    if "adjust_total_periods" in config:
        if isinstance(config["adjust_total_periods"], (int, float)):
            if config["adjust_total_periods"] > 26 and config["adjust_total_periods"] < 300:
                app.adjust_total_periods = int(config["adjust_total_periods"])
        else:
            raise TypeError("adjust_total_periods must be > 26 and < 300 and of type int or float")

    if "manual_trades_only" in config:
        if isinstance(config["manual_trades_only"], int):
            if config["manual_trades_only"] in [0, 1]:
                app.manual_trades_only = bool(config["manual_trades_only"])
        else:
            raise TypeError("manual_trades_only must be of type int")
