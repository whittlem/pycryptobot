import sys

sys.path.append('.')
# pylint: disable=import-error
from models.PyCryptoBot import PyCryptoBot

def test_instantiate_model_without_error():
    app = PyCryptoBot()
    assert type(app) is PyCryptoBot

    app = PyCryptoBot(exchange='coinbasepro')
    assert type(app) is PyCryptoBot
    assert app.getExchange() == 'coinbasepro'

    app = PyCryptoBot(exchange='binance')
    assert type(app) is PyCryptoBot
    assert app.getExchange() == 'binance'

    #app = PyCryptoBot(exchange='dummy')
    #assert type(app) is PyCryptoBot
    #assert app.getExchange() == 'dummy'

    # TODO: validate file exists
    app = PyCryptoBot(filename='config.json')
    assert type(app) is PyCryptoBot