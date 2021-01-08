import pandas as pd

try:
    df = pd.read_csv('experiments/experiments.csv')
    print (df['result'].describe())
    print (str(len(df[df['result'] >= 0]) / len(df) * 100) + '% success')
except OSError:
    raise SystemExit('Unable to open: experiments/experiments.csv')