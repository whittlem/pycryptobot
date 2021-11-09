

class EventInterface:
    name: str

    """Export to json function"""
    def reprJSON(self):
        pass


class EventAbstract(EventInterface):

    def reprJSON(self):
        return self.__dict__