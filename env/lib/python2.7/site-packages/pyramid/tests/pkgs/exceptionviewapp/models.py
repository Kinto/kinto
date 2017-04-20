
class NotAnException(object):
    pass

class AnException(Exception):
    pass

class RouteContext(object):
    pass

class RouteContext2(object):
    pass

def route_factory(*arg):
    return RouteContext()

def route_factory2(*arg):
    return RouteContext2()
