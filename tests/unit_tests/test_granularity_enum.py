import sys

import pytest

from models.exchange.Granularity import Granularity

sys.path.append('.')


def test_enum_can_be_created_from_values():
    assert Granularity.convert_to_enum(60) == Granularity.ONE_MINUTE
    assert Granularity.convert_to_enum("1m") == Granularity.ONE_MINUTE
    assert Granularity.convert_to_enum("1min") == Granularity.ONE_MINUTE
    assert Granularity.convert_to_enum("1T") == Granularity.ONE_MINUTE


def test_exception_thrown_when_invalid_value():
    with pytest.raises(ValueError) as exc_info:
        Granularity(10000000)
    assert exc_info.type is ValueError
    assert exc_info.value.args[0] == "10000000 is not a valid Granularity"
