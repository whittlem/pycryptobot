from models.PyCryptoBot import PyCryptoBot
from models.Trading import TechnicalAnalysis

app = PyCryptoBot()
df = app.getHistoricalData(app.getMarket(), app.getGranularity())

model = TechnicalAnalysis(df)
model.addATR(14)
df = model.getDataFrame()
print (df)