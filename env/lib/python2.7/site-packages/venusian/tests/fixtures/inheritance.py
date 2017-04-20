from venusian.tests.fixtures import decorator

@decorator()
class Parent(object):
    pass

class Child(Parent):
    pass
