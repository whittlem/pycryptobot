from cement import Controller
from ..models.PyCryptoBot import PyCryptoBot


class GetOrders(Controller):
    class Meta:
        label = 'get-orders'
        stacked_on = 'base'
        stacked_type = 'nested'
        # text displayed at the top of --help output
        description = 'ex. script-get_orders.py'
        help = 'get-orders'
        # text dis played at the bottom of --help output
        epilog = 'Usage: pycryptobot get-orders'

        arguments = []

    def _default(self):
        """Default action if no sub-command is passed."""

        app = PyCryptoBot(self.app, exchange='coinbasepro')
        print(app.getExchange())

        app = PyCryptoBot(self.app, exchange='binance')
        print(app.getExchange())

        app = PyCryptoBot(self.app, exchange='dummy')
        print(app.getExchange())

        app = PyCryptoBot(self.app)
        print(app.getExchange())
