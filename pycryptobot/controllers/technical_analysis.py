from cement import Controller
from ..models.PyCryptoBot import PyCryptoBot
from ..models.Trading import TechnicalAnalysis


class GetTechnicalAnalysis(Controller):
    class Meta:
        label = 'get-technical-analysis'
        stacked_on = 'base'
        stacked_type = 'nested'
        # text displayed at the top of --help output
        description = 'ex. script-technical-analysis.py'
        help = 'get-technical-analysis'
        # text dis played at the bottom of --help output
        epilog = 'Usage: pycryptobot get-time'

        arguments = []

    def _default(self):
        """Default action if no sub-command is passed."""

        app = PyCryptoBot(self.app)
        df = app.getHistoricalData(
            app.getMarket(),
            app.getGranularity(),
            websocket=None
        )

        model = TechnicalAnalysis(df)
        model.addATR(14)
        df = model.getDataFrame()
        print(df)
