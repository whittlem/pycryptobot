"""Analyses the output from simulations.py"""

import pandas as pd

try:
    df = pd.read_csv('experiments/experiments.csv')
    # count, mean, std, min, 25%, 50%, 75%, max from DataFrame
    print (df['result'].describe())
    # returns the success rate (non-negative is positive)
    print (str(len(df[df['result'] >= 0]) / len(df) * 100) + '% success')
except OSError:
    raise SystemExit('Unable to open: experiments/experiments.csv')