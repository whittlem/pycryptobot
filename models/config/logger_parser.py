import re

from .default_parser import is_currency_valid, default_config_parse, merge_config_and_args
from models.helper.LogHelper import Logger


def parser(app, logger_config):
    if not logger_config:
        raise Exception("There is an error in your config dictionary")

    if not app:
        raise Exception("No app is passed")

    if "filelog" in logger_config:
        if isinstance(logger_config["filelog"], int):
            if logger_config["filelog"] in [0, 1]:
                app.filelog = logger_config["filelog"]
        else:
            raise TypeError("filelog must be type of int")

    if app.filelog:
        if "logfile" in logger_config:
            if isinstance(logger_config["logfile"], str):
                if app.logfile == "pycryptobot.log":
                    app.logfile = logger_config["logfile"]
            else:
                raise TypeError("logfile must be type of str")

        if "fileloglevel" in logger_config:
            if isinstance(logger_config["fileloglevel"], str):
                if logger_config["fileloglevel"] in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"):
                    app.fileloglevel = logger_config["fileloglevel"]
                else:
                    raise TypeError('fileloglevel must be one of: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"')
            else:
                raise TypeError("fileloglevel must be type of str")

    if "consolelog" in logger_config:
        if isinstance(logger_config["consolelog"], int):
            if logger_config["consolelog"] in [0, 1]:
                app.consolelog = logger_config["consolelog"]
        else:
            raise TypeError("consolelog must be type of int")

    if app.consolelog:
        if "consoleloglevel" in logger_config:
            if isinstance(logger_config["consoleloglevel"], str):
                if logger_config["consoleloglevel"] in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"):
                    app.consoleloglevel = logger_config["consoleloglevel"]
                else:
                    raise TypeError('consoleloglevel must be one of: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"')
            else:
                raise TypeError("consoleloglevel must be type of str")
