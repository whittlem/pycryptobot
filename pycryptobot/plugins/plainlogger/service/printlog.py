from pycryptobot.DTO.Event import EventDTO
from cement import App

def print(app: App, evt: EventDTO):
    app.print(app.render(evt.__dict__, 'plugins/plainlogger/command1.jinja2', None))