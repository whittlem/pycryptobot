from cement import App

from ..DTO.StartEvent import StartEvent
from ..models.PyCryptoBot import PyCryptoBot
from ..models.helper.TelegramBotHelper import TelegramBotHelper


class TelegramBot:
    """
    This is basic extension, for the beginning for signal handling
    Later can be moved all Bot logic
    """
    pycryptobot_app: PyCryptoBot

    def init(self, evt: StartEvent):
        self.pycryptobot_app = evt.pycryptobot_app

    def signal_handler(self, _):
        telegram_bot = TelegramBotHelper(self.pycryptobot_app)
        try:
            telegram_bot.removeactivebot()
        except:
            pass


def load(app: App):
    telegram_bot = TelegramBot()
    app.hook.register('event.bot.start', telegram_bot.init)
    app.hook.register('pre_close', telegram_bot.signal_handler)
