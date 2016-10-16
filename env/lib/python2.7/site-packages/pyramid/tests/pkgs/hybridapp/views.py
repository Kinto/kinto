from webob import Response

def route_view(request):
    """ """
    return Response('route')

def global_view(request):
    """ """
    return Response('global')

def global2_view(request):
    """ """
    return Response('global2')

def route2_view(request):
    """ """
    return Response('route2')

def exception_view(request):
    """ """
    return Response('supressed')

def exception2_view(request):
    """ """
    return Response('supressed2')

def erroneous_view(request):
    """ """
    raise RuntimeError()

def erroneous_sub_view(request):
    """ """
    raise SubException()

class SuperException(Exception):
    """ """

class SubException(SuperException):
    """ """
