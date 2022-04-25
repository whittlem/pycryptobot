from enum import Enum


class Granularity(Enum):
    ONE_MINUTE = 60, "1m", "1min", "1T"
    FIVE_MINUTES = 300, "5m", "5min", "5T"
    FIFTEEN_MINUTES = 900, "15m", "15min", "15T"
    THIRTY_MINUTES = 1800, "30m", "30min", "30T"
    ONE_HOUR = 3600, "1h", "1hour", "1H"
    SIX_HOURS = 21600, "6h", "6hour", "6H"
    ONE_DAY = 86400, "1d", "1day", "1D"

    def __init__(self, integer, short, medium, frequency):
        self.integer = integer
        self.short = short
        self.medium = medium
        self.frequency = frequency

    @staticmethod
    def convert_to_enum(value):
        for granularity in Granularity:
            for enum_value in granularity.value:
                if enum_value == value:
                    return granularity
        raise ValueError("Invalid Granularity")

    @property
    def to_short(self):
        return self.short

    @property
    def to_integer(self):
        return self.integer

    @property
    def to_medium(self):
        return self.medium

    @property
    def get_frequency(self):
        return self.frequency
