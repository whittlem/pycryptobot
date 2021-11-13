from dataclasses import dataclass
from .EventInterface import EventAbstract
from ..models.exchange.Granularity import Granularity


@dataclass
class GranularityChange(EventAbstract):
    new: Granularity
    old: Granularity
    name: str = 'GranularityChange'

    def repr_json(self):
        return {
            "new": self.new.value,
            "old": self.old.value,
            "name": self.name,
        }
