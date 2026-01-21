# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from unittest import TestCase, mock

from pyramid.exceptions import ConfigurationError
from pyramid.interfaces import IRendererFactory

from kinto.core.cornice.service import (
    Service,
    _UnboundView,
    clear_services,
    decorate_view,
    get_services,
)
from kinto.core.cornice.util import func_name


def _validator(req):
    return True


def _validator2(req):
    return True


def _stub(req):
    return None


class TestService(TestCase):
    def tearDown(self):
        clear_services()

    def test_service_instantiation(self):
        service = Service("coconuts", "/migrate")
        self.assertEqual(service.name, "coconuts")
        self.assertEqual(service.path, "/migrate")
        self.assertEqual(service.renderer, Service.renderer)

        service = Service("coconuts", "/migrate", renderer="html")
        self.assertEqual(service.renderer, "html")

        # test that lists are also set
        validators = [
            lambda x: True,
        ]
        service = Service("coconuts", "/migrate", validators=validators)
        self.assertEqual(service.validators, validators)

    def test_representation(self):
        service = Service("coconuts", "/migrate")
        self.assertEqual(repr(service), "<Service coconuts at /migrate>")

    def test_representation_path(self):
        service = Service("coconuts", pyramid_route="some_route")
        self.assertEqual(repr(service), "<Service coconuts at some_route>")

    def test_get_arguments(self):
        service = Service("coconuts", "/migrate")
        # not specifying anything, we should get the default values
        args = service.get_arguments({})
        for arg in Service.mandatory_arguments:
            self.assertEqual(args[arg], getattr(Service, arg, None))

        # calling this method on a configured service should use the values
        # passed at instantiation time as default values
        service = Service("coconuts", "/migrate", renderer="html")
        args = service.get_arguments({})
        self.assertEqual(args["renderer"], "html")

        # if we specify another renderer for this service, despite the fact
        # that one is already set in the instance, this one should be used
        args = service.get_arguments({"renderer": "foobar"})
        self.assertEqual(args["renderer"], "foobar")

        # test that list elements are not overwritten
        # define a validator for the needs of the test

        service = Service("vaches", "/fetchez", validators=(_validator,))
        self.assertEqual(len(service.validators), 1)
        args = service.get_arguments({"validators": (_validator2,)})

        # the list of validators didn't changed
        self.assertEqual(len(service.validators), 1)

        # but the one returned contains 2 validators
        self.assertEqual(len(args["validators"]), 2)

        # test that exclude effectively removes the items from the list of
        # validators / filters it returns, without removing it from the ones
        # registered for the service.
        service = Service("open bar", "/bar", validators=(_validator, _validator2))
        self.assertEqual(service.validators, [_validator, _validator2])

        args = service.get_arguments({"exclude": _validator2})
        self.assertEqual(args["validators"], [_validator])

        # defining some non-mandatory arguments in a service should make
        # them available on further calls to get_arguments.

        service = Service("vaches", "/fetchez", foobar="baz")
        self.assertIn("foobar", service.arguments)
        self.assertIn("foobar", service.get_arguments())

    def test_view_registration(self):
        # registering a new view should make it available in the list.
        # The methods list is populated
        service = Service("color", "/favorite-color")

        def view(request):
            pass

        service.add_view("post", view, validators=(_validator,))
        self.assertEqual(len(service.definitions), 1)
        method, _view, _ = service.definitions[0]

        # the view had been registered. we also test here that the method had
        # been inserted capitalized (POST instead of post)
        self.assertEqual(("POST", view), (method, _view))

    def test_error_handler(self):
        error_handler = object()
        service = Service("color", "/favorite-color", error_handler=error_handler)

        @service.get()
        def get_favorite_color(request):
            return "blue, hmm, red, hmm, aaaaaaaah"

        method, view, args = service.definitions[0]
        self.assertIs(args["error_handler"], error_handler)

    def test_default_error_handler(self):
        # If not configured otherwise, Service.default_error_handler should
        # be used to handle and render errors.
        service = Service("error service", "/error_service")

        @service.get()
        def get_error(request):
            return "error"

        method, view, args = service.definitions[0]
        self.assertEqual(args["error_handler"], service.default_error_handler)

    def test_default_error_handler_calls_default_renderer(self):
        # Default error handler should call `render_errors` on the
        # registered renderer.
        service = Service("error service", "/error_service")

        renderer = mock.MagicMock()
        renderer.render_errors.return_value = "rendered_errors"

        request = mock.MagicMock()
        request.registry.queryUtility.return_value = renderer

        self.assertEqual(service.default_error_handler(request), "rendered_errors")
        request.registry.queryUtility.assert_called_with(IRendererFactory, name=service.renderer)
        renderer.render_errors.assert_called_with(request)

    def test_decorators(self):
        service = Service("color", "/favorite-color")

        @service.get()
        def get_favorite_color(request):
            return "blue, hmm, red, hmm, aaaaaaaah"

        self.assertEqual(2, len(service.definitions))
        method, view, _ = service.definitions[0]
        self.assertEqual(("GET", get_favorite_color), (method, view))
        method, view, _ = service.definitions[1]
        self.assertEqual(("HEAD", get_favorite_color), (method, view))

        @service.post(accept="text/plain", renderer="plain")
        @service.post(accept="application/json")
        def post_favorite_color(request):
            pass

        # using multiple decorators on a resource should register them all in
        # as many different definitions in the service
        self.assertEqual(4, len(service.definitions))

        @service.patch()
        def patch_favorite_color(request):
            return ""

        method, view, _ = service.definitions[4]
        self.assertEqual("PATCH", method)

        @service.put()
        def put_favorite_color(request):
            return ""

        method, view, _ = service.definitions[5]
        self.assertEqual("PUT", method)

        @service.delete()
        def delete_favorite_color(request):
            return ""

        method, view, _ = service.definitions[6]
        self.assertEqual("DELETE", method)

        @service.options()
        def favorite_color_options(request):
            return ""

        method, view, _ = service.definitions[7]
        self.assertEqual("OPTIONS", method)

    def test_get_acceptable(self):
        # defining a service with different "accept" headers, we should be able
        # to retrieve this information easily
        service = Service("color", "/favorite-color")
        service.add_view("GET", lambda x: "blue", accept="text/plain")
        self.assertEqual(service.get_acceptable("GET"), ["text/plain"])

        service.add_view("GET", lambda x: "blue", accept="application/json")
        self.assertEqual(service.get_acceptable("GET"), ["text/plain", "application/json"])

        # adding a view for the POST method should not break everything :-)
        service.add_view("POST", lambda x: "ok", accept=("foo/bar"))
        self.assertEqual(service.get_acceptable("GET"), ["text/plain", "application/json"])
        # and of course the list of accepted egress content-types should be
        # available for the "POST" as well.
        self.assertEqual(service.get_acceptable("POST"), ["foo/bar"])

        # it is possible to give acceptable egress content-types dynamically at
        # run-time. You don't always want to have the callables when retrieving
        # all the acceptable content-types
        service.add_view("POST", lambda x: "ok", accept=lambda r: "application/json")
        self.assertEqual(len(service.get_acceptable("POST")), 2)
        self.assertEqual(len(service.get_acceptable("POST", True)), 1)

    def test_get_contenttypes(self):
        # defining a service with different "content_type" headers, we should
        # be able to retrieve this information easily
        service = Service("color", "/favorite-color")
        service.add_view("GET", lambda x: "blue", content_type="text/plain")
        self.assertEqual(service.get_contenttypes("GET"), ["text/plain"])

        service.add_view("GET", lambda x: "blue", content_type="application/json")
        self.assertEqual(service.get_contenttypes("GET"), ["text/plain", "application/json"])

        # adding a view for the POST method should not break everything :-)
        service.add_view("POST", lambda x: "ok", content_type=("foo/bar"))
        self.assertEqual(service.get_contenttypes("GET"), ["text/plain", "application/json"])
        # and of course the list of supported ingress content-types should be
        # available for the "POST" as well.
        self.assertEqual(service.get_contenttypes("POST"), ["foo/bar"])

        # it is possible to give supported ingress content-types dynamically at
        # run-time. You don't always want to have the callables when retrieving
        # all the supported content-types
        service.add_view("POST", lambda x: "ok", content_type=lambda r: "application/json")
        self.assertEqual(len(service.get_contenttypes("POST")), 2)
        self.assertEqual(len(service.get_contenttypes("POST", True)), 1)

    def test_class_parameters(self):
        # when passing a "klass" argument, it gets registered. It also tests
        # that the view argument can be a string and not a callable.
        class TemperatureCooler(object):
            def get_fresh_air(self):
                pass

        service = Service("TemperatureCooler", "/freshair", klass=TemperatureCooler)
        service.add_view("get", "get_fresh_air")

        self.assertEqual(len(service.definitions), 2)

        method, view, args = service.definitions[0]
        self.assertEqual(view, "get_fresh_air")
        self.assertEqual(args["klass"], TemperatureCooler)

    def test_get_services(self):
        self.assertEqual([], get_services())
        foobar = Service("Foobar", "/foobar")
        self.assertIn(foobar, get_services())

        barbaz = Service("Barbaz", "/barbaz")
        self.assertIn(barbaz, get_services())

        self.assertEqual(
            [
                barbaz,
            ],
            get_services(
                exclude=[
                    "Foobar",
                ]
            ),
        )
        self.assertEqual(
            [
                foobar,
            ],
            get_services(
                names=[
                    "Foobar",
                ]
            ),
        )
        self.assertEqual([foobar, barbaz], get_services(names=["Foobar", "Barbaz"]))

    def test_default_validators(self):
        old_validators = Service.default_validators
        try:

            def custom_validator(request):
                pass

            def custom_filter(request):
                pass

            def freshair(request):
                pass

            # the default validators should be used when registering a service
            Service.default_validators = [
                custom_validator,
            ]
            service = Service("TemperatureCooler", "/freshair")
            service.add_view("GET", freshair)
            method, view, args = service.definitions[0]

            self.assertIn(custom_validator, args["validators"])

            # defining a service with additional filters / validators should
            # work as well
            def another_validator(request):
                pass

            def groove_em_all(request):
                pass

            service2 = Service(
                "FunkyGroovy",
                "/funky-groovy",
                validators=[another_validator],
            )

            service2.add_view("GET", groove_em_all)
            method, view, args = service2.definitions[0]

            self.assertIn(custom_validator, args["validators"])
            self.assertIn(another_validator, args["validators"])
        finally:
            Service.default_validators = old_validators

    def test_cors_headers_for_service_instantiation(self):
        # When defining services, it's possible to add headers. This tests
        # it is possible to list all the headers supported by a service.
        service = Service("coconuts", "/migrate", cors_headers=("X-Header-Coconut"))
        self.assertNotIn("X-Header-Coconut", service.cors_supported_headers_for())

        service.add_view("POST", _stub)
        self.assertIn("X-Header-Coconut", service.cors_supported_headers_for())

    def test_cors_headers_for_view_definition(self):
        # defining headers in the view should work.
        service = Service("coconuts", "/migrate")
        service.add_view("POST", _stub, cors_headers=("X-Header-Foobar"))
        self.assertIn("X-Header-Foobar", service.cors_supported_headers_for())

    def test_cors_headers_for_method(self):
        # defining headers in the view should work.
        service = Service("coconuts", "/migrate")
        service.add_view("GET", _stub, cors_headers=("X-Header-Foobar"))
        service.add_view("POST", _stub, cors_headers=("X-Header-Barbaz"))
        get_headers = service.cors_supported_headers_for(method="GET")
        self.assertNotIn("X-Header-Barbaz", get_headers)

    def test_cors_headers_for_method_are_deduplicated(self):
        # defining headers in the view should work.
        service = Service("coconuts", "/migrate")
        service.cors_headers = ("X-Header-Foobar",)
        service.add_view("GET", _stub, cors_headers=("X-Header-Foobar", "X-Header-Barbaz"))
        get_headers = service.cors_supported_headers_for(method="GET")
        expected = set(["X-Header-Foobar", "X-Header-Barbaz"])
        self.assertEqual(expected, get_headers)

    def test_cors_supported_methods(self):
        foo = Service(name="foo", path="/foo")
        foo.add_view("GET", _stub)
        self.assertIn("GET", foo.cors_supported_methods)

        foo.add_view("POST", _stub)
        self.assertIn("POST", foo.cors_supported_methods)

    def test_cors_supported_origins(self):
        foo = Service(name="foo", path="/foo", cors_origins=("mozilla.org",))

        foo.add_view("GET", _stub, cors_origins=("notmyidea.org", "lolnet.org"))

        self.assertIn("mozilla.org", foo.cors_supported_origins)
        self.assertIn("notmyidea.org", foo.cors_supported_origins)
        self.assertIn("lolnet.org", foo.cors_supported_origins)

    def test_per_method_supported_origins(self):
        foo = Service(name="foo", path="/foo", cors_origins=("mozilla.org",))
        foo.add_view("GET", _stub, cors_origins=("lolnet.org",))

        self.assertTrue("mozilla.org" in foo.cors_origins_for("GET"))
        self.assertTrue("lolnet.org" in foo.cors_origins_for("GET"))

        foo.add_view("POST", _stub)
        self.assertFalse("lolnet.org" in foo.cors_origins_for("POST"))

    def test_credential_support_can_be_enabled(self):
        foo = Service(name="foo", path="/foo", cors_credentials=True)
        foo.add_view("POST", _stub)
        self.assertTrue(foo.cors_support_credentials_for())

    def test_credential_support_is_disabled_by_default(self):
        foo = Service(name="foo", path="/foo")
        foo.add_view("POST", _stub)
        self.assertFalse(foo.cors_support_credentials_for())

    def test_per_method_credential_support(self):
        foo = Service(name="foo", path="/foo")
        foo.add_view("GET", _stub, cors_credentials=True)
        foo.add_view("POST", _stub)
        self.assertTrue(foo.cors_support_credentials_for("GET"))
        self.assertFalse(foo.cors_support_credentials_for("POST"))

    def test_method_takes_precendence_for_credential_support(self):
        foo = Service(name="foo", path="/foo", cors_credentials=True)
        foo.add_view("GET", _stub, cors_credentials=False)
        self.assertFalse(foo.cors_support_credentials_for("GET"))

    def test_max_age_is_none_if_undefined(self):
        foo = Service(name="foo", path="/foo")
        foo.add_view("POST", _stub)
        self.assertIsNone(foo.cors_max_age_for("POST"))

    def test_max_age_can_be_defined(self):
        foo = Service(name="foo", path="/foo", cors_max_age=42)
        foo.add_view("POST", _stub)
        self.assertEqual(foo.cors_max_age_for(), 42)

    def test_max_age_can_be_different_dependeing_methods(self):
        foo = Service(name="foo", path="/foo", cors_max_age=42)
        foo.add_view("GET", _stub)
        foo.add_view("POST", _stub, cors_max_age=32)
        foo.add_view("PUT", _stub, cors_max_age=7)

        self.assertEqual(foo.cors_max_age_for("GET"), 42)
        self.assertEqual(foo.cors_max_age_for("POST"), 32)
        self.assertEqual(foo.cors_max_age_for("PUT"), 7)

    def test_cors_policy(self):
        policy = {"origins": ("foo", "bar", "baz")}
        foo = Service(name="foo", path="/foo", cors_policy=policy)
        self.assertTrue("foo" in foo.cors_supported_origins)
        self.assertTrue("bar" in foo.cors_supported_origins)
        self.assertTrue("baz" in foo.cors_supported_origins)

    def test_cors_policy_can_be_overwritten(self):
        policy = {"origins": ("foo", "bar", "baz")}
        foo = Service(name="foo", path="/foo", cors_origins=(), cors_policy=policy)
        self.assertEqual(len(foo.cors_supported_origins), 0)

    def test_can_specify_a_view_decorator(self):
        def dummy_decorator(view):
            return view

        service = Service("coconuts", "/migrate", decorator=dummy_decorator)
        args = service.get_arguments({})
        self.assertEqual(args["decorator"], dummy_decorator)

        # make sure Service.decorator() still works
        @service.decorator("put")
        def dummy_view(request):
            return "data"

        self.assertTrue(any(view is dummy_view for method, view, args in service.definitions))

    def test_cannot_specify_both_factory_and_acl(self):
        with self.assertRaises(ConfigurationError):
            Service(
                "coconuts",
                "/migrate",
                acl="dummy_permission",
                factory="TheFactoryMethodCalledByPyramid",
            )

    def test_decorate_view(self):
        def myfunction():
            pass

        meth = "POST"
        decorated = decorate_view(myfunction, {}, meth)
        self.assertEqual(decorated.__name__, "{0}__{1}".format(func_name(myfunction), meth))

    def test_decorate_resource_view(self):
        class MyResource(object):
            def __init__(self, **kwargs):
                pass

            def myview(self):
                pass

        meth = "POST"
        decorated = decorate_view(_UnboundView(MyResource, "myview"), {}, meth)
        self.assertEqual(decorated.__name__, "{0}__{1}".format(func_name(MyResource.myview), meth))
