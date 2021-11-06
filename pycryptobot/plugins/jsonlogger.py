from cement import App
from ..DTO.Event import EventDTO, ComplexEncoder
import json


def print(app: App, evt: EventDTO):
    app.print(json.dumps(evt.reprJSON(), cls=ComplexEncoder))

def load(app: App):
    app.hook.register('event_log_technical_indicators', print)
