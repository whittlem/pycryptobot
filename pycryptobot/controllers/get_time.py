from cement import Controller
from ..models.PyCryptoBot import PyCryptoBot
from ..models.exchange.binance import PublicAPI as BPublicAPI
from ..models.exchange.coinbase_pro import PublicAPI as CBPublicAPI

class GetTime(Controller):
    class Meta:
        label = 'get-time'
        stacked_on = 'base'
        stacked_type = 'nested'
        # text displayed at the top of --help output
        description = 'ex. script-get_time.py'
        help = 'get-fees'
        # text dis played at the bottom of --help output
        epilog = 'Usage: pycryptobot get-time'

        arguments = []

    def _default(self):
            """Default action if no sub-command is passed."""

            # Coinbase Pro time
            api = CBPublicAPI()
            ts = api.getTime()
            print (ts)

            app = PyCryptoBot(self.app, exchange='coinbasepro')
            ts = api.getTime()
            print (ts)

            # Binance Live time
            api = BPublicAPI()
            ts = api.getTime()
            print (ts)

            app = PyCryptoBot(self.app, exchange='binance')
            ts = api.getTime()
            print (ts)