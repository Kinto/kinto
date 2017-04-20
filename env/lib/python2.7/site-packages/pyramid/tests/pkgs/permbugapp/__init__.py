from pyramid.compat import escape
from pyramid.security import view_execution_permitted
from pyramid.response import Response

def x_view(request): # pragma: no cover
     return Response('this is private!')

def test(context, request):
    # should return false
     msg = 'Allow ./x? %s' % repr(view_execution_permitted(
         context, request, 'x'))
     return Response(escape(msg))

def includeme(config):
     from pyramid.authentication import AuthTktAuthenticationPolicy
     from pyramid.authorization import ACLAuthorizationPolicy
     authn_policy = AuthTktAuthenticationPolicy('seekt1t', hashalg='sha512')
     authz_policy = ACLAuthorizationPolicy()
     config.set_authentication_policy(authn_policy)
     config.set_authorization_policy(authz_policy)
     config.add_view(test, name='test')
     config.add_view(x_view, name='x', permission='private')
