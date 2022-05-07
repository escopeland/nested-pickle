import pickle
# import types
import pprint
import json
# import random
# import string
import time

from imports.time_utils import timer
from itertools import chain

# letters = string.ascii_letters
# rstring = ''.join(random.choice(letters) for i in range(10))
pp = pprint.PrettyPrinter()

class NullClass:
    pass

def get_attrs(obj):
    return chain.from_iterable(getattr(cls, '__slots__', []) for cls in obj.__class__.__mro__)

def get_target(state, attr):
    cls = state[attr]['__class__'].split('.')
    target = globals()[cls.pop(0)]
    for attr in cls:
        target = getattr(target, attr)
    return target()

def get_state(obj):
    state = dict()
    state['__class__'] = obj.__class__.__name__ # used by get_target()
    for attr in get_attrs(obj):
        value = getattr(obj, attr, None) # `None` traps for unset `__slots__`
        cls_keys, cls_vals = obj.__get_nested_classes__()
        if isinstance(value, cls_vals):
            state[attr] = value.__getstate__()
        else:
            state[attr] = value
    return state

def set_state(obj, state): 
    __class__ = state.pop('__class__') # used by get_target()
    for attr in get_attrs(obj):
        value = getattr(obj, attr, None) # None traps for unset `__slots__`
        cls_keys, cls_vals = obj.__get_nested_classes__()
        if attr in cls_keys and value is None and state[attr]:
            # `value` was dynamically created: rebuild it
            value = get_target(state, attr)
            setattr(obj, attr, value) # attach the new object to this one
        if isinstance(value, cls_vals):
            value.__setstate__(state.pop(attr))
        else:
            setattr(obj, attr, state.pop(attr))

def __get_nested_classes__(obj):
    try:
        return obj.__class__.__nested_class_keys__, obj.__class__.__nested_class_vals__
    except:
        nested_classes = obj.__class__.__nested_classes__
        keys = nested_classes.keys()
        vals = tuple(globals()[cls] for cls in nested_classes.values())   
        obj.__class__.__nested_class_keys__, obj.__class__.__nested_class_vals__ = keys, vals
        return keys, vals

def __equal__(self, other):
    return self.__getstate__() == other.__getstate__()

class SerDesMeta(type):
    def __new__(cls, name, bases, namespace):
        if not bases:
            namespace['__getstate__'] = get_state
            namespace['__setstate__'] = set_state
            namespace['__get_nested_classes__'] = __get_nested_classes__
            namespace['__nested_class_keys'] = None
            namespace['__nested_class_vals'] = None
            namespace['__eq__'] = __equal__
        return super().__new__(cls, name, bases, namespace)

class PositionMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    def __new__(cls, name, bases, namespace, attrs=None):
        # `Position` base class `__slots__` are defined in the class definition
        if bases:
            namespace['__slots__'] = attrs

        return super().__new__(cls, name, bases, namespace)

class PositionSerDesMeta(PositionMeta, SerDesMeta):
    pass

class Position(metaclass=PositionSerDesMeta):
    __slots__ = ('label', ) # Need to know owner since it's dynamically set!
    __nested_classes__ = {'null_class': 'NullClass'}

    def __init__(self, label=None, **kwargs):
        self.label = label

        for a in self.__slots__:
            setattr(self, a, 0)

        for k, v in kwargs.items():
            setattr(self, k, v) # AttributeError on write to non-existent slot

    def __repr__(self):
        _repr = (f'{k}={getattr(self, k, None)}' for k in self.__slots__)
        return f"{self.__class__.__name__.split('.')[0]}({self.label}): {', '.join(_repr)}"

class History(metaclass=SerDesMeta):
    # `__owner__` is skipped by __getstate__ and __setstate__ since it's a
    # dunder attribute. That's OK because `owner` is passed in History's
    # `__init__()`, which gets called by the parent <class Holding> object's
    # metaclass at the time of class construction. If this were not the case,
    # then I'd have to rename `__owner__` to something without dunders so that
    # __getstate__ and __setstate__ would pick it up.

    __slots__ = ('__owner__', 'id', 'position')
    __nested_classes__ = {'position': 'Position'}

    def __init__(self, owner): # All slots require initialization
        self.position = None
        self.__owner__ = owner.__name__
        self.id = 0

    def make(self, **kwargs):
        self.id += 1
        label = 'label-' + str(self.id)
        self.position = globals()[self.__owner__].__Position__(label=label, **kwargs)

class BaseMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

class BaseSerDesMeta(BaseMeta, SerDesMeta):
    pass

class BaseHolding(metaclass=BaseSerDesMeta):
    __slots__ = ('holdings', 'history')
    __nested_classes__ = {'holdings': 'BaseHolding', 'history': 'History'}

    def __new__(cls, *args, **kwargs):
        __pos_name__ = '.'.join(c.__name__ for c in reversed(cls.__mro__[:-2])) + '.__Position__'
        cls.__Position__ = type(__pos_name__, (Position, ), dict(), attrs=cls.attrs)
        instance = super().__new__(cls)
        instance.history = History(cls)
        instance.holdings = getattr(cls, 'holding_type', lambda :None)()
        return instance

class SubSubHolding(BaseHolding):
    attrs = ('alpha', 'beta', 'gamma', 'delta')

class SubHolding(BaseHolding):
    attrs = ('a', 'b')
    holding_type = SubSubHolding

class Holding(BaseHolding):
    attrs = ('x', 'y', 'z')
    holding_type = SubHolding


if __name__ == '__main__':
    h1 = Holding()
    h2 = Holding()
    h3 = Holding()
    h4 = Holding()

    h1.history.make(x=1, y=2, z=3)
    h1.holdings.history.make(a=4, b=5)
    h1.holdings.holdings.history.make(alpha='alpha', beta='beta', gamma='gamma', delta='delta')

    print(f'Serdes test ')
    with timer('    Test: sleeping 1 second completed'):
        time.sleep(0.5)
    with timer('    Directly serdes completed'):
        h2.__setstate__(h1.__getstate__())
    with timer('    Pickle serdes completed'):
        h3 = pickle.loads(pickle.dumps(h2))
    with timer('    Chained JSON and Direct serdes completed'):
        h4.__setstate__(json.loads(json.dumps(h1.__getstate__())))

    assert h1 == h2
    assert h1 == h3
    assert h1 == h4

    pass
