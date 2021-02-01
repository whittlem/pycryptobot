import pytest, sys

sys.path.append('.')
# pylint: disable=import-error
from models.TradingAccount import TradingAccount

def test_default_initial_balance():
    account = TradingAccount()
    assert account.getBalance('GBP') == 1000

def test_buy_sufficient_funds():
    account = TradingAccount()
    account.buy('BTC', 'GBP', 1000, 30000)
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
    assert account.getBalance('GBP') == 1152.7