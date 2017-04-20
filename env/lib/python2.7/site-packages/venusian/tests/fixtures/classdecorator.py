from venusian.tests.fixtures import decorator

@decorator(superclass=True)
class SuperClass(object):
    pass

@decorator(subclass=True)
class SubClass(SuperClass):
    pass

