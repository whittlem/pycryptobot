from models.PyCryptoBot import PyCryptoBot
# from models.Trading import TechnicalAnalysis
# from models.TradingAccount import TradingAccount
# from models.AppState import AppState

app = PyCryptoBot()
df = self.get_historical_data(app.market, self.granularity, None)
print(df)
