from models.PyCryptoBot import PyCryptoBot

app = PyCryptoBot(exchange='coinbasepro')
print (app.exchange)

app = PyCryptoBot(exchange='binance')
print (app.exchange)

app = PyCryptoBot(exchange='dummy')
print (app.exchange)

app = PyCryptoBot()
print (app.exchange)