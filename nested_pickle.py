import pickle
# import types
from pprint import pprint
import json
# import random
# import string
import time

from imports.time_utils import timer
from itertools import chain

# letters = string.ascii_letters
# rstring = ''.join(random.choice(letters) for i in range(10))
# pprint = pprint.PrettyPrinter()

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
        cls_keys, cls_vals = obj.get_nested_classes()
        if isinstance(value, cls_vals):
            state[attr] = value.__getstate__()
        else:
            state[attr] = value
    return state

def set_state(obj, state): 
    __class__ = state.pop('__class__') # used by get_target()
    for attr in get_attrs(obj):
        value = getattr(obj, attr, None) # None traps for unset `__slots__`
        cls_keys, cls_vals = obj.get_nested_classes()
        if attr in cls_keys and value is None and state[attr]:
            # `value` was dynamically created: rebuild it
            value = get_target(state, attr)
            setattr(obj, attr, value) # attach the new object to this one
        if isinstance(value, cls_vals):
            value.__setstate__(state.pop(attr))
        else:
            setattr(obj, attr, state.pop(attr))

def get_nested_classes(obj):
    try:
        return obj.__class__.nested_class_keys, obj.__class__.nested_class_vals
    except:
        nested_classes = getattr(obj.__class__, 'nested_classes', {'null_class': 'NullClass'})
        keys = nested_classes.keys()
        vals = tuple(globals()[cls] for cls in nested_classes.values())   
        obj.__class__.nested_class_keys, obj.__class__.nested_class_vals = keys, vals
        return keys, vals

def __equal__(self, other):
    return self.__getstate__() == other.__getstate__()

class SerDesMeta(type):
    def __new__(cls, name, bases, namespace):
        if not bases:
            namespace['__getstate__'] = get_state
            namespace['__setstate__'] = set_state
            namespace['get_nested_classes'] = get_nested_classes
            namespace['__eq__'] = __equal__
        return super().__new__(cls, name, bases, namespace)

class PositionMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    def __new__(cls, name, bases, namespace, owner=None):
        if bases:
            namespace['__slots__'] = owner.attrs
            namespace['owner'] = owner.__name__

        return super().__new__(cls, name, bases, namespace)

class PositionSerDesMeta(PositionMeta, SerDesMeta):
    pass

class Position(metaclass=PositionSerDesMeta):
    __slots__ = ('label', )

    def __init__(self, label=None, **kwargs):
        self.label = label

        for a in self.__slots__:
            setattr(self, a, 0)

        for k, v in kwargs.items():
            setattr(self, k, v) # AttributeError on write to non-existent slot

    def __repr__(self):
        attr_repr = (f'{k}={getattr(self, k, None)}' for k in self.__slots__)
        return f"{self.owner}({self.label}): {', '.join(attr_repr)}"

class History(metaclass=SerDesMeta):
    __slots__ =      ('position', 'owner', 'id')
    nested_classes = {'position': 'Position'}

    def __init__(self, owner): # All slots require initialization
        self.position = None
        self.owner = owner.__name__
        self.id = 0

    def make(self, **kwargs):
        self.id += 1
        label = 'label-' + str(self.id)
        self.position = globals()[self.owner].Position(label, **kwargs)

class BaseMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

class BaseSerDesMeta(BaseMeta, SerDesMeta):
    pass

class BaseHolding(metaclass=BaseSerDesMeta):
    __slots__ =      ('holdings', 'history')
    nested_classes = {'holdings': 'BaseHolding', 'history': 'History'}

    def __new__(cls, *args, **kwargs):
        cls.Position = type(cls.__name__ + '.Position', (Position, ), dict(), owner=cls)
        self = super().__new__(cls)
        self.history = History(cls)
        self.holdings = getattr(cls, 'holding_type', lambda :None)()
        return self

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
