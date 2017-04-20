class RootFactory(object):
    __acl__ = [('Allow', 'fred', 'view')]
    def __init__(self, request):
        pass

class LocalRootFactory(object):
    __acl__ = [('Allow', 'bob', 'view')]
    def __init__(self, request):
        pass
    

def includeme(config):
     from pyramid.authentication import RemoteUserAuthenticationPolicy
     from pyramid.authorization import ACLAuthorizationPolicy
     authn_policy = RemoteUserAuthenticationPolicy()
     authz_policy = ACLAuthorizationPolicy()
     config._set_authentication_policy(authn_policy)
     config._set_authorization_policy(authz_policy)
     config.add_static_view('allowed', 'pyramid.tests:fixtures/static/')
     config.add_static_view('protected', 'pyramid.tests:fixtures/static/',
                            permission='view')
     config.add_static_view('factory_protected',
                            'pyramid.tests:fixtures/static/',
                            permission='view',
                            factory=LocalRootFactory)
