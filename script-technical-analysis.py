from models.PyCryptoBot import PyCryptoBot
from models.Trading import TechnicalAnalysis

app = PyCryptoBot()
df = self.get_historical_data(app.market, self.granularity)

model = TechnicalAnalysis(df)
model.addATR(14)
df = model.getDataFrame()
print (df)