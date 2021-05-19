def calculate_margin(buy_size: float = 0.0, buy_filled: int = 0.0, buy_price: int = 0.0, buy_fee: float = 0.0,
                     sell_percent: float = 100, sell_price: float = 0.0, sell_fee: float = 0.0,
                     sell_taker_fee: float = 0.0, debug: bool = False, exchange: str = 'coinbasepro') -> float:
    
    if debug is True:
        print(f'buy_size: {buy_size}') #buy_size for CB is quote currency, for binance is base currency
        print(f'buy_filled: {buy_filled}') #buy_filled for CB is base currency, for binance is quote currency
        print(f'buy_price: {buy_price}') #buy_price for CB is quote currency, for binance is quote currency
        print(f'buy_fee: {buy_fee}', "\n") #buy_fee for CB is quote currency, for binance is quote currency

    #for CB buy_size represents the quote currency value of the buy including fees and buy_filled represents the base currency size of the buy
    #for Binance buy_filled represents the quote currency value of the buy including fees and buy_size represents the base currency size of the buy

    if exchange == 'coinbasepro':
        #sell_size in quote currency by multiplying current price by buy_filled in base currency
        sell_size = round((sell_percent / 100) * (sell_price  * buy_filled), 8)

        #calculate sell_fee in quote currency
        if sell_fee == 0.0 and sell_taker_fee > 0.0:
            sell_fee = round((sell_size * sell_taker_fee), 8)
        
        #calculate sell_value after fees in quote currency
        sell_value = round(sell_size - sell_fee, 8)

        #profit is difference between sell_value without fees and buy_size including fees in quote currency
        profit = round(sell_value - buy_size, 2)

        #calculate margin
        margin = round((profit / buy_size) * 100, 2)

    else:
        #sell size in quote currency by multiplying current price by buy_size in base currency
        sell_size = round((sell_percent / 100) * (sell_price  * buy_size), 8)

        #calculate sell fee in quote currency
        if sell_fee == 0.0 and sell_taker_fee > 0.0:
            sell_fee = round(sell_size * sell_taker_fee, 8)
        
        #calculate sell_value after fees in quote currency
        sell_value = round(sell_size - sell_fee, 8)
        
        #profit is difference between sell_value and buy_filled in quote currency
        profit = round(sell_value - buy_filled, 2)
        
        #calculate margin
        margin = round((profit / buy_filled) * 100, 2)
         
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
