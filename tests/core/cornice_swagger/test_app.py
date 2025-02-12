import unittest

import webtest
from flex.core import validate
from pyramid import testing

from kinto.core.cornice import Service
from kinto.core.cornice.service import clear_services
from kinto.core.cornice.validators import colander_validator
from kinto.core.cornice_swagger import CorniceSwagger

from .support import GetRequestSchema, PutRequestSchema, response_schemas


class AppTest(unittest.TestCase):
    def tearDown(self):
        clear_services()
        testing.tearDown()

    def setUp(self):
        service = Service("IceCream", "/icecream/{flavour}")

        @service.get(
            validators=(colander_validator,),
            schema=GetRequestSchema(),
            response_schemas=response_schemas,
        )
        def view_get(request):
            """Serve icecream"""
            return request.validated

        @service.put(validators=(colander_validator,), schema=PutRequestSchema())
        def view_put(request):
            """Add flavour"""
            return request.validated

        api_service = Service("OpenAPI", "/api")

        @api_service.get()
        def api_get(request):
            swagger = CorniceSwagger([service, api_service])
            return swagger.generate("IceCreamAPI", "4.2")

        self.config = testing.setUp()
        self.config.add_route("ice_test", "/ice_test/{flavour}")
        self.config.include("kinto.core.cornice")
        self.config.include("kinto.core.cornice_swagger")
        self.config.add_cornice_service(service)
        self.config.add_cornice_service(api_service)
        self.app = webtest.TestApp(self.config.make_wsgi_app())

    def test_app_get(self):
        self.app.get("/icecream/strawberry")

    def test_app_put(self):
        body = {"id": "chocolate", "timestamp": 123, "obj": {"my_precious": True}}
        headers = {"bar": "foo"}
        self.app.put_json("/icecream/chocolate", body, headers=headers)

    def test_validate_spec(self):
        spec = self.app.get("/api").json
        validate(spec)


class AppGoodRoutesTest(unittest.TestCase):
    def tearDown(self):
        clear_services()
        testing.tearDown()

    def setUp(self):
        service = Service("Ice Route", pyramid_route="ice_test")

        @service.get()
        def view_get(request):
            """Serve icecream"""
            return request.validated

        self.config = testing.setUp()
        self.config.add_route("ice_test", "/ice_test/{flavour}")
        self.config.include("kinto.core.cornice")
        self.config.include("kinto.core.cornice_swagger")
        self.config.add_cornice_service(service)
        self.app = webtest.TestApp(self.config.make_wsgi_app())

    def test_route_explicit_registry(self):
        swagger = CorniceSwagger(get_services(), pyramid_registry=self.config.registry)
        spec = swagger.generate("IceCreamAPI", "4.2")
        self.assertIn("/ice_test/{flavour}", spec["paths"])

    def test_route_fallback_registry(self):
        swagger = CorniceSwagger(get_services())
        spec = swagger.generate("IceCreamAPI", "4.2")
        self.assertIn("/ice_test/{flavour}", spec["paths"])
