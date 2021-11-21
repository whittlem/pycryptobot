from cement import App
from ..DTO.StartEvent import StartEvent


class SignalHandler:
    websocket: None

    def init(self, evt: StartEvent):
        self.websocket = evt.websocket

    def handle(self, _):
        if self.websocket is not None:
            self.websocket.close()


def load(app: App):
    signal_handler = SignalHandler()
    app.hook.register('event.bot.start', signal_handler.init)
    app.hook.register('pre_close', signal_handler.handle)