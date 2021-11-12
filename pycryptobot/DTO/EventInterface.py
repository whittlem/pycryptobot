

class EventInterface:
    name: str

    """Export to json function"""
    def repr_json(self):
        pass


class EventAbstract(EventInterface):

    def repr_json(self):
        return self.__dict__
