from venusian.tests.fixtures import decorator

class Super(object): # pragma: no cover
    @decorator()
    def classname(self): pass

    @decorator()
    def boo(self): pass


# the Sub class must not inherit the decorations of its superclass when scanned

class Sub(Super): # pragma: no cover
     pass
    
