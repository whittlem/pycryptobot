
from cement import App, TestApp, init_defaults
from cement.core.exc import CaughtSignal
from .core.exc import PyCryptoBotError
from .controllers.base import Base

# configuration defaults
CONFIG = init_defaults('pycryptobot')
CONFIG['pycryptobot']['foo'] = 'bar'
CONFIG['plugin.plainlogger'] = {"enabled": True}
CONFIG['plugin.jsonlogger'] = {"enabled": True}


class PyCryptoBot(App):
    """PyCryptoBot primary application."""

    class Meta:
        label = 'pycryptobot'

        # configuration defaults
        config_defaults = CONFIG

        # call sys.exit() on close
        exit_on_close = True

        # load additional framework extensions
        extensions = [
            'json',
            'colorlog',
            'jinja2',
            'print',
        ]

        # configuration handler
        config_handler = 'json'

        # configuration file suffix
        config_file_suffix = '.json'

        # set the log handler
        log_handler = 'colorlog'

        # set the output handler
        output_handler = 'jinja2'

        # register handlers
        handlers = [
            Base
        ]
        define_hooks = [
            'event_log_technical_indicators'
        ]

class PyCryptoBotTest(TestApp,PyCryptoBot):
    """A sub-class of PyCryptoBot that is better suited for testing."""

    class Meta:
        label = 'pycryptobot'


def main():
    with PyCryptoBot() as app:
        try:
            app.run()

        except AssertionError as e:
            print('AssertionError > %s' % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except PyCryptoBotError as e:
            print('PyCryptoBotError > %s' % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except CaughtSignal as e:
            # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
            print('\n%s' % e)
            app.exit_code = 0


if __name__ == '__main__':
    main()
