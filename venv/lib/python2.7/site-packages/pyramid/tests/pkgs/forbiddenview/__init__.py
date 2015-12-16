from pyramid.view import forbidden_view_config, view_config
from pyramid.response import Response
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

@forbidden_view_config(route_name='foo')
def foo_forbidden(request): # pragma: no cover
    return Response('foo_forbidden')

@forbidden_view_config()
def forbidden(request):
    return Response('generic_forbidden')

@view_config(route_name='foo')
def foo(request): # pragma: no cover
    return Response('OK foo')

@view_config(route_name='bar')
def bar(request): # pragma: no cover
    return Response('OK bar')

def includeme(config):
    authn_policy = AuthTktAuthenticationPolicy('seekri1', hashalg='sha512')
    authz_policy = ACLAuthorizationPolicy()
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    config.set_default_permission('a')
    config.add_route('foo', '/foo')
    config.add_route('bar', '/bar')
    config.scan('pyramid.tests.pkgs.forbiddenview')
    
