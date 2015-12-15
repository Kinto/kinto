from webob import Response
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.view import view_config

@view_config(name='x')
def x_view(request): # pragma: no cover
     return Response('this is private!')

@view_config(name='y', permission='private2')
def y_view(request): # pragma: no cover
     return Response('this is private too!')
     
@view_config(name='z', permission=NO_PERMISSION_REQUIRED)
def z_view(request):
     return Response('this is public')

def includeme(config):
     from pyramid.authorization import ACLAuthorizationPolicy
     from pyramid.authentication import AuthTktAuthenticationPolicy
     authn_policy = AuthTktAuthenticationPolicy('seekt1t', hashalg='sha512')
     authz_policy = ACLAuthorizationPolicy()
     config.scan('pyramid.tests.pkgs.defpermbugapp')
     config._set_authentication_policy(authn_policy)
     config._set_authorization_policy(authz_policy)
     config.set_default_permission('private')
     
