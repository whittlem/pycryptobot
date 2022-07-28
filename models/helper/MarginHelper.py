
"""Financial margin functions"""

from models.helper.LogHelper import Logger


def calculate_margin(buy_size: float = 0.0, buy_filled: int = 0.0, buy_price: int = 0.0, buy_fee: float = 0.0,
                     sell_percent: float = 100, sell_price: float = 0.0, sell_fee: float = 0.0,
                     sell_taker_fee: float = 0.0) -> float:
    """
    Calculate the margin for a given trade.
    """

    PRECISION = 8

    Logger.debug(f'buy_size: {buy_size}')  # buy_size is quote currency (before fees)
    Logger.debug(f'buy_filled: {buy_filled}')  # buy_filled is base currency (after fees)
    Logger.debug(f'buy_price: {buy_price}')  # buy_price is quote currency
    Logger.debug(f'buy_fee: {buy_fee}')  # buy_fee is quote currency

    # sell_size is quote currency (before fees) - self.price * buy_filled
    sell_size = round((sell_percent / 100) * (sell_price * buy_filled), PRECISION)

    # calculate sell_fee in quote currency, sell_fee is actual fee, sell_taker_fee is the rate
    if sell_fee == 0.0 and sell_taker_fee > 0.0:
        sell_fee = round((sell_size * sell_taker_fee), PRECISION)

    # calculate sell_filled after fees in quote currency
    sell_filled = round(sell_size - sell_fee, PRECISION)

    # profit is the difference between buy_size without fees and sell_filled with fees
    profit = round(sell_filled - buy_size, PRECISION)

    # error handling
    if buy_size == 0.0:
        Logger.error('buy_size is 0.0 and would result in a divide by 0 error')
        return 0, 0, 0

    # calculate margin
    margin = round((profit / buy_size) * 100, PRECISION)  # TODO: division by zero check

    Logger.debug(f'sell_size: {sell_size}')  # sell_size is quote currency (before fees)
    Logger.debug(f'sell_filled: {sell_filled}')  # sell_filled is quote currency (after fees)
    Logger.debug(f'sell_price: {sell_price}')  # sell_price is quote currency
    Logger.debug(f'sell_fee: {sell_fee}')  # sell_fee is quote currency
    Logger.debug(f'profit: {profit}')
    Logger.debug(f'margin: {margin}')

    return margin, profit, sell_fee
