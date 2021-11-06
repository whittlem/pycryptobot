
import os
from .service.printlog import print
from cement import App

def add_template_dir(app: App):
    path = os.path.join(os.path.dirname(__file__), 'templates')
    app.add_template_dir(path)


def load(app: App):
    app.hook.register('event_log_technical_indicators', print)
    app.hook.register('post_setup', add_template_dir)
