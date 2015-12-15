from venusian import lift, onlyliftedfrom
from venusian.tests.fixtures import (
    categorydecorator,
    categorydecorator2,
    )

@onlyliftedfrom()
class Super(object): # pragma: no cover
    @categorydecorator()
    def hiss(self): pass

    @categorydecorator2()
    def jump(self): pass
        
@lift(('mycategory',))
class Sub(Super): # pragma: no cover
    def hiss(self): pass
    
    def jump(self): pass

    @categorydecorator2()
    def smack(self): pass
    
