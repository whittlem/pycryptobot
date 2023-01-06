import functools
import sys
import pytest

sys.path.append('.')
# pylint: disable=import-error
from utils.PyCryptoBot import truncate as _truncate

@pytest.mark.parametrize(('f', 'n', 'expected'), [
    (1.234567,    4, '1.2345'),
    (12.34567,    4, '12.3456'),
    (1.234567,    3, '1.234'),
    (1.23,        4, '1.2300'),
    (0.00009,     5, '0.00009'),
    # corner cases
    ('0.01',      4, '0.0'),
    (1.1234,    '4', '0.0')
])

def test_truncate(f, n, expected):
    assert _truncate(f, n) == expected

    # make sure nothing breaks compatibility with partial()
    assert functools.partial(_truncate, n=n)(f) == expected
