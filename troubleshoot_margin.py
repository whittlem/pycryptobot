from models.PyCryptoBot import PyCryptoBot

app = PyCryptoBot()

def calculateMargin(buy_size: float=0.0, buy_filled: int=0.0, buy_price: int=0.0, buy_fee: float=0.0, sell_percent: float=100, sell_price: float=0.0, sell_fee: float=0.0, sell_taker_fee: float=0.0, debug: bool=False) -> float:
    if debug is True:
        print (f'buy_size: {buy_size}')
        print (f'buy_filled: {buy_filled}')
        print (f'buy_price: {buy_price}')
        print (f'buy_fee: {buy_fee}', "\n")

    sell_size = (sell_percent / 100) * ((sell_price / buy_price) * buy_size)

    if sell_fee == 0.0 and sell_taker_fee > 0.0:
        #sell_fee = sell_size * sell_taker_fee
        sell_fee = sell_price * sell_taker_fee

    if debug is True:
        print (f'sell_size: {sell_size}')
        print (f'sell_price: {sell_price}')
        print (f'sell_fee: {sell_fee}', "\n")

    #buy_value = buy_size + buy_fee
    #sell_value = sell_size - sell_fee
    #profit = sell_value - buy_value

    buy_value = buy_price + buy_fee
    sell_value = sell_price - sell_fee
    profit = sell_value - buy_value

    if debug is True:
        print (f'buy_value: {buy_value}')
        print (f'sell_value: {sell_value}')
        print (f'profit: {profit}', "\n")

    margin = (profit / buy_value) * 100

    if debug is True:
        print (f'margin: {margin}', "\n")

    return margin, profit, sell_fee

print ("BINANCE:\n")
margin, profit, sell_fee = calculateMargin(buy_size=177.2, buy_filled=88.043592, buy_price=0.4968600000000001, buy_fee=0.22, sell_percent=100, sell_price=0.48001, sell_fee=0.34, debug=True)
#margin, profit, sell_fee = calculateMargin(buy_size=0.08438, buy_filled=31.3454824, buy_price=371.48, buy_fee=0.22, sell_percent=100, sell_price=371.48, sell_taker_fee=app.getTakerFee(), debug=True)

print ("COINBASE PRO:\n")
#margin, profit, sell_fee = calculateMargin(buy_size=1500.0, buy_filled=1.45481998, buy_price=1029.0, buy_fee=2.99, sell_percent=100, sell_price=987.89, sell_fee=2.99, debug=True)
#margin, profit, sell_fee = calculateMargin(buy_size=1500.0, buy_filled=1.45481998, buy_price=1029.0, buy_fee=2.99, sell_percent=100, sell_price=987.89, sell_taker_fee=app.getTakerFee(), debug=True)
margin, profit, sell_fee = calculateMargin(buy_size=1500.0, buy_filled=0.53298323, buy_price=2808.73, buy_fee=2.99, sell_percent=100, sell_price=2849.42, sell_taker_fee=app.getTakerFee(), debug=True)
