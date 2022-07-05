from models.PyCryptoBot import PyCryptoBot
# from models.Trading import TechnicalAnalysis
# from models.TradingAccount import TradingAccount
# from models.AppState import AppState

app = PyCryptoBot()
df = app.getHistoricalData(app.getMarket(), app.getGranularity(), None)
print(df)
