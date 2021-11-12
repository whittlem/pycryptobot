from cement import Controller, ex
from ..constants.base_arguments import base_arguments
from ..core.core import main
from ..models.ConfigBuilder import ConfigBuilder
from ..models.PyCryptoBot import PyCryptoBot


class Base(Controller):
    class Meta:
        label = 'base'

        # text displayed at the top of --help output
        description = 'Python Crypto Bot using the Coinbase Pro or Binanace API'

        # text displayed at the bottom of --help output
        epilog = 'Usage: pycryptobot'

        # controller level arguments. ex: 'pycryptobot --version'

        arguments = base_arguments

    def _default(self):
            """Default action if no sub-command is passed."""

            app = PyCryptoBot(self.app)
            app.cementApp = self.app
            main(app)

    @ex(
        help='Init new config.json file'
    )
    def init(self):
        ConfigBuilder().init()

