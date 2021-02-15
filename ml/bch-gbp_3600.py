import sys
import pandas as pd

sys.path.append('.')
# pylint: disable=import-error
from models.Trading import TechnicalAnalysis
from models.CoinbasePro import PublicAPI

api = PublicAPI()
data = api.getHistoricalData('BCH-GBP', 3600)

ta = TechnicalAnalysis(data)
ta.addAll()

df = ta.getDataFrame()
df.to_csv('ml/data/BCH-GBP_3600.csv', index=False)