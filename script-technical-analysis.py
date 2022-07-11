from models.PyCryptoBot import PyCryptoBot
from models.Trading import TechnicalAnalysis

app = PyCryptoBot()
df = app.get_historical_data(app.market, app.granularity)

model = TechnicalAnalysis(df)
model.addATR(14)
df = model.getDataFrame()
print (df)