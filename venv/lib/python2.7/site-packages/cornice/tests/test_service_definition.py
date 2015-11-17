# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from pyramid import testing
from webtest import TestApp

from cornice import Service
from cornice.tests.support import TestCase, CatchErrors


service1 = Service(name="service1", path="/service1")
service2 = Service(name="service2", path="/service2")


@service1.get()
def get1(request):
    return {"test": "succeeded"}


@service1.post()
def post1(request):
    return {"body": request.body}


@service2.get(accept="text/html")
@service2.post(accept="audio/ogg")
def get2_or_post2(request):
    return {"test": "succeeded"}


class TestServiceDefinition(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_service_definition")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_basic_service_operation(self):

        self.app.get("/unknown", status=404)
        self.assertEqual(
            self.app.get("/service1").json,
            {'test': "succeeded"})

        self.assertEqual(
            self.app.post("/service1", params="BODY").json,
            {'body': 'BODY'})

    def test_loading_into_multiple_configurators(self):
        # When initializing a second configurator, it shouldn't interfere
        # with the one already in place.
        config2 = testing.setUp()
        config2.include("cornice")
        config2.scan("cornice.tests.test_service_definition")

        # Calling the new configurator works as expected.
        app = TestApp(CatchErrors(config2.make_wsgi_app()))
        self.assertEqual(
            app.get("/service1").json,
            {'test': 'succeeded'})

        # Calling the old configurator works as expected.
        self.assertEqual(
            self.app.get("/service1").json,
            {'test': 'succeeded'})

    def test_stacking_api_decorators(self):
        # Stacking multiple @api calls on a single function should
        # register it multiple times, just like @view_config does.
        resp = self.app.get("/service2", headers={'Accept': 'text/html'})
        self.assertEqual(resp.json, {'test': 'succeeded'})

        resp = self.app.post("/service2", headers={'Accept': 'audio/ogg'})
        self.assertEqual(resp.json, {'test': 'succeeded'})
