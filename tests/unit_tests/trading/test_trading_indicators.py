import sys
import pandas as pd
from numpy import around, round, float64, ceil

sys.path.append(".")
# pylint: disable=import-error
from models.Trading import TechnicalAnalysis


def calculate_mean_on_range(start, end, list) -> float64:
    """
    Calculates the mean on a range of values
    """
    return round(float(sum(list[start:end]) / (end - start)), 4)


def calculate_percentage_evol(start, end) -> float64:
    """
    Calculates the evolution percentage for 2 values
    """
    return end / start - 1
