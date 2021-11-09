from dataclasses import dataclass

from pycryptobot.DTO.EventInterface import EventAbstract


@dataclass
class ChangeActionEvent(EventAbstract):
    old: str
    new: str
    market: str
    name: str = 'ChangeActionEvent'

