import json, os, sys

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

def test_configjson_islive():
    config = {
        "coinbasepro" : {
            "api_url" : "https://api.pro.coinbase.com",
            "api_key" : "00000000000000000000000000000000",
            "api_secret" : "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000==",
            "api_passphrase" : "00000000000"
        } 
    }

    try:
        config_json = json.dumps(config)
        fh = open('/tmp/pycryptobot_pytest_config.json', 'w')
        fh.write(config_json)
        fh.close()
    except Exception as err:
        print (err)

    app = PyCryptoBot(filename='/tmp/pycryptobot_pytest_config.json')
    assert type(app) is PyCryptoBot
    assert app.getExchange() == 'coinbasepro'
    assert app.isLive() == 0

    if os.path.exists('/tmp/pycryptobot_pytest_config.json'):
        os.remove('/tmp/pycryptobot_pytest_config.json')

    config = {
        "coinbasepro" : {
            "api_url" : "https://api.pro.coinbase.com",
            "api_key" : "00000000000000000000000000000000",
            "api_secret" : "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000==",
            "api_passphrase" : "00000000000",
            "config" : {
                "live" : 1
            }
        } 
    }

    try:
        config_json = json.dumps(config)
        fh = open('/tmp/pycryptobot_pytest_config.json', 'w')
        fh.write(config_json)
        fh.close()
    except Exception as err:
        print (err)

    app = PyCryptoBot(filename='/tmp/pycryptobot_pytest_config.json')
    assert type(app) is PyCryptoBot
    assert app.getExchange() == 'coinbasepro'
    assert app.isLive() == 1

    app.setLive(0)
    assert app.isLive() == 0

    if os.path.exists('/tmp/pycryptobot_pytest_config.json'):
        os.remove('/tmp/pycryptobot_pytest_config.json')