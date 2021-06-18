from models.PyCryptoBot import PyCryptoBot

app = PyCryptoBot(exchange='coinbasepro')
print (app.getExchange())

app = PyCryptoBot(exchange='binance')
print (app.getExchange())

app = PyCryptoBot(exchange='dummy')
print (app.getExchange())

app = PyCryptoBot()
print (app.getExchange())