import json
import pytest
import responses
import requests
import sys

sys.path.append('.')
# pylint: disable=import-error
from models.PyCryptoBot import PyCryptoBot
from models.exchange.binance import AuthAPI as BAuthAPI, PublicAPI as BPublicAPI

@responses.activate
def test_api_v3_account1():
    app = PyCryptoBot(exchange='binance', config=False)
    api = BAuthAPI(app.getAPIKey(), app.getAPISecret())

    with open('tests/unit_tests/responses/account1.json') as fh:
        responses.add(responses.GET, 'https://api.binance.com/api/v3/account', json=json.load(fh), status=200)
        df = api.getAccounts()
        fh.close()

        assert len(df) > 1
        assert df.columns.tolist() == [ 'index', 'id', 'currency', 'balance', 'hold', 'available', 'profile_id', 'trading_enabled' ]
        assert df.dtypes['index'] == 'int64'
        assert df.dtypes['id'] == 'object'
        assert df.dtypes['currency'] == 'object'
        assert df.dtypes['balance'] == 'object'
        assert df.dtypes['hold'] == 'object'
        assert df.dtypes['available'] == 'object'
        assert df.dtypes['profile_id'] == 'object'
        assert df.dtypes['trading_enabled'] == 'bool'