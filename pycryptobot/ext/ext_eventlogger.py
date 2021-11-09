from pycryptobot.DTO.ChangeActionEvent import ChangeActionEvent
from pycryptobot.DTO.EventInterface import EventInterface
from pycryptobot.DTO.GranularityChangeEvent import GranularityChange
from pycryptobot.DTO.OrderEvent import BuyEvent, SellEvent
from pycryptobot.DTO.TIEvent import TIEvent
from pycryptobot.DTO.StartEvent import StartEvent, StateChange
from cement import App

templates = {
    StartEvent.__name__: 'bot_start.jinja2',
    GranularityChange.__name__: 'granularity_change.jinja2',
    TIEvent.__name__: 'print_indicators.jinja2',
    ChangeActionEvent.__name__: 'action_change.jinja2',
    BuyEvent.__name__: 'order_buy.jinja2',
    SellEvent.__name__: 'order_sell.jinja2',
    StateChange.__name__: 'state_change.jinja2',
}


class PlainLogService():
    _app: App

    def init(self, app: App):
        self._app = app

    def print(self, evt: EventInterface):
        self._app.print(self._app.render(evt.reprJSON(), templates[evt.__class__.__name__], None))


def load(app: App):
    plain_logger = PlainLogService()
    # app.hook.register('post_setup', add_template_dir)
    app.hook.register('post_setup', plain_logger.init)
    app.hook.register('event.bot.start', plain_logger.print)
    app.hook.register('event.bot.paused', plain_logger.print)
    app.hook.register('event.bot.stop', plain_logger.print)
    app.hook.register('event.granularity.change', plain_logger.print)
    app.hook.register('event.log.technical.indicators', plain_logger.print)
    app.hook.register('event.action.change', plain_logger.print)
    app.hook.register('event.order.buy', plain_logger.print)
    app.hook.register('event.order.sell', plain_logger.print)


# if not _app.isSimulation() or (
#                                 _app.isSimulation() and not _app.simResultOnly()
#                         ):