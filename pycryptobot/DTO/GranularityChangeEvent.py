from dataclasses import dataclass
from .EventInterface import EventAbstract


@dataclass
class GranularityChange(EventAbstract):
    new: int
    new_text: str
    old: int
    old_text: str
    name: str = 'GranularityChange'

