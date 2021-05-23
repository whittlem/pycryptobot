def calculate_margin(buy_size: float = 0.0, buy_filled: int = 0.0, buy_price: int = 0.0, buy_fee: float = 0.0,
                     sell_percent: float = 100, sell_price: float = 0.0, sell_fee: float = 0.0,
                     sell_taker_fee: float = 0.0, debug: bool = False) -> float:
    precision = 8

    if debug is True:
        print(f'buy_size: {buy_size}') #buy_size is quote currency,
        print(f'buy_filled: {buy_filled}') #buy_filled is base currency,
        print(f'buy_price: {buy_price}') #buy_price is quote currency, 
        print(f'buy_fee: {buy_fee}', "\n") #buy_fee is quote currency, 

    # buy_size represents the quote currency value of the buy including fees and buy_filled represents the base currency size of the buy

    #sell_size in quote currency by multiplying current price by buy_filled in base currency
    sell_size = round((sell_percent / 100) * (sell_price  * buy_filled), precision)

    #calculate sell_fee in quote currency
    if sell_fee == 0.0 and sell_taker_fee > 0.0:
        sell_fee = round((sell_size * sell_taker_fee), precision)
    
    #calculate sell_value after fees in quote currency
    sell_value = round(sell_size - sell_fee, precision)

    #profit is difference between sell_value without fees and buy_size including fees in quote currency
    profit = round(sell_value - buy_size, precision)

    #calculate margin
    margin = round((profit / buy_size) * 100, precision)

         
    if debug is True:
       
        print(f'sell_size: {sell_size}')
        print(f'sell_price: {sell_price}')
        print(f'sell_fee: {sell_fee}', "\n")

        print(f'buy_with_fees: {buy_size}')
        print(f'sell_with_fees: {sell_size}')
        print(f'sell_minus_fees: {sell_value}')

        print(f'profit: {profit}', "\n")
        print(f'margin: {margin}', "\n")

    return margin, profit, sell_fee
