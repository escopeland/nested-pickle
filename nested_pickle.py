# There is some tricky shit in here so you have to follow the recipe carefully.
#
# Note <class BaseHolindg> in particular:
#   1. If initialization uses __new__ instead of __init__, then type.__call__
#      will call dict.__init__(label) after __new__, which will create a key,
#      value pair {'label':label} with label defaulting to None obviously given
#      the signature of __new__.
#   2. A workaround to this problem is to add an __init__ method, which just
#      ignores the label argument and then either (i) doesn't bother to call
#      super().__init__, or (ii) calls super().__init__ w/ NO arguments.
#   3. The problem with using __init__ instead of __new__ is that pickle calls
#      __new__ BUT NOT __init__. That means that __setstate__ needs to create
#      self.holding = self.Holding(label=self.label) as shown below; otherwise,
#      you get a "history does not exist" error. 


import json
import pickle
import time
from pprint import PrettyPrinter

from imports.time_utils import timer

pprint = PrettyPrinter(sort_dicts=False).pprint

class PositionMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    def __new__(cls, name, bases, namespace):
        if bases:
            namespace['__slots__'] = namespace.pop('attrs')

        return super().__new__(cls, name, bases, namespace)
        
class Position(metaclass=PositionMeta):

    def __init__(self, **kwargs):

        for a in self.__slots__:
            setattr(self, a, 0)

        for k, v in kwargs.items():
            setattr(self, k, v) # AttributeError on write to non-existent slot

    def __repr__(self):
        attr_repr = (f'{k}={getattr(self, k, None)}' for k in self.__slots__)
        return f"Position: {', '.join(attr_repr)}"

    def __getstate__(self):
        state = dict()
        # log __slots__
        for s in self.__slots__:
            state[s] = getattr(self, s)
        return state

    def __setstate__(self, state):
        # restore __slots__
        for s in self.__slots__:
            setattr(self, s, state.pop(s))

    def __eq__(self, other):
        return self.__getstate__() == other.__getstate__()

class HistoryMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    def __new__(cls, name, bases, namespace):
        if not dict in bases:
            namespace['Position'] = type(
                name.split('.')[0] + '.Position', (Position, ),
                dict(attrs=namespace.pop('attrs')))
        return super().__new__(cls, name, bases, namespace)

class History(dict, metaclass=HistoryMeta):

    def create(self, label, **kwargs):
        self[label] = self.Position(**kwargs)

    def __repr__(self):
        return f'History object: {len(self)} instances of type {self.Position}'

    def __getstate__(self):
        state = dict()
        # log self.items()
        for k, v in self.items():
            state[k] = v.__getstate__()
        return state

    def __setstate__(self, state):
        self.clear()
        # restore self.items()
        for k, s in state.items():
            v = self.Position()
            v.__setstate__(s)
            self[k] = v

    def __eq__(self, other):
        return self.__getstate__() == other.__getstate__()

class BaseMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    def __new__(cls, name, bases, namespace):
        if not dict in bases:
            if len(name.split('.')) < 2: # Skip if an already setup `holding_type`
                namespace['History'] = type(name + '.History',  (History, ),
                    dict(attrs=namespace.pop('attrs')))

                holding_type = namespace.pop('holding_type', None)
                namespace['Holding'] = (
                    type(name.split('.')[0] + '.Holding', (holding_type, ), dict())
                    if holding_type else None)

                namespace['__slots__'] = ('label', 'history', )

        return super().__new__(cls, name, bases, namespace)

class BaseHolding(dict, metaclass=BaseMeta):

    def __init__(self, label=None):
        self.label = label
        self.history = self.History()
        # no call to super().__init__() needed.

    def create(self, label):
        self[label] = self.Holding(label=label)

    def __getstate__(self):
        state = dict()
        # log __slots__
        state['label'] = self.label
        state['history']  = self.history.__getstate__()
        # log self.items()
        for k, v in self.items():
            state[k] = v.__getstate__()
        return state

    def __setstate__(self, state):
        self.clear()
        # restore __slots__
        self.label = state.pop('label')
        # The follwoing line is not req'd if self.history created in __new__
        self.history = self.History(label=self.label)
        self.history.__setstate__(state.pop('history'))
        # restore self.items()
        for k, s in state.items():
            v = self.Holding(self.label)
            v.__setstate__(s)
            self[k] = v

    def __eq__(self, other):
        return self.__getstate__() == other.__getstate__()


if __name__ == '__main__':
    class SubSubHolding(BaseHolding):
        attrs = ('alpha', 'beta', 'gamma', 'delta')

    class SubHolding(BaseHolding):
        attrs = ('a', 'b')
        holding_type = SubSubHolding

    class Holding(BaseHolding):
        attrs = ('x', 'y', 'z')
        holding_type = SubHolding

    h1 = Holding(label='Portfolio')
    h2 = Holding(label='Portfolio')
    h3 = Holding(label='Portfolio')
    h4 = Holding(label='Portfolio')

    h1.create('Vanguard')
    h1.__getstate__()
    h1['Vanguard'].create('VTSNX')
    h1.history.create(label='position-1', x=1, y=2, z=3)
    h1.history.create(label='position-2', x=5, y=6, z=7)
    h1['Vanguard'].history.create(label='position-1', a=4, b=5)
    h1['Vanguard']['VTSNX'].history.create(label='position-1', alpha='alpha', beta='beta', gamma='gamma', delta='delta')

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
    pass