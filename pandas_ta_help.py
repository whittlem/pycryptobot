#from models.PyCryptoBot import PyCryptoBot
#from models.Trading import TechnicalAnalysis
#from models.TradingAccount import TradingAccount
#from models.AppState import AppState
import numpy as np
import pandas as pd
try:
    import pandas_ta as ta
    use_pandas_ta = True
except ImportError:
    use_pandas_ta = False
try:
    import talib
    use_talib = True
except ImportError:
    use_talib = False

#app = PyCryptoBot()
#df = app.getHistoricalData(app.getMarket(), app.getGranularity())
df = pd.DataFrame()

# Main Help
#help(ta)

# List Indicators
#df.ta.indicators()

# Help for specific item
help(ta.wma)

#ta.cdl_pattern(name="doji")

#df = df.ta.cdl_pattern(name="doji")

#print(self.df)
#print(self.df.shift())

#print (df)

exit()
