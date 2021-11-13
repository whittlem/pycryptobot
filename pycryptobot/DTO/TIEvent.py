from dataclasses import dataclass
import json
import pandas

from .EventInterface import EventAbstract
from ..models.exchange.Granularity import Granularity


@dataclass
class TIBaseEvent:
    df_index: str
    market: str
    bullbeear: str
    granularity: Granularity
    price: float
    ema_co_prefix: str
    ema_text: str
    ema_co_suffix: str
    macd_co_prefix: str
    macd_text: str
    macd_co_suffix: str
    obv_prefix: str
    obv_text: str
    obv_suffix: str
    eri_text: str
    action: str
    last_action: str

    def reprJSON(self):
        return {
            'df_index': self.df_index,
            'market': self.market,
            'bullbeear': self.bullbeear,
            'granularity': self.granularity.value,
            'price': self.price,
            'ema_co_prefix': self.ema_co_prefix,
            'ema_text': self.ema_text,
            'ema_co_suffix': self.ema_co_suffix,
            'macd_co_prefix': self.macd_co_prefix,
            'macd_text': self.macd_text,
            'macd_co_suffix': self.macd_co_suffix,
            'obv_prefix': self.obv_prefix,
            'obv_text': self.obv_text,
            'obv_suffix': self.obv_suffix,
            'eri_text': self.eri_text,
            'action': self.action,
            'last_action': self.last_action,
        }


@dataclass
class TIEvent(EventAbstract):
    base_event: TIBaseEvent
    df_high: float
    df_low: float
    swing: float
    curr_prie: float
    range_start: pandas.Timestamp
    range_end: pandas.Timestamp
    margin: float = None
    delta: float = None
    name: str = "TIEvent"

    def set_margin(self, margin: float):
        self.margin = margin

    def set_delta(self, delta: float):
        self.delta = delta

    def repr_json(self):
        return {
            'base_event': self.base_event.reprJSON(),
            'df_high': self.df_high,
            'df_low': self.df_low,
            'swing': self.swing,
            'curr_prie': self.curr_prie,
            'range_start': self.range_start.strftime('%Y-%m-%d %H:%M:%S'),
            'range_end': self.range_end.strftime('%Y-%m-%d %H:%M:%S'),
            'margin': self.margin,
            'delta': self.delta,
            'name': self.name,
        }
