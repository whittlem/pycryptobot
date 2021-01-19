"""Analyses the output from simulations.py"""

import pandas as pd

try:
    df = pd.read_csv('experiments/experiments.csv')
    # count, mean, std, min, 25%, 50%, 75%, max from DataFrame
    print (df['result'].describe())
    # returns the success rate (non-negative is positive)
    print (len(df[df['result'] == 0]), 'out of', len(df), 'had no buy opportunties')
    print (len(df[df['result'] < 0]), 'out of', len(df), 'resulted was a loss')
    print (len(df[df['result'] > 0]), 'out of', len(df), 'resulted in profit')
    print (str(len(df[df['result'] >= 0]) / len(df) * 100) + '% success')
    print ('sum of wins', df[df['result'] > 0]['result'].sum())
    print ('sum of losses', df[df['result'] < 0]['result'].sum())
    print ('earnings (wins-losses):', df['result'].sum())
except OSError:
    raise SystemExit('Unable to open: experiments/experiments.csv')