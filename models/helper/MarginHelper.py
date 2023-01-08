"""Financial margin functions"""

from stat import UF_APPEND
from views.PyCryptoBot import RichText


def calculate_margin(
    buy_size: float = 0.0,
    buy_filled: int = 0.0,
    buy_price: int = 0.0,
    buy_fee: float = 0.0,
    sell_percent: float = 100,
    sell_price: float = 0.0,
    sell_fee: float = 0.0,
    sell_taker_fee: float = 0.0,
    app: object = None,
) -> float:
    """
    Calculate the margin for a given trade.
    """

    PRECISION = 8

    if app is not None and app.debug:
        RichText.notify(f"buy_size: {buy_size}", app, "debug")  # buy_size is quote currency (before fees)
        RichText.notify(f"buy_filled: {buy_filled}", app, "debug")  # buy_filled is base currency (after fees)
        RichText.notify(f"buy_price: {buy_price}", app, "debug")  # buy_price is quote currency
        RichText.notify(f"buy_fee: {buy_fee}", app, "debug")  # buy_fee is quote currency

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
        RichText.notify("buy_size is 0.0 and would result in a divide by 0 error", app, "error")
        return 0, 0, 0

    # calculate margin
    margin = round((profit / buy_size) * 100, PRECISION)  # TODO: division by zero check

    if app is not None and app.debug:
        RichText.notify(f"sell_size: {sell_size}", app, "debug")  # sell_size is quote currency (before fees)
        RichText.notify(f"sell_filled: {sell_filled}", app, "debug")  # sell_filled is quote currency (after fees)
        RichText.notify(f"sell_price: {sell_price}", app, "debug")  # sell_price is quote currency
        RichText.notify(f"sell_fee: {sell_fee}", app, "debug")  # sell_fee is quote currency
        RichText.notify(f"profit: {profit}", app, "debug")
        RichText.notify(f"margin: {margin}", app, "debug")

    return margin, profit, sell_fee
