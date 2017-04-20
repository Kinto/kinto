from webob import Response
from pyramid.httpexceptions import HTTPForbidden
from pyramid.compat import bytes_

def x_view(request): # pragma: no cover
     return Response('this is private!')

def forbidden_view(context, request):
     msg = context.message
     result = context.result
     message = msg + '\n' + str(result)
     resp = HTTPForbidden()
     resp.body = bytes_(message)
     return resp

def includeme(config):
     from pyramid.authentication import AuthTktAuthenticationPolicy
     from pyramid.authorization import ACLAuthorizationPolicy
     authn_policy = AuthTktAuthenticationPolicy('seekr1t', hashalg='sha512')
     authz_policy = ACLAuthorizationPolicy()
     config._set_authentication_policy(authn_policy)
     config._set_authorization_policy(authz_policy)
     config.add_view(x_view, name='x', permission='private')
     config.add_view(forbidden_view, context=HTTPForbidden)
