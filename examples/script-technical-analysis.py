import sys

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.Trading import TechnicalAnalysis  # noqa: E402

app = PyCryptoBot()
df = app.get_historical_data(app.market, app.granularity, None)

model = TechnicalAnalysis(df)
model.add_atr(14)
df = model.get_df()
print(df)
