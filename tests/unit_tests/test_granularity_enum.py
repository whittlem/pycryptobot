import sys

from models.exchange.Granularity import Granularity

sys.path.append('.')


def test_enum_can_be_created_from_values():
    assert Granularity.convert_to_enum(60) == Granularity.ONE_MINUTE
    assert Granularity.convert_to_enum("1m") == Granularity.ONE_MINUTE
    assert Granularity.convert_to_enum("1min") == Granularity.ONE_MINUTE
    assert Granularity.convert_to_enum("1T") == Granularity.ONE_MINUTE
