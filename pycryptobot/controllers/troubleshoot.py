from cement import Controller
from ..models.PyCryptoBot import PyCryptoBot
from ..models.Trading import TechnicalAnalysis


# from models.TradingAccount import TradingAccount
# from models.AppState import AppState

class Troubleshoot(Controller):
    class Meta:
        label = 'troubleshoot'
        stacked_on = 'base'
        stacked_type = 'nested'
        # text displayed at the top of --help output
        description = 'ex. troubleshoot.py'
        help = 'troubleshoot'
        # text dis played at the bottom of --help output
        epilog = 'Usage: pycryptobot get-orders'

        arguments = []

    def _default(self):
        """Default action if no sub-command is passed."""
        app = PyCryptoBot(self.app)
        df = app.getHistoricalData(app.getMarket(), app.getGranularity(), websocket=None)
        print(df)
