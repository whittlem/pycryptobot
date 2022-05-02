import sys

import pytest
# pylint: disable=import-error
from models.exchange.ExchangesEnum import Exchange

sys.path.append('.')


def test_enum_value_is_correct_for_binance():
    assert Exchange.BINANCE.value == "binance"


def test_enum_value_is_correct_for_coinbasepro():
    assert Exchange.COINBASEPRO.value == "coinbasepro"


def test_enum_value_is_correct_for_kucoin():
    assert Exchange.KUCOIN.value == "kucoin"


def test_enum_value_is_correct_for_dummy():
    assert Exchange.DUMMY.value == "dummy"


def test_converting_string_to_enum():
    assert Exchange("binance") == Exchange.BINANCE
    assert Exchange("coinbasepro") == Exchange.COINBASEPRO
    assert Exchange("kucoin") == Exchange.KUCOIN


def test_exception_thrown_when_invalid_value():
    with pytest.raises(ValueError) as exc_info:
        Exchange("xxx")
    assert exc_info.type is ValueError
    assert exc_info.value.args[0] == "'xxx' is not a valid Exchange"
