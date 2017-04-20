from webob import Response

def rdf_view(request):
    """ """
    return Response('rdf')

def juri_view(request):
    """ """
    return Response('juri')

def includeme(config):
    config.add_route('rdf', 'licenses/:license_code/:license_version/rdf')
    config.add_route('juri',
                     'licenses/:license_code/:license_version/:jurisdiction')
    config.add_view(rdf_view, route_name='rdf')
    config.add_view(juri_view, route_name='juri')
