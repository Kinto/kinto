from pyramid.response import Response
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

def aview(request):
    return Response('a view')

def routeview(request):
    return Response('route view')

def protectedview(request):
    return Response('protected view')

def includeme(config):
    # purposely sorta-randomly ordered (route comes after view naming it,
    # authz comes after views)
    config.add_view(aview)
    config.add_view(protectedview, name='protected', permission='view')
    config.add_view(routeview, route_name='aroute')
    config.add_route('aroute', '/route')
    config.set_authentication_policy(AuthTktAuthenticationPolicy(
        'seekri1t', hashalg='sha512'))
    config.set_authorization_policy(ACLAuthorizationPolicy())
    config.include('pyramid.tests.pkgs.conflictapp.included')
