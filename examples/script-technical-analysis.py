from models.PyCryptoBot import PyCryptoBot
from models.Trading import TechnicalAnalysis

app = PyCryptoBot()
df = self.get_historical_data(app.market, self.granularity)

model = TechnicalAnalysis(df)
model.add_atr(14)
df = model.get_df()
print (df)