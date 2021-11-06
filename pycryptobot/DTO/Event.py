from dataclasses import dataclass
import json
import pandas

@dataclass()
class BaseEventDTO:
    df_index: str
    market: str
    bullbeear: str
    granularity: str
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
        return self.__dict__

@dataclass()
class EventDTO:
    base_event: BaseEventDTO
    df_high: float
    df_low: float
    swing: float
    curr_prie: float
    range_start: pandas.Timestamp
    range_end: pandas.Timestamp
    margin: float = None
    delta: float = None

    def set_margin(self, margin: float):
        self.margin = margin

    def set_delta(self, delta: float):
        self.delta = delta

    def reprJSON(self):
        return {
            'base_event': self.base_event.__dict__,
            'df_high': self.df_high,
            'df_low': self.df_low,
            'swing': self.swing,
            'curr_prie': self.curr_prie,
            'range_start': self.range_start.strftime('%Y-%m-%d %H:%M:%S'),
            'range_end': self.range_end.strftime('%Y-%m-%d %H:%M:%S'),
            'margin': self.margin,
            'delta': self.delta,
        }

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj,'reprJSON'):
            return obj.reprJSON()
        else:
            return json.JSONEncoder.default(self, obj)