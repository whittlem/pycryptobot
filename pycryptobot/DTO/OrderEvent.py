from dataclasses import dataclass
from pycryptobot.DTO.EventInterface import EventAbstract
from ..models.exchange.Granularity import Granularity


@dataclass
class BuyEvent(EventAbstract):
    current_df_index: str
    market: str
    granularity: Granularity
    price: float
    action: str
    name: str = 'BuyEvent'

    def repr_json(self):
        return {
            'current_df_index': self.current_df_index,
            'market': self.market,
            'granularity': self.granularity.value,
            'price': self.price,
            'action': self.action,
            'name': self.name,
        }


@dataclass
class SellEvent(EventAbstract):
    current_df_index: str
    market: str
    granularity: Granularity
    price: float
    buy_at: float
    action: str
    margin: float
    delta: float
    profit: float
    margin_fee: float
    name: str = 'SellEvent'

    def repr_json(self):
        return {
            'current_df_index': self.current_df_index,
            'market': self.market,
            'granularity': self.granularity.value,
            'price': self.price,
            'buy_at': self.buy_at,
            'action': self.action,
            'margin': self.margin,
            'delta': self.delta,
            'profit': self.profit,
            'margin_fee': self.margin_fee,
            'name': self.name,
        }
