import pytest, sys
import pandas as pd

sys.path.append('.')
# pylint: disable=import-error
from models.TradingAccount import TradingAccount

def test_default_initial_balance():
    account = TradingAccount()
    assert type(account.getBalance('GBP')) is float
    assert account.getBalance('GBP') == 1000

def test_buy_sufficient_funds():
    account = TradingAccount()
    account.buy('BTC', 'GBP', 1000, 30000)
    assert type(account.getBalance('GBP')) is float
    assert account.getBalance('GBP') == 0

def test_buy_insufficient_funds():
    account = TradingAccount()
    with pytest.raises(Exception) as execinfo:
        account.buy('BTC', 'GBP', 1001, 30000)
    assert str(execinfo.value) == 'Insufficient funds.'

def test_sell_insufficient_funds():
    account = TradingAccount()
    account.buy('BTC', 'GBP', 1000, 30000)
    with pytest.raises(Exception) as execinfo:
        account.sell('BTC', 'GBP', 1, 35000)
    assert str(execinfo.value) == 'Insufficient funds.'

def test_successful_buy_and_sell():
    account = TradingAccount()
    account.buy('BTC', 'GBP', 1000, 30000)
    account.sell('BTC', 'GBP', 0.0331, 35000)
    assert type(account.getBalance('GBP')) is float
    assert account.getBalance('GBP') == 1152.7

def test_unspecified_balance_returns_dict():
    account = TradingAccount()
    assert type(account.getBalance()) is pd.DataFrame

def test_orders_returns_dict():
    account = TradingAccount()
    assert type(account.getOrders()) is pd.DataFrame

def test_orders_columns():
    account = TradingAccount()
    account.buy('BTC', 'GBP', 1000, 30000)
    actual = account.getOrders().columns.to_list()
    expected = [ 'created_at', 'market', 'action', 'type', 'size', 'value', 'status', 'price' ]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])

def test_orders_filtering():
    account = TradingAccount()
    account.buy('BTC','GBP',250,30000)
    assert len(account.getOrders()) == 1
    account.sell('BTC','GBP',0.0082,35000)
    assert len(account.getOrders()) == 2
    account.buy('ETH','GBP',250,30000)
    assert len(account.getOrders()) == 3
    account.sell('ETH','GBP',0.0082,35000)
    assert len(account.getOrders()) == 4
    assert len(account.getOrders('BTC-GBP')) == 2