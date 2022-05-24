from itertools import chain

class NullClass:
    pass


class SerDesMeta(type):
    def __new__(cls, name, bases, namespace):
        if not bases:
            namespace['__getstate__'] = get_state
            namespace['__setstate__'] = set_state
            namespace['get_nested_classes'] = get_nested_classes
            namespace['__eq__'] = __equal__
        return super().__new__(cls, name, bases, namespace)


def get_slots(obj):
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
    for attr in get_slots(obj):
        value = getattr(obj, attr, None) # `None` traps for unset `__slots__`
        cls_keys, cls_vals = obj.get_nested_classes()
        if isinstance(value, cls_vals):
            state[attr] = value.__getstate__()
        else:
            state[attr] = value
    return state

def set_state(obj, state): 
    __class__ = state.pop('__class__') # used by get_target()
    for attr in get_slots(obj):
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




