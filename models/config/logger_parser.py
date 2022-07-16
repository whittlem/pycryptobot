import re

from .default_parser import isCurrencyValid, defaultConfigParse, merge_config_and_args
from models.helper.LogHelper import Logger

def parser(app, logger_config):
    #print('Logger Configuration parser')

    if not logger_config:
        raise Exception('There is an error in your config dictionnary')

    if not app:
        raise Exception('No app is passed')

    if 'filelog' in logger_config:
        if isinstance(logger_config['filelog'], int):
            if logger_config['filelog'] in [0, 1]:
                self.filelog = logger_config['filelog']
        else:
            raise TypeError('filelog must be type of int')

    if self.filelog:
        if 'logfile' in logger_config:
            if isinstance(logger_config['logfile'], str):
                if self.logfile == "pycryptobot.log":
                    self.logfile = logger_config['logfile']
            else:
                raise TypeError('logfile must be type of str')

        if 'fileloglevel' in logger_config:
            if isinstance(logger_config['fileloglevel'], str):
                if logger_config['fileloglevel'] in ('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'):
                    self.fileloglevel = logger_config['fileloglevel']
                else:
                    raise TypeError('fileloglevel must be one of: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"')
            else:
                raise TypeError('fileloglevel must be type of str')

    if 'consolelog' in logger_config:
        if isinstance(logger_config['consolelog'], int):
            if logger_config['consolelog'] in [0, 1]:
                self.consolelog = logger_config['consolelog']
        else:
            raise TypeError('consolelog must be type of int')

    if self.consolelog:
        if 'consoleloglevel' in logger_config:
            if isinstance(logger_config['consoleloglevel'], str):
                if logger_config['consoleloglevel'] in ('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'):
                    self.consoleloglevel = logger_config['consoleloglevel']
                else:
                    raise TypeError('consoleloglevel must be one of: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"')
            else:
                raise TypeError('consoleloglevel must be type of str')
