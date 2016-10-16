# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
from zope.interface import implementer

import pyramid.authorization
import pyramid.testing
from pyramid.testing import DummyRequest
from pyramid.security import Everyone, Authenticated
from pyramid.exceptions import Forbidden
from pyramid.interfaces import IAuthenticationPolicy, IAuthorizationPolicy

from pyramid_multiauth import MultiAuthenticationPolicy

if sys.version_info < (2, 7):
    import unittest2 as unittest  # pragma: nocover
else:
    import unittest  # pragma: nocover


#  Here begins various helper classes and functions for the tests.

@implementer(IAuthenticationPolicy)
class BaseAuthnPolicy(object):
    """A do-nothing base class for authn policies."""

    def __init__(self, **kwds):
        self.__dict__.update(kwds)

    def authenticated_userid(self, request):
        return self.unauthenticated_userid(request)

    def unauthenticated_userid(self, request):
        return None

    def effective_principals(self, request):
        principals = [Everyone]
        userid = self.authenticated_userid(request)
        if userid is not None:
            principals.append(Authenticated)
            principals.append(userid)
        return principals

    def remember(self, request, principal):
        return []

    def forget(self, request):
        return []


@implementer(IAuthenticationPolicy)
class TestAuthnPolicy1(BaseAuthnPolicy):
    """An authn policy that adds "test1" to the principals."""

    def effective_principals(self, request):
        return [Everyone, "test1"]

    def remember(self, request, principal):
        return [("X-Remember", principal)]

    def forget(self, request):
        return [("X-Forget", "foo")]


@implementer(IAuthenticationPolicy)
class TestAuthnPolicy2(BaseAuthnPolicy):
    """An authn policy that sets "test2" as the username."""

    def unauthenticated_userid(self, request):
        return "test2"

    def remember(self, request, principal):
        return [("X-Remember-2", principal)]

    def forget(self, request):
        return [("X-Forget", "bar")]


@implementer(IAuthenticationPolicy)
class TestAuthnPolicy3(BaseAuthnPolicy):
    """Authn policy that sets "test3" as the username "test4" in principals."""

    def unauthenticated_userid(self, request):
        return "test3"

    def effective_principals(self, request):
        return [Everyone, Authenticated, "test3", "test4"]


@implementer(IAuthenticationPolicy)
class TestAuthnPolicyUnauthOnly(BaseAuthnPolicy):
    """An authn policy that returns an unauthenticated userid but not an
    authenticated userid, similar to the basic auth policy.
    """

    def authenticated_userid(self, request):
        return None

    def unauthenticated_userid(self, request):
        return "test3"

    def effective_principals(self, request):
        return [Everyone]


@implementer(IAuthorizationPolicy)
class TestAuthzPolicyCustom(object):
    def permits(self, context, principals, permission):
        return True

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError()  # pragma: nocover


def testincludeme1(config):
    """Config include that sets up a TestAuthnPolicy1 and a forbidden view."""
    config.set_authentication_policy(TestAuthnPolicy1())

    def forbidden_view(request):
        return "FORBIDDEN ONE"

    config.add_view(forbidden_view,
                    renderer="json",
                    context="pyramid.exceptions.Forbidden")


def testincludeme2(config):
    """Config include that sets up a TestAuthnPolicy2."""
    config.set_authentication_policy(TestAuthnPolicy2())


def testincludemenull(config):
    """Config include that doesn't do anything."""
    pass


def testincludeme3(config):
    """Config include that adds a TestAuthPolicy3 and commits it."""
    config.set_authentication_policy(TestAuthnPolicy3())
    config.commit()


def raiseforbidden(request):
    """View that always just raises Forbidden."""
    raise Forbidden()


def testgroupfinder(userid, request):
    """A test groupfinder that only recognizes user "test3"."""
    if userid != "test3":
        return None
    return ["group"]


#  Here begins the actual test cases


class MultiAuthPolicyTests(unittest.TestCase):
    """Testcases for MultiAuthenticationPolicy and related hooks."""

    def setUp(self):
        self.config = pyramid.testing.setUp(autocommit=False)

    def tearDown(self):
        pyramid.testing.tearDown()

    def test_basic_stacking(self):
        policies = [TestAuthnPolicy1(), TestAuthnPolicy2()]
        policy = MultiAuthenticationPolicy(policies)
        request = DummyRequest()
        self.assertEquals(policy.authenticated_userid(request),
                          "test2")
        self.assertEquals(sorted(policy.effective_principals(request)),
                          [Authenticated, Everyone, "test1", "test2"])

    def test_policy_selected_event(self):
        from pyramid.testing import testConfig
        from pyramid_multiauth import MultiAuthPolicySelected

        policies = [TestAuthnPolicy2(), TestAuthnPolicy3()]
        policy = MultiAuthenticationPolicy(policies)
        # Simulate loading from config:
        policies[0]._pyramid_multiauth_name = "name"

        with testConfig() as config:
            request = DummyRequest()

            selected_policy = []

            def track_policy(event):
                selected_policy.append(event)

            config.add_subscriber(track_policy, MultiAuthPolicySelected)

            self.assertEquals(policy.authenticated_userid(request), "test2")

            self.assertEquals(selected_policy[0].policy, policies[0])
            self.assertEquals(selected_policy[0].policy_name, "name")
            self.assertEquals(selected_policy[0].userid, "test2")
            self.assertEquals(selected_policy[0].request, request)
            self.assertEquals(len(selected_policy), 1)

            # Effective principals also triggers an event when groupfinder
            # is provided.
            policy_with_group = MultiAuthenticationPolicy(policies,
                                                          lambda u, r: ['foo'])
            policy_with_group.effective_principals(request)
            self.assertEquals(len(selected_policy), 2)

    def test_stacking_of_unauthenticated_userid(self):
        policies = [TestAuthnPolicy2(), TestAuthnPolicy3()]
        policy = MultiAuthenticationPolicy(policies)
        request = DummyRequest()
        self.assertEquals(policy.unauthenticated_userid(request), "test2")
        policies.reverse()
        self.assertEquals(policy.unauthenticated_userid(request), "test3")

    def test_stacking_of_authenticated_userid(self):
        policies = [TestAuthnPolicy2(), TestAuthnPolicy3()]
        policy = MultiAuthenticationPolicy(policies)
        request = DummyRequest()
        self.assertEquals(policy.authenticated_userid(request), "test2")
        policies.reverse()
        self.assertEquals(policy.authenticated_userid(request), "test3")

    def test_stacking_of_authenticated_userid_with_groupdfinder(self):
        policies = [TestAuthnPolicy2(), TestAuthnPolicy3()]
        policy = MultiAuthenticationPolicy(policies, testgroupfinder)
        request = DummyRequest()
        self.assertEquals(policy.authenticated_userid(request), "test3")
        policies.reverse()
        self.assertEquals(policy.unauthenticated_userid(request), "test3")

    def test_only_unauthenticated_userid_with_groupfinder(self):
        policies = [TestAuthnPolicyUnauthOnly()]
        policy = MultiAuthenticationPolicy(policies, testgroupfinder)
        request = DummyRequest()
        self.assertEquals(policy.unauthenticated_userid(request), "test3")
        self.assertEquals(policy.authenticated_userid(request), None)
        self.assertEquals(policy.effective_principals(request), [Everyone])

    def test_authenticated_userid_unauthenticated_with_groupfinder(self):
        policies = [TestAuthnPolicy2()]
        policy = MultiAuthenticationPolicy(policies, testgroupfinder)
        request = DummyRequest()
        self.assertEquals(policy.authenticated_userid(request), None)
        self.assertEquals(sorted(policy.effective_principals(request)),
                          [Everyone, 'test2'])

    def test_stacking_of_effective_principals(self):
        policies = [TestAuthnPolicy2(), TestAuthnPolicy3()]
        policy = MultiAuthenticationPolicy(policies)
        request = DummyRequest()
        self.assertEquals(sorted(policy.effective_principals(request)),
                          [Authenticated, Everyone, "test2", "test3", "test4"])
        policies.reverse()
        self.assertEquals(sorted(policy.effective_principals(request)),
                          [Authenticated, Everyone, "test2", "test3", "test4"])
        policies.append(TestAuthnPolicy1())
        self.assertEquals(sorted(policy.effective_principals(request)),
                          [Authenticated, Everyone, "test1", "test2",
                           "test3", "test4"])

    def test_stacking_of_effective_principals_with_groupfinder(self):
        policies = [TestAuthnPolicy2(), TestAuthnPolicy3()]
        policy = MultiAuthenticationPolicy(policies, testgroupfinder)
        request = DummyRequest()
        self.assertEquals(sorted(policy.effective_principals(request)),
                          ["group", Authenticated, Everyone, "test2",
                           "test3", "test4"])
        policies.reverse()
        self.assertEquals(sorted(policy.effective_principals(request)),
                          ["group", Authenticated, Everyone, "test2",
                           "test3", "test4"])
        policies.append(TestAuthnPolicy1())
        self.assertEquals(sorted(policy.effective_principals(request)),
                          ["group", Authenticated, Everyone, "test1",
                           "test2", "test3", "test4"])

    def test_stacking_of_remember_and_forget(self):
        policies = [TestAuthnPolicy1(), TestAuthnPolicy2(), TestAuthnPolicy3()]
        policy = MultiAuthenticationPolicy(policies)
        request = DummyRequest()
        self.assertEquals(policy.remember(request, "ha"),
                          [("X-Remember", "ha"), ("X-Remember-2", "ha")])
        self.assertEquals(policy.forget(request),
                          [("X-Forget", "foo"), ("X-Forget", "bar")])
        policies.reverse()
        self.assertEquals(policy.remember(request, "ha"),
                          [("X-Remember-2", "ha"), ("X-Remember", "ha")])
        self.assertEquals(policy.forget(request),
                          [("X-Forget", "bar"), ("X-Forget", "foo")])

    def test_includeme_uses_acl_authorization_by_default(self):
        self.config.include("pyramid_multiauth")
        self.config.commit()
        policy = self.config.registry.getUtility(IAuthorizationPolicy)
        expected = pyramid.authorization.ACLAuthorizationPolicy
        self.assertTrue(isinstance(policy, expected))

    def test_includeme_reads_authorization_from_settings(self):
        self.config.add_settings({
            "multiauth.authorization_policy": "pyramid_multiauth.tests."
            "TestAuthzPolicyCustom"
        })
        self.config.include("pyramid_multiauth")
        self.config.commit()
        policy = self.config.registry.getUtility(IAuthorizationPolicy)
        self.assertTrue(isinstance(policy, TestAuthzPolicyCustom))

    def test_includeme_by_module(self):
        self.config.add_settings({
            "multiauth.groupfinder": "pyramid_multiauth.tests.testgroupfinder",
            "multiauth.policies": "pyramid_multiauth.tests.testincludeme1 "
                                  "pyramid_multiauth.tests.testincludeme2 "
                                  "pyramid_multiauth.tests.testincludemenull "
                                  "pyramid_multiauth.tests.testincludeme3 "
        })
        self.config.include("pyramid_multiauth")
        self.config.commit()
        policy = self.config.registry.getUtility(IAuthenticationPolicy)
        self.assertEquals(policy._callback, testgroupfinder)
        self.assertEquals(len(policy._policies), 3)
        # Check that they stack correctly.
        request = DummyRequest()
        self.assertEquals(policy.unauthenticated_userid(request), "test2")
        self.assertEquals(policy.authenticated_userid(request), "test3")
        # Check that the forbidden view gets invoked.
        self.config.add_route("index", path="/")
        self.config.add_view(raiseforbidden, route_name="index")
        app = self.config.make_wsgi_app()
        environ = {"PATH_INFO": "/", "REQUEST_METHOD": "GET"}

        def start_response(*args):
            pass

        result = b"".join(app(environ, start_response))
        self.assertEquals(result, b'"FORBIDDEN ONE"')

    def test_includeme_by_callable(self):
        self.config.add_settings({
            "multiauth.groupfinder":
                "pyramid_multiauth.tests.testgroupfinder",
            "multiauth.policies":
                "pyramid_multiauth.tests.testincludeme1 policy1 policy2",
            "multiauth.policy.policy1.use":
                "pyramid_multiauth.tests.TestAuthnPolicy2",
            "multiauth.policy.policy1.foo":
                "bar",
            "multiauth.policy.policy2.use":
                "pyramid_multiauth.tests.TestAuthnPolicy3"
        })
        self.config.include("pyramid_multiauth")
        self.config.commit()
        policy = self.config.registry.getUtility(IAuthenticationPolicy)
        self.assertEquals(policy._callback, testgroupfinder)
        self.assertEquals(len(policy._policies), 3)
        self.assertEquals(policy._policies[1].foo, "bar")
        # Check that they stack correctly.
        request = DummyRequest()
        self.assertEquals(policy.unauthenticated_userid(request), "test2")
        self.assertEquals(policy.authenticated_userid(request), "test3")
        # Check that the forbidden view gets invoked.
        self.config.add_route("index", path="/")
        self.config.add_view(raiseforbidden, route_name="index")
        app = self.config.make_wsgi_app()
        environ = {"PATH_INFO": "/", "REQUEST_METHOD": "GET"}

        def start_response(*args):
            pass

        result = b"".join(app(environ, start_response))
        self.assertEquals(result, b'"FORBIDDEN ONE"')

    def test_includeme_with_unconfigured_policy(self):
        self.config.add_settings({
            "multiauth.groupfinder":
                "pyramid_multiauth.tests.testgroupfinder",
            "multiauth.policies":
                "pyramid_multiauth.tests.testincludeme1 policy1 policy2",
            "multiauth.policy.policy1.use":
                "pyramid_multiauth.tests.TestAuthnPolicy2",
            "multiauth.policy.policy1.foo":
                "bar",
        })
        self.assertRaises(ValueError, self.config.include, "pyramid_multiauth")

    def test_get_policy(self):
        self.config.add_settings({
            "multiauth.policies":
                "pyramid_multiauth.tests.testincludeme1 policy1 policy2",
            "multiauth.policy.policy1.use":
                "pyramid_multiauth.tests.TestAuthnPolicy2",
            "multiauth.policy.policy1.foo":
                "bar",
            "multiauth.policy.policy2.use":
                "pyramid_multiauth.tests.TestAuthnPolicy3"
        })
        self.config.include("pyramid_multiauth")
        self.config.commit()
        policy = self.config.registry.getUtility(IAuthenticationPolicy)
        # Test getting policies by name.
        self.assertTrue(isinstance(policy.get_policy("policy1"),
                                   TestAuthnPolicy2))
        self.assertTrue(isinstance(policy.get_policy("policy2"),
                                   TestAuthnPolicy3))
        self.assertEquals(policy.get_policy("policy3"), None)
        # Test getting policies by class.
        self.assertTrue(isinstance(policy.get_policy(TestAuthnPolicy1),
                                   TestAuthnPolicy1))
        self.assertTrue(isinstance(policy.get_policy(TestAuthnPolicy2),
                                   TestAuthnPolicy2))
        self.assertTrue(isinstance(policy.get_policy(TestAuthnPolicy3),
                                   TestAuthnPolicy3))
        self.assertEquals(policy.get_policy(MultiAuthPolicyTests), None)

    def test_get_policies(self):
        self.config.add_settings({
            "multiauth.policies":
                "pyramid_multiauth.tests.testincludeme1 policy1 policy2",
            "multiauth.policy.policy1.use":
                "pyramid_multiauth.tests.TestAuthnPolicy2",
            "multiauth.policy.policy2.use":
                "pyramid_multiauth.tests.TestAuthnPolicy3"
        })
        self.config.include("pyramid_multiauth")
        self.config.commit()
        policy = self.config.registry.getUtility(IAuthenticationPolicy)
        policies = policy.get_policies()
        expected_result = [
            ("pyramid_multiauth.tests.testincludeme1", TestAuthnPolicy1),
            ("policy1", TestAuthnPolicy2),
            ("policy2", TestAuthnPolicy3),
        ]
        for (obtained, expected) in zip(policies, expected_result):
            self.assertEquals(obtained[0], expected[0])
            self.assertTrue(isinstance(obtained[1], expected[1]))
