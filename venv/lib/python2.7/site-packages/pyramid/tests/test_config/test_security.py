import unittest

from pyramid.exceptions import ConfigurationExecutionError
from pyramid.exceptions import ConfigurationError

class ConfiguratorSecurityMethodsTests(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test_set_authentication_policy_no_authz_policy(self):
        config = self._makeOne()
        policy = object()
        config.set_authentication_policy(policy)
        self.assertRaises(ConfigurationExecutionError, config.commit)

    def test_set_authentication_policy_no_authz_policy_autocommit(self):
        config = self._makeOne(autocommit=True)
        policy = object()
        self.assertRaises(ConfigurationError,
                          config.set_authentication_policy, policy)

    def test_set_authentication_policy_with_authz_policy(self):
        from pyramid.interfaces import IAuthenticationPolicy
        from pyramid.interfaces import IAuthorizationPolicy
        config = self._makeOne()
        authn_policy = object()
        authz_policy = object()
        config.registry.registerUtility(authz_policy, IAuthorizationPolicy)
        config.set_authentication_policy(authn_policy)
        config.commit()
        self.assertEqual(
            config.registry.getUtility(IAuthenticationPolicy), authn_policy)

    def test_set_authentication_policy_with_authz_policy_autocommit(self):
        from pyramid.interfaces import IAuthenticationPolicy
        from pyramid.interfaces import IAuthorizationPolicy
        config = self._makeOne(autocommit=True)
        authn_policy = object()
        authz_policy = object()
        config.registry.registerUtility(authz_policy, IAuthorizationPolicy)
        config.set_authentication_policy(authn_policy)
        config.commit()
        self.assertEqual(
            config.registry.getUtility(IAuthenticationPolicy), authn_policy)

    def test_set_authorization_policy_no_authn_policy(self):
        config = self._makeOne()
        policy = object()
        config.set_authorization_policy(policy)
        self.assertRaises(ConfigurationExecutionError, config.commit)

    def test_set_authorization_policy_no_authn_policy_autocommit(self):
        from pyramid.interfaces import IAuthorizationPolicy
        config = self._makeOne(autocommit=True)
        policy = object()
        config.set_authorization_policy(policy)
        self.assertEqual(
            config.registry.getUtility(IAuthorizationPolicy), policy)

    def test_set_authorization_policy_with_authn_policy(self):
        from pyramid.interfaces import IAuthorizationPolicy
        from pyramid.interfaces import IAuthenticationPolicy
        config = self._makeOne()
        authn_policy = object()
        authz_policy = object()
        config.registry.registerUtility(authn_policy, IAuthenticationPolicy)
        config.set_authorization_policy(authz_policy)
        config.commit()
        self.assertEqual(
            config.registry.getUtility(IAuthorizationPolicy), authz_policy)

    def test_set_authorization_policy_with_authn_policy_autocommit(self):
        from pyramid.interfaces import IAuthorizationPolicy
        from pyramid.interfaces import IAuthenticationPolicy
        config = self._makeOne(autocommit=True)
        authn_policy = object()
        authz_policy = object()
        config.registry.registerUtility(authn_policy, IAuthenticationPolicy)
        config.set_authorization_policy(authz_policy)
        self.assertEqual(
            config.registry.getUtility(IAuthorizationPolicy), authz_policy)

    def test_set_default_permission(self):
        from pyramid.interfaces import IDefaultPermission
        config = self._makeOne(autocommit=True)
        config.set_default_permission('view')
        self.assertEqual(config.registry.getUtility(IDefaultPermission),
                         'view')

    def test_add_permission(self):
        config = self._makeOne(autocommit=True)
        config.add_permission('perm')
        cat = config.registry.introspector.get_category('permissions')
        self.assertEqual(len(cat), 1)
        D = cat[0]
        intr = D['introspectable']
        self.assertEqual(intr['value'], 'perm')

