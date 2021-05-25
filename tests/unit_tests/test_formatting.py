import functools
import sys
import pytest

sys.path.append('.')
from models.PyCryptoBot import truncate


@pytest.mark.parametrize(('f', 'n', 'expected'), [
    (1.234567,    4, '1.2345'),
    (12.34567,    4, '12.3456'),
    (1.234567,    3, '1.234'),
    (1.23,        4, '1.2300'),
    # corner cases
    (0.00009,     4, '0.0001'),
    (0.00001,     4, '0.0000'),
    ('0.01',      4, '0.0'),
    (1.1234,    '4', '0.0')
])
def test_truncate(f, n, expected):
    assert truncate(f, n) == expected

    # make sure nothing breaks compatibility with partial()
    assert functools.partial(truncate, n=n)(f) == expected
