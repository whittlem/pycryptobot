import pandas as pd

try:
    df = pd.read_csv('experiments/experiments.csv')
    print (df['result'].describe())
    print (len(df[df['result'] >= 0]))
except OSError:
    raise SystemExit('Unable to open: experiments/experiments.csv')