from dataclasses import dataclass
from .EventInterface import EventAbstract

from pycryptobot.models.exchange.ExchangesEnum import Exchange


@dataclass
class StartEvent(EventAbstract):
    exchange: Exchange
    action: str
    market: str
    granularity: int
    smartswitch: bool
    name: str = "StartEvent"

    def repr_json(self):
        return {
            'exchange': self.exchange.value,
            'action': self.action,
            'market': self.market,
            'granularity': self.granularity,
            'smartswitch': self.smartswitch,
            'name': self.name
        }

@dataclass
class StateChange(EventAbstract):
    action_text: str
    datetime: str
    market: str
    name: str = "StateChange"
