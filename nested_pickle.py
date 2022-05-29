# There is some tricky shit in here so you have to follow the recipe carefully.
#
# Note <class BaseHolindg> in particular:
#   1. If initialization uses __new__ instead of __init__, then type.__call__
#      will call dict.__init__(label) after __new__, which will create a label,
#      value pair {'label':label} with label defaulting to None obviously given
#      the signature of __new__.
#   2. A workaround to this problem is to add an __init__ method, which just
#      ignores the label argument and then either (i) doesn't bother to call
#      super().__init__, or (ii) calls super().__init__ w/ NO arguments.
#   3. The problem with using __init__ instead of __new__ is that pickle calls
#      __new__ BUT NOT __init__. That means that __setstate__ needs to create
#      self.holding = self.Holding(label=self.label); otherwise, you get a
#      "history does not exist" error. 


import json
import pickle
import time
from pprint import PrettyPrinter

from imports.time_utils import timer

pprint = PrettyPrinter(sort_dicts=False).pprint

class Label:
    __slots__ = ()

    @property
    def label(self):
        return self.__class__.__name__

class ClassAttribute:
    __slots__ = ('value', 'default')

    def __init__(self, default=None):
        self.value = default

    def __get__(self, instance, owner):
        return self.value

    def __set__(self, instance, value):
        self.value = value

class PrivateName:
    __slots__ = ('_pname', 'default')

    def __init__(self, default=None):
        self.default = default

    def __get__(self, instance, owner):
        try:
            return getattr(instance, self._pname)
        except:
            return self.default

    def __set__(self, instance, value):
        setattr(instance, self._pname, value)

    def __set_name__(self, owner, name):
        self._pname = f'_{name}'

class PositionMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    def __new__(cls, name, bases, namespace):
        if Label not in bases:
            namespace['__slots__'] = namespace.pop('attrs')

        return super().__new__(cls, name, bases, namespace)
        
class Position(Label, metaclass=PositionMeta):

    def __init__(self, **kwargs):

        for a in self.__slots__[1:]:
            setattr(self, a, 0)

        for k, v in kwargs.items():
            setattr(self, k, v) # AttributeError on write to non-existent slot

    def __repr__(self):
        attr_repr = (f'{k}={getattr(self, k, None)}' for k in self.__slots__)
        return f"{self.label}({', '.join(attr_repr)})"

    def __getstate__(self):
        state = dict()
        for s in self.__slots__:
            state[s] = getattr(self, s)
        return state

    def __setstate__(self, state):
        for s in self.__slots__:
            setattr(self, s, state.pop(s))

    def __eq__(self, other):
        return self.__getstate__() == other.__getstate__()

class HistoryMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return {'__slots__': ()}

    #staticmethod
    def __new__(cls, name, bases, namespace):
        if dict not in bases and Label not in bases:
            namespace['Position'] = type(namespace.pop('label') + '.Position',
                (Position, ), dict(attrs=namespace.pop('attrs')))

        return super().__new__(cls, name, bases, namespace)

class History(dict, Label, metaclass=HistoryMeta):

    def __init__(self):
        pass

    def create(self, label, **kwargs):
        self[label] = self.Position(**kwargs)

    def __repr__(self):
        position_type = '.'.join(self.Position.__name__.split('.')[:-1])
        return f'{self.label}({len(self)} {position_type} entries)'

    def __getstate__(self):
        state = dict()
        for k, v in self.items():
            state[k] = v.__getstate__()
        return state

    def __setstate__(self, state):
        self.clear()
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
        if dict not in bases:
            if holding_type:=namespace.pop('holding_type', None):
                namespace['Holding'] = holding_type

            namespace['__slots__'] = ('label', 'history', )

        return super().__new__(cls, name, bases, namespace)

class BaseHolding(dict, metaclass=BaseMeta):

    def __init__(self, label=None): # no call to super().__init__()
        self.label = label
        self.history = self._make_history(self.label, self.attrs)

    def __repr__(self):
        holding_type = getattr(self, 'Holding', type(None))
        return f'{self.label}({len(self)} {holding_type.__name__} holding(s))'

    def create(self, label):
        self[label] = self.Holding(label=self.label + '.' + label)

    def _make_history(self, label, attrs):
        cls = type(label + '.History', (History, ),
              dict(label=label, attrs=attrs))
        instance = cls()
        return instance

    def __getstate__(self):
        # log class variables
        state = dict()
        # log __slots__
        state['label'] = self.label
        state['history'] = self.history.__getstate__()
        # log self.items()
        for k, v in self.items():
            state[k] = v.__getstate__()
        return state

    def __setstate__(self, state):
        self.clear()
        # restore class variables
        # restore __slots__
        self.label = state.pop('label')
        # The follwoing line is not req'd if self.history created in __new__
        self.history = self._make_history(self.label, self.attrs)
        self.history.__setstate__(state.pop('history'))
        # restore self.items()
        for k, s in state.items():
            v = self.Holding(self.label)
            v.__setstate__(s)
            self[k] = v

    def __eq__(self, other):
        return self.__getstate__() == other.__getstate__()


if __name__ == '__main__':
    class Security(BaseHolding):
        attrs = ('alpha', 'beta', 'gamma', 'delta')

    class Account(BaseHolding):
        attrs = ('a', 'b')
        holding_type = Security

    class Holding(BaseHolding):
        attrs = ('x', 'y', 'z')
        holding_type = Account

    h1 = Holding(label='Portfolio')
    h2 = Holding(label='Portfolio')
    h3 = Holding(label='Portfolio')
    h4 = Holding(label='Portfolio')

    h1.create('Vanguard')
    h1.create('Bank of America')
    h1.__getstate__()
    h1['Vanguard'].create('VTSNX')
    h1['Vanguard'].create('VNQI')
    h1.history.create(label='position-1', x=1, y=2, z=3)
    h1.history.create(label='position-2', x=5, y=6, z=7)
    h1['Vanguard'].history.create(label='position-1', a=4, b=5)
    h1['Vanguard']['VTSNX'].history.create(label='position-1', alpha='alpha', beta='beta', gamma='gamma', delta='delta')
    h1['Vanguard']['VNQI'].history.create(label='position-1', alpha='a', beta='b', gamma='c', delta='d')
    h1['Bank of America'].history.create(label='position-1', a=6, b=7)
    h1['Bank of America'].create('VNQI')
    h1['Bank of America']['VNQI'].history.create(label='position-1', alpha='a-1', beta='b-1', gamma='c-1', delta='d-1')

    print()
    print(h1)
    print(h1['Vanguard'])
    print(h1['Vanguard'].history)
    print(h1['Vanguard'].history['position-1'])
    print(h1['Vanguard']['VTSNX'].history)
    print(h1['Vanguard']['VNQI'].history['position-1'])
    print(h1['Bank of America'].history)
    print(h1['Bank of America']['VNQI'].history['position-1'])
    print()

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
