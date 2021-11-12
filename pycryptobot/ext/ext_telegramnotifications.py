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


def _is_telegram_notifications_disabled(app: App) -> bool:
    if not app.config.has_section('telegram'):
        return True
    if 'disable' in app.config.keys('telegram') and app.config.get('telegram', 'disable'):
        return True
    if 'disabletelegram' in app.pargs and app.pargs.disabletelegram:
        return True
    if app.config.has_section('binance') \
            and 'disabletelegram' in app.config.keys('binance') \
            and app.config.get('binance', 'disabletelegram'):
        return True
    if app.config.has_section('coinbasepro') \
            and 'disabletelegram' in app.config.keys('coinbasepro') \
            and app.config.get('coinbasepro', 'disabletelegram'):
        return True
    if app.config.has_section('kucoin') \
            and 'disabletelegram' in app.config.keys('kucoin') \
            and app.config.get('coinbasepro', 'disabletelegram'):
        return True
    return False


class TelegramNotification():
    render = None
    _chat_client: Telegram = None

    def init(self, app: App):
        if _is_telegram_notifications_disabled(app):
            return
        token = app.config.get('telegram', 'token')
        client_id = app.config.get('telegram', 'client_id')
        self.render = app.render
        if token and client_id:
            self._chat_client = Telegram(token, client_id)

    def notify_telegram(self, evt: EventInterface):
        if self._chat_client is None and evt.__name__ not in templates.keys():
            return

        self._chat_client.send(
            self.render(evt.reprJSON(), templates[evt.__class__.__name__], handler='jinja2', out=None))


def load(app: App):
    telegram = TelegramNotification()
    app.hook.register('post_argument_parsing', telegram.init)
    app.hook.register('event.bot.start', telegram.notify_telegram)
    app.hook.register('event.bot.paused', telegram.notify_telegram)
    app.hook.register('event.bot.stop', telegram.notify_telegram)
    app.hook.register('event.granularity.change', telegram.notify_telegram)
    app.hook.register('event.action.change', telegram.notify_telegram)
    app.hook.register('event.order.buy', telegram.notify_telegram)
    app.hook.register('event.order.sell', telegram.notify_telegram)
