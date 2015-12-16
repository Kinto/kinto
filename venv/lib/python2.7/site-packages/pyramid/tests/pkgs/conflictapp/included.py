from webob import Response

def bview(request): return Response('b view')

def includeme(config):
    config.add_view(bview)
