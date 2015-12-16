from venusian.tests.fixtures import decorator

@decorator(function=True)
def function(request): # pragma: no cover
    return request

class Class(object):
    @decorator(method=True)
    def method(self, request): # pragma: no cover
        return request
    
class Instance(object):
    def __call__(self, request): # pragma: no cover
        return request

inst = Instance()
inst = decorator(instance=True)(inst)

