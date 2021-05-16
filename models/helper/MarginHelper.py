def calculate_margin(buy_size: float = 0.0, buy_filled: int = 0.0, buy_price: int = 0.0, buy_fee: float = 0.0,
                     sell_percent: float = 100, sell_price: float = 0.0, sell_fee: float = 0.0,
                     sell_taker_fee: float = 0.0, debug: bool = False, exchange: str = 'coinbasepro') -> float:
    
    if debug is True:
        print(f'buy_size: {buy_size}') #buy_size for CB is FIAT, for binance is crypto
        print(f'buy_filled: {buy_filled}') #buy_filled for CB is Crypto, for binance is FIAT
        print(f'buy_price: {buy_price}') #buy_price for CB is FIAT, for binance is FIAT
        print(f'buy_fee: {buy_fee}', "\n") #buy_fee for CB is FIAT, for binance is FIAT

    #for CB buy_size represents the FIAT value of the buy including fees and buy_filled represents the Crypto size of the buy
    #for Binance buy_filled represents the FIAT value of the buy including fees and buy_size represents the Crypto size of the buy

    if exchange == 'coinbasepro':
        #sell_size in FIAT by multiplying current price by buy_filled in Crypto
        sell_size = round((sell_percent / 100) * (sell_price  * buy_filled), 2)

        #calculate sell_fee in FIAT
        if sell_fee == 0.0 and sell_taker_fee > 0.0:
            sell_fee = round((sell_size * sell_taker_fee), 2)
        
        #calculate sell_value after fees in FIAT
        sell_value = round(sell_size - sell_fee, 2)

        #profit is difference between sell_value without fees and buy_size including fees in FIAT
        profit = round(sell_value - buy_size, 2)

        #calculate margin
        margin = round((profit / buy_size) * 100, 2)

    else:
        #sell size in FIAT by multiplying current price by buy_size in Crypto
        sell_size = (sell_percent / 100) * (sell_price  * buy_size)

        #calculate sell fee in FIAT
        if sell_fee == 0.0 and sell_taker_fee > 0.0:
            sell_fee = (sell_size /100) * sell_taker_fee
        
        #calculate sell_value after fees in FIAT
        sell_value = sell_size - sell_fee
        
        #profit is difference between sell_value and buy_filled in FIAT
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