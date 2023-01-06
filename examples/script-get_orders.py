import sys

sys.path.insert(0, ".")

from controllers.PyCryptoBot import PyCryptoBot  # noqa: E402

app = PyCryptoBot(exchange="coinbasepro")
print(app.exchange)

app = PyCryptoBot(exchange="binance")
print(app.exchange)

app = PyCryptoBot(exchange="dummy")
print(app.exchange)

app = PyCryptoBot()
print(app.exchange)
