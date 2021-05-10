from models.PyCryptoBot import PyCryptoBot

app = PyCryptoBot()

### BINANCE ###

print ("BINANCE:\n")

last_buy_size = 177.2
last_buy_filled = 88.043592
last_buy_price = 0.4968600000000001
last_buy_fee = 0.22 

print ('buy_size:', last_buy_size)
print ('buy_filled:', last_buy_filled)
print ('buy_price:', last_buy_price)
print ('buy_fee:', last_buy_fee, "\n")

price = 0.48001
sell_size = (app.getSellPercent() / 100) * ((price / last_buy_price) * last_buy_size)
sell_fee = round(sell_size * app.getTakerFee(), 2)
sell_filled = sell_size - sell_fee

print ('sell_percent:', app.getSellPercent(), "\n")

print ('sell_size:', sell_size)
print ('sell_price:', price)
print ('sell_fee:', sell_fee)
print ('sell_filled:', sell_filled, "\n")

buy_value = last_buy_size + last_buy_fee
sell_value = sell_size - sell_fee
profit = sell_value - buy_value

margin = (profit / last_buy_size) * 100

print ('margin:', margin, "\n")

### COINBASE PRO ###

print ("COINBASE PRO:\n")

last_buy_size = 1500.0
last_buy_filled = 1.45481998
last_buy_price = 1029.0
last_buy_fee = 2.99 

print ('buy_size:', last_buy_size)
print ('buy_filled:', last_buy_filled)
print ('buy_price:', last_buy_price)
print ('buy_fee:', last_buy_fee, "\n")

price = 987.89
sell_size = (app.getSellPercent() / 100) * ((price / last_buy_price) * last_buy_size)
sell_fee = round(sell_size * app.getTakerFee(), 2)
sell_filled = sell_size - sell_fee

print ('sell_percent:', app.getSellPercent(), "\n")

print ('sell_size:', sell_size)
print ('sell_price:', price)
print ('sell_fee:', sell_fee)
print ('sell_filled:', sell_filled, "\n")

buy_value = last_buy_size + last_buy_fee
sell_value = sell_size - sell_fee
profit = sell_value - buy_value

margin = (profit / last_buy_size) * 100

print ('margin:', margin, "\n")