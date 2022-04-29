import pickle


class PositionMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    def __new__(cls, name, bases, attrs, position=None):
        # `Position` base class `__slots__` are defined in the class definition
        if bases:
            attrs['__slots__'] = position

        return super().__new__(cls, name, bases, attrs)


class Position(metaclass=PositionMeta):

    __slots__ = ('owner', 'label')


    def __init__(self, owner=None, label=None, **kwargs):
        self.owner = owner
        self.label = label

        for a in self.__slots__:
            setattr(self, a, 0)

        for k, v in kwargs.items():
            if k in self.__slots__:
                setattr(self, k, v)

    def __getstate__(self):
        values = {k:getattr(self, k) for k in self.__slots__}
        return values

    def __setstate__(self, values):
        for k,v in values.items():
            setattr(self, k, v)

    def __repr__(self):
        _repr = (f'{k}={getattr(self, k, None)}' for k in self.__slots__)
        return f'{self.owner.__class__.__name__}({self.label}): {", ".join(_repr)}'


class PositionMaker:
    __slots__ = ('label', 'attrs', '_Position')

    def __init__(self, label, attrs):
        self.label = label
        self.attrs = attrs
        self._Position = type('_Position', (Position, ), dict(), position=attrs)
        pass

    def __getstate__(self):
        values = {k:getattr(self, k) for k in self.__slots__}
        return values

    def __setstate__(self, values):
        for k,v in values.items():
            setattr(self, k, v)

    def make(self, **kwargs):
        position = self._Position(self, label=self.label, **kwargs)
        return position


P = PositionMaker(label='label-1', attrs=('x', 'y', 'z'))
n = P.make(x=1, y=2, z=3)

# n = P.make(x=1, y=2, z=3)

# pickle.dumps(n)
pass


