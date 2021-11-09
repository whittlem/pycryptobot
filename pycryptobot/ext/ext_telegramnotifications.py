from cement import App

from ..DTO.ChangeActionEvent import ChangeActionEvent
from ..DTO.EventInterface import EventInterface
from ..DTO.GranularityChangeEvent import GranularityChange
from ..DTO.OrderEvent import BuyEvent, SellEvent
from ..DTO.StartEvent import StartEvent, StateChange
from ..models.chat.telegram import Telegram

templates = {
    StartEvent.__name__: 'bot_start.jinja2',
    GranularityChange.__name__: 'granularity_change.jinja2',
    ChangeActionEvent.__name__: 'action_change.jinja2',
    BuyEvent.__name__: 'order_buy.jinja2',
    SellEvent.__name__: 'order_sell.jinja2',
    StateChange.__name__: 'state_change.jinja2',
}


class TelegramNotification():
    render = None
    _chat_client: Telegram = None

    def init(self, app: App):
        token = app.config.get('telegram', 'token')
        client_id = app.config.get('telegram', 'client_id')
        self.render = app.render
        # disabled = app.config.get('telegram', 'disabletelegram') #TODO: figure out how to get this value
        if token and client_id:
            self._chat_client = Telegram(token, client_id)

    def notify_telegram(self, evt: EventInterface):
        if self._chat_client is None and evt.__name__ not in templates.keys():
            return

        self._chat_client.send(
            self.render(evt.reprJSON(), templates[evt.__class__.__name__], handler='jinja2', out=None))


def load(app: App):
    telegram = TelegramNotification()
    app.hook.register('post_setup', telegram.init)
    app.hook.register('event.bot.start', telegram.notify_telegram)
    app.hook.register('event.bot.paused', telegram.notify_telegram)
    app.hook.register('event.bot.stop', telegram.notify_telegram)
    app.hook.register('event.granularity.change', telegram.notify_telegram)
    app.hook.register('event.action.change', telegram.notify_telegram)
    app.hook.register('event.order.buy', telegram.notify_telegram)
    app.hook.register('event.order.sell', telegram.notify_telegram)
