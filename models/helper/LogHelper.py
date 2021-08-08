import logging


class Logger:
    logger = None

    def __init__(self):
        pass

    @classmethod
    def get_level(cls, level):
        if level == "CRITICAL":
            return logging.CRITICAL
        elif level == "ERROR":
            return logging.ERROR
        elif level == "WARNING":
            return logging.WARNING
        elif level == "INFO":
            return logging.INFO
        elif level == "DEBUG":
            return logging.DEBUG
        else:
            return logging.NOTSET

    @classmethod
    def configure(
        cls,
        filelog=1,
        logfile="pycryptobot.log",
        fileloglevel="DEBUG",
        consolelog=1,
        consoleloglevel="INFO",
    ):
        # reduce informational logging
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        # initialize class logger
        cls.logger = logging.getLogger("pycryptobot")
        cls.logger.setLevel(logging.DEBUG)

        if not consolelog and not filelog:
            cls.logger.disabled = True

        if consolelog:
            # set a format which is simpler for console use
            consoleHandlerFormatter = logging.Formatter("%(message)s")
            # define a Handler which writes sys.stdout
            consoleHandler = logging.StreamHandler()
            # Set log level
            consoleHandler.setLevel(cls.get_level(consoleloglevel))

            # tell the handler to use this format
            consoleHandler.setFormatter(consoleHandlerFormatter)
            # add the handler to the root logger
            cls.logger.addHandler(consoleHandler)

        if filelog:
            # set up logging to file
            fileHandlerFormatter = logging.Formatter(
                fmt="%(asctime)s %(levelname)-8s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            fileHandler = logging.FileHandler(logfile)
            fileHandler.setLevel(cls.get_level(fileloglevel))
            fileHandler.setFormatter(fileHandlerFormatter)
            cls.logger.addHandler(fileHandler)

    @classmethod
    def debug(cls, str):
        cls.logger.debug(str)

    @classmethod
    def info(cls, str):
        cls.logger.info(str)

    @classmethod
    def warning(cls, str):
        cls.logger.warning(str)

    @classmethod
    def error(cls, str):
        cls.logger.error(str)

    @classmethod
    def critical(cls, str):
        cls.logger.critical(str)
