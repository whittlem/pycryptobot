def calculate_margin(buy_size: float = 0.0, buy_filled: int = 0.0, buy_price: int = 0.0, buy_fee: float = 0.0,
                     sell_percent: float = 100, sell_price: float = 0.0, sell_fee: float = 0.0,
                     sell_taker_fee: float = 0.0, debug: bool = False, exchange: str = 'coinbasepro') -> float:
    if debug is True:
        print(f'buy_size: {buy_size}')
        print(f'buy_filled: {buy_filled}')
        print(f'buy_price: {buy_price}')
        print(f'buy_fee: {buy_fee}', "\n")

    sell_size = (sell_percent / 100) * ((sell_price / buy_price) * buy_size)

    if sell_fee == 0.0 and sell_taker_fee > 0.0:
        sell_fee = sell_size * sell_taker_fee

    if debug is True:
        print(f'sell_size: {sell_size}')
        print(f'sell_price: {sell_price}')
        print(f'sell_fee: {sell_fee}', "\n")

    if exchange == 'coinbasepro':
        buy_value = buy_size + buy_fee
        sell_value = sell_size - sell_fee
        profit = sell_value - buy_value
    else:
        buy_value = buy_price + buy_fee
        sell_value = sell_price - sell_fee
        profit = sell_value - buy_value

    if debug is True:
        print(f'buy_value: {buy_value}')
        print(f'sell_value: {sell_value}')
        print(f'profit: {profit}', "\n")

    margin = (profit / buy_value) * 100

    if debug is True:
        print(f'margin: {margin}', "\n")

    return margin, profit, sell_fee
