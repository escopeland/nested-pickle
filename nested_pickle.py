import json
import pickle
import time
from itertools import chain
from pprint import PrettyPrinter

from imports.time_utils import timer
from utilities import get_slots

pprint = PrettyPrinter(sort_dicts=False).pprint
# class PositionSerDesMeta(PositionMeta, SerDesMeta):
#     pass
# class BaseSerDesMeta(BaseMeta, SerDesMeta):
#     pass


class PositionMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    def __new__(cls, name, bases, namespace, owner=None, attrs=None):
        if bases:
            namespace['owner'] = owner
            namespace['__slots__'] = attrs

        return super().__new__(cls, name, bases, namespace)
        
class Position(metaclass=PositionMeta):
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

    def __getstate__(self):
        state = dict(owner=self.__class__.owner)
        state |= {s:getattr(self, s) for s in get_slots(self)}
        return state

    def __setstate__(self, state):
        self.__class__.owner = state.pop('owner')
        for s in get_slots(self):
            setattr(self, s, state.pop(s))

    def __eq__(self, other):
        return self.__getstate__() == other.__getstate__()

class HistoryMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    def __new__(cls, name, bases, namespace, owner=None, attrs=None):
        if not dict in bases:
            namespace['owner'] = owner
            namespace['Position'] = type(owner + '.Position', (Position, ),
                                         dict(), owner=owner, attrs=attrs)
        return super().__new__(cls, name, bases, namespace)

class History(dict, metaclass=HistoryMeta):

    def create(self, label, **kwargs):
        self[label] = self.__class__.Position(label, **kwargs)

    def __repr__(self):
        return f'History object: {len(self)} instances of type {self.__class__.Position}'

    def __getstate__(self):
        state = dict(owner=self.__class__.owner)
        state |= {k:v.__getstate__() for k,v in self.items()}
        return state

    def __setstate__(self, state):
        self.clear()
        self.__class__.owner = state.pop('owner')
        target = self.__class__.Position
        for k, s in state.items():
            v = target()
            v.__setstate__(s)
            self[k] = v

    def __eq__(self, other):
        return self.__getstate__() == other.__getstate__()


class HoldingsMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    def __new__(cls, name, bases, namespace, owner=None, holding_type=None):
        """ `holding_type` is a sub-class created by BaseMeta. To sub-class
        it again here to be consistent with other metaclasses, i.e.::

            type(owner.__name__ + holding_type.name, (holding_type, ),
                    dict(), owner=owner)

        would require `BaseMeta` to trap for sub-sub-classes. It's easier not
        to bother with that since we don't need a unique sub-sub-class.
        """
        if not dict in bases:
            namespace['owner'] = owner
            namespace['Holding'] = holding_type
            # namespace['Holding'] = type(name + '.holding_type',  (holding_type, ),  dict(),
            #     owner=name)

        return super().__new__(cls, name, bases, namespace)

class Holdings(dict, metaclass=HoldingsMeta):

    def create(self, label):
        # self[label] = self.__class__.Holding(owner=self.__class__.owner)
        self[label] = self.__class__.Holding(owner=self.__class__.owner)

    def __getstate__(self):
        state = dict(owner=self.__class__.owner)
        state |= {k:v.__getstate__() for k,v in self.items()}
        return state

    def __setstate__(self, state):
        self.clear()
        self.__class__.owner = state.pop('owner')
        target = self.__class__.Holding
        for k, s in state.items():
            v = target()
            v.__setstate__(s)
            self[k] = v

    def __eq__(self, other):
        return self.__getstate__() == other.__getstate__()

class BaseMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    def __new__(cls, name, bases, namespace, owner=None):
        if bases:
            namespace['owner'] = owner
            namespace['History']  = type(name + '.History',  (History, ),  dict(),
                owner=name, attrs=namespace['attrs'])
            namespace['Holdings'] = type(name + '.Holdings', (Holdings, ), dict(),
                owner=name, holding_type=namespace.get('holding_type'))
            namespace['__slots__'] = ('history', 'holdings')

        return super().__new__(cls, name, bases, namespace)

class BaseHolding(metaclass=BaseMeta):
    # __slots__ = ('history', 'holdings')

    def __new__(cls, owner=None):
        self = super().__new__(cls)
        if owner is not None: self.__class__.owner = owner
        self.history  = cls.History()
        self.holdings = cls.Holdings()
        return self

    def __getstate__(self):
        state = dict(owner=self.__class__.owner)
        state['history']  = self.history.__getstate__()
        state['holdings'] = self.holdings.__getstate__()
        return state

    def __setstate__(self, state):
        self.__class__.owner = state.pop('owner')
        self.history.__setstate__(state.pop('history'))
        self.holdings.__setstate__(state.pop('holdings'))

    def __eq__(self, other):
        return self.__getstate__() == other.__getstate__()


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

    h1.holdings.create('holding-1')
    h1.holdings['holding-1'].holdings.create('holding-1')
    h1.history.create(label='position-1', x=1, y=2, z=3)
    h1.history.create(label='position-2', x=5, y=6, z=7)
    h1.holdings['holding-1'].history.create(label='position-1', a=4, b=5)
    h1.holdings['holding-1'].holdings['holding-1'].history.create(label='position-1', alpha='alpha', beta='beta', gamma='gamma', delta='delta')

    print(f'Serdes test ')
    with timer('    Test: sleeping 1/2 second completed'):
        time.sleep(0.5)
    with timer('    Directly serdes completed'):
        h2.__setstate__(h1.__getstate__())
    with timer('    Pickle serdes completed'):
        h3 = pickle.loads(pickle.dumps(h2))
    with timer('    Chained JSON and Direct serdes completed'):
        h4.__setstate__(json.loads(json.dumps(h1.__getstate__())))

    assert h1 == h2
    assert h2 == h3
    assert h3 == h4

    # pass
