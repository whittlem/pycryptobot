"""Reusable utilities"""

import math
from typing import Union


def truncate(f: Union[int, float], n: Union[int, float]) -> str:
    """
    Format a given number ``f`` with a given precision ``n``.
    """

    if not isinstance(f, int) and not isinstance(f, float):
        return "0.0"

    if not isinstance(n, int) and not isinstance(n, float):
        return "0.0"

    if (f < 0.0001) and n >= 5:
        return f"{f:.5f}"

    # `{n}` inside the actual format honors the precision
    return f"{math.floor(f * 10 ** n) / 10 ** n:.{n}f}"


def compare(val1, val2, label="", precision=2):
    """
    Compare two values and print a message if they are not equal.
    """

    if val1 > val2:
        if label == "":
            return f"{truncate(val1, precision)} > {truncate(val2, precision)}"
        else:
            return f"{label}: {truncate(val1, precision)} > {truncate(val2, precision)}"
    if val1 < val2:
        if label == "":
            return f"{truncate(val1, precision)} < {truncate(val2, precision)}"
        else:
            return f"{label}: {truncate(val1, precision)} < {truncate(val2, precision)}"
    else:
        if label == "":
            return f"{truncate(val1, precision)} = {truncate(val2, precision)}"
        else:
            return f"{label}: {truncate(val1, precision)} = {truncate(val2, precision)}"
