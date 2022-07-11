from models.PyCryptoBot import PyCryptoBot
# from models.Trading import TechnicalAnalysis
# from models.TradingAccount import TradingAccount
# from models.AppState import AppState

app = PyCryptoBot()
df = app.get_historical_data(app.market, app.granularity, None)
print(df)
