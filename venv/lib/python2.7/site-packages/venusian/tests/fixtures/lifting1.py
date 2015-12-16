from venusian import lift
from venusian.tests.fixtures import decorator

class Super1(object): # pragma: no cover
    @decorator()
    def classname(self): pass

    @decorator()
    def boo(self): pass

    @decorator()
    def ram(self): pass

    def jump(self): pass

class Super2(object): # pragma: no cover
    def boo(self): pass

    @decorator()
    def hiss(self): pass

    @decorator()
    def jump(self): pass
        
@lift()
class Sub(Super1, Super2): # pragma: no cover
    def boo(self): pass

    def hiss(self): pass
    
    @decorator()
    def smack(self): pass
    
