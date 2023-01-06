import sys

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402
from models.Trading import TechnicalAnalysis  # noqa: E402

app = PyCryptoBot()
df = app.get_historical_data(app.market, app.granularity, None)

model = TechnicalAnalysis(df, app=app)
# model.add_elder_ray_index()
# df = model.get_df()
# print(df)

# model.add_support_resistance_levels()
# print(model.get_df())

# model.add_support_resistance_levels()
# model.print_support_resistance_levels_v2()

# model.add_bollinger_bands(20)
model.add_bbands_buy_signals()
print(model.get_df())
