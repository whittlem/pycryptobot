from cement import Controller
from pycryptobot.models.PyCryptoBot import PyCryptoBot
from pycryptobot.models.exchange.binance import AuthAPI as BAuthAPI
from pycryptobot.models.exchange.coinbase_pro import AuthAPI as CAuthAPI

class GetFees(Controller):
    class Meta:
        label = 'get-fees'
        stacked_on = 'base'
        stacked_type = 'nested'
        # text displayed at the top of --help output
        description = 'ex. script-get_fees.py'
        help = 'get-fees'
        # text dis played at the bottom of --help output
        epilog = 'Usage: pycryptobot get-fees'

        arguments = []

    def _default(self):
            """Default action if no sub-command is passed."""

            app = PyCryptoBot(self.app, exchange='coinbasepro')
            api = CAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIPassphrase(), app.getAPIURL())
            # print (api.getTakerFee())
            # print (api.getTakerFee('BTC-GBP'))
            # print (api.getMakerFee())
            # print (api.getMakerFee('BTC-GBP'))
            # print (api.getFees('BTCGBP'))
            # print (api.getFees())
            print(app.getMakerFee())
            print(app.getTakerFee())

            # Binance fees
            app = PyCryptoBot(self.app, exchange='binance')
            api = BAuthAPI(app.getAPIKey(), app.getAPISecret(), app.getAPIURL())
            # print (api.getTakerFee())
            # print (api.getTakerFee('BTCGBP'))
            # print (api.getMakerFee())
            # print (api.getMakerFee('BTCGBP'))
            # print (api.getFees('BTCGBP'))
            # print (api.getFees())
            print(app.getMakerFee())
            print(app.getTakerFee())
