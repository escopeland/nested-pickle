import pickle
# import dill as pickle

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

    def __eq__(self, other):
        return all(getattr(self, s) == getattr(other, s) for s in self.__slots__)

    def __repr__(self):
        _repr = (f'{k}={getattr(self, k, None)}' for k in self.__slots__)
        return f'{self.owner.__class__.__name__}({self.label}): {", ".join(_repr)}'


class Maker:
    __slots__ = ('label')

    def __new__(cls, *args, **kwargs):
        position = kwargs.get('attrs')
        if position:
            cls._Position1 = type('Maker._Position1', (Position, ), dict(), position=position)
        return super().__new__(cls)

    def __init__(self, label, attrs):
        self.label = label

    def make(self, **kwargs):
        position = self.__class__._Position1(self, label=self.label, **kwargs)
        return position


P = Maker(label='label-1', attrs=('x', 'y', 'z'))
n = P.make(x=1, y=2, z=3)

pn = pickle.dumps(n)
un = pickle.loads(pn)
if n == un:
    print('match!')
pass


print('done!')