import pickle

class WidgetType(object):
    
    class FloatType(object):
        pass
    
    class TextType(object):
        pass

class ObjectToPickle(object):
     def __init__(self):
         self.type = WidgetType.TextType

o = ObjectToPickle()
p = pickle.dumps(o)
