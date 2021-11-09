from dataclasses import dataclass
from pycryptobot.DTO.EventInterface import EventAbstract


@dataclass
class BuyEvent(EventAbstract):
    current_df_index: str
    market: str
    granularity: str
    price: float
    action: str
    name: str = 'OrderEvent'


@dataclass
class SellEvent(EventAbstract):
    current_df_index: str
    market: str
    granularity: str
    price: float
    buy_at: float
    action: str
    margin: float
    delta: float
    profit: float
    margin_fee: float
    name: str = 'OrderEvent'
