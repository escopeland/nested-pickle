from collections import namedtuple
import pickle


class Foo:

    # Bar = namedtuple('Foo.Bar', ['x', 'y'])
    Bar = type('Foo.Bar', (), dict.fromkeys(('x', 'y')))

    def baz(self):
        s = set()
        b = self.Bar()
        b.x = 2
        b.y = 3
        s.add(b)
        print(pickle.dumps(s))

if __name__ == '__main__':
    f = Foo()
    f.baz()
