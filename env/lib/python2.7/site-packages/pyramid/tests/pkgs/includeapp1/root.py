from pyramid.response import Response

def aview(request):
    return Response('root')

def configure(config):
    config.add_view(aview)
    config.include('pyramid.tests.pkgs.includeapp1.two.configure')
    config.commit()
    
