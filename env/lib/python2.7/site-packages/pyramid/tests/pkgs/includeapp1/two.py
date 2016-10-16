from pyramid.response import Response

def aview(request):
    return Response('two')

def configure(config):
    config.add_view(aview, name='two')
    config.include('pyramid.tests.pkgs.includeapp1.three.configure')
    config.add_view(aview) # will be overridden by root when resolved
