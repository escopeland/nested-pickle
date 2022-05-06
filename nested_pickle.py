import pickle
import types
import pprint
import json
from random import randbytes
from imports.time_utils import timer


pp = pprint.PrettyPrinter(indent=2)

def get_attrs(obj):
    return (a for a in dir(obj) if
            not a.startswith('__') and not a.endswith('__') and
            not isinstance(getattr(obj, a, None), types.MethodType))

def get_target(state, attr):
    cls = state[attr]['__class__'].split('.')
    target = globals()[cls.pop(0)]
    for attr in cls:
        target = getattr(target, attr)
    return target()


class PositionMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    def __new__(cls, name, bases, namespace, attrs=None):
        # `Position` base class `__slots__` are defined in the class definition
        if bases:
            namespace['__slots__'] = attrs

        return super().__new__(cls, name, bases, namespace)


class Position(metaclass=PositionMeta):
    __slots__ = ('label') # Need to know owner since it's dynamically set!

    def __init__(self, label=None, **kwargs):
        self.label = label

        for a in self.__slots__:
            setattr(self, a, 0)

        for k, v in kwargs.items():
            setattr(self, k, v) # AttributeError on write to non-existent slot

    def __getstate__(self):
        state = dict()
        state['__class__'] = self.__class__.__name__ # used by get_target()
        for attr in get_attrs(self):
            value = getattr(self, attr, None) # `None` traps for unset `__slots__`
            state[attr] = value
        return state

    def __setstate__(self, state):
        __class__ = state.pop('__class__') # used by get_target()
        for attr in get_attrs(self):
            setattr(self, attr, state.pop(attr))

    def __eq__(self, other):
        return all(getattr(self, s) == getattr(other, s) for s in self.__slots__)

    def __repr__(self):
        _repr = (f'{k}={getattr(self, k, None)}' for k in self.__slots__)
        return f"{self.__class__.__name__.split('.')[0]}({self.label}): {', '.join(_repr)}"


class History:
    # `__owner__` is skipped by __getstate__ and __setstate__ since it's a
    # dunder attribute. That's OK because `owner` is passed in History's
    # `__init__()`, which gets called by the parent <class Holding> object's
    # metaclass at the time of class construction. If this were not the case,
    # then I'd have to rename `__owner__` to something without dunders so that
    # __getstate__ and __setstate__ would pick it up.

    __slots__ = ('__owner__', 'id', 'position')

    def __init__(self, owner): # All slots require initialization
        self.position = None
        self.__owner__ = owner
        self.id = 0

    def make(self, **kwargs):
        self.id += 1
        label = 'label-' + str(self.id)
        self.position = self.__owner__.__Position__(label=label, **kwargs)
        return self.position

    def __getstate__(self):
        state = dict()
        state['__class__'] = self.__class__.__name__ # used by get_target()
        for attr in get_attrs(self):
            value = getattr(self, attr, None) # `None` traps for unset `__slots__`
            if isinstance(value, Position):
                state[attr] = value.__getstate__()
            else:
                state[attr] = value
        return state

    def __setstate__(self, state):
        __class__ = state.pop('__class__') # used by get_target()
        for attr in get_attrs(self):
            value = getattr(self, attr, None) # None traps for unset `__slots__`
            if attr == 'position' and value is None and state[attr]:
                # `value` was dynamically created: rebuild it
                value = get_target(state, attr)
                setattr(self, attr, value) # attach the new object to this one
            if isinstance(value, Position):
                value.__setstate__(state.pop(attr))
            else:
                setattr(self, attr, state.pop(attr))


class BaseMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}


class BaseHolding(metaclass=BaseMeta):
    __slots__ = ('holdings', 'history')

    def __new__(cls, *args, **kwargs):
        __pos_name__ = '.'.join(c.__name__ for c in reversed(cls.__mro__[:-2])) + '.__Position__'
        cls.__Position__ = type(__pos_name__, (Position, ), dict(), attrs=cls.__attrs__)
        instance = super().__new__(cls)
        instance.history = History(cls)
        instance.holdings = None
        return instance


    def __getstate__(self):
        state = dict()
        state['__class__'] = self.__class__.__name__ # used by get_target()
        for attr in get_attrs(self):
            value = getattr(self, attr, None) # None traps for unset `__slots__`
            if isinstance(value, (BaseHolding, History)):
                state[attr] = value.__getstate__()
            else:
                state[attr] = value
        return state

    def __setstate__(self, state):
        __class__ = state.pop('__class__')  # used by get_target()
        for attr in get_attrs(self):
            value = getattr(self, attr, None) # None traps for unset `__slots__`
            if attr in ('holdings', 'history') and value is None and state[attr]:
                # `value` was dynamically created: rebuild it
                value = get_target(state, attr)
                setattr(self, attr, value) # attach the new object to this one
            if isinstance(value, (BaseHolding, History)):
                value.__setstate__(state.pop(attr))
            else:
                setattr(self, attr, state.pop(attr))


class Holding(BaseHolding):
    __attrs__ = ('x', 'y', 'z')
    __slots__ = ('data')

    def __init__(self):
        self.holdings = SubHolding()
        self.data = randbytes(1)


class SubHolding(BaseHolding):
    __attrs__ = ('a', 'b')

    def __init__(self):
        self.holdings = SubSubHolding()


class SubSubHolding(BaseHolding):
    __attrs__ = ('alpha', 'beta', 'gamma', 'delta')


if __name__ == '__main__':
    h1 = Holding()
    h2 = Holding()
    h3 = Holding()

    h1.history.make(x=1, y=2, z=3)
    h1.holdings.history.make(a=4, b=5)
    h1.holdings.holdings.history.make(alpha='alpha', beta='beta', gamma='gamma', delta='delta')

    with timer('Directly serialization/deserialization'):
        h2.__setstate__(h1.__getstate__())
    with timer('Pickle serialization/deserialization'):
        h3 = pickle.loads(pickle.dumps(h2))

    if h1.history.position == h3.history.position:
        print('Successhul holdings rebuild!')
    if h1.holdings.history.position == h3.holdings.history.position:
        print('Successful sub-holdings rebuild!')
    if h1.holdings.holdings.history.position == h3.holdings.holdings.history.position:
        print('Successful sub-sub-holdings rebuild!')
    pass
