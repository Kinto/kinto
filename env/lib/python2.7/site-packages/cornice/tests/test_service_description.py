# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import warnings

from pyramid import testing
from webtest import TestApp

from cornice.schemas import CorniceSchema
from cornice.tests.validationapp import COLANDER
from cornice.tests.support import TestCase, CatchErrors
from cornice.service import Service

if COLANDER:
    from cornice.tests.validationapp import FooBarSchema
    from colander import (MappingSchema, SchemaNode, String, SequenceSchema,
                          Length)

    class SchemaFromQuerystring(MappingSchema):
        yeah = SchemaNode(String(), location="querystring", type='str')

    class SchemaFromHeader(MappingSchema):
        x_qux = SchemaNode(String(), location="header", type='str',
                           name="X-Qux")

    class ModelField(MappingSchema):
        name = SchemaNode(String())
        description = SchemaNode(String())

    class ModelFields(SequenceSchema):
        field = ModelField()

    class ModelDefinition(MappingSchema):
        title = SchemaNode(String(), location="body")
        fields = ModelFields(validator=Length(min=1), location="body")

    nested_service = Service(name='nested', path='/nested')

    @nested_service.post(schema=ModelDefinition)
    def get_nested(request):
        return "yay"

    foobar = Service(name="foobar", path="/foobar")

    @foobar.post(schema=FooBarSchema)
    def foobar_post(request):
        return {"test": "succeeded", 'baz': request.validated['baz']}

    @foobar.get(schema=SchemaFromQuerystring)
    def foobar_get(request):
        return {"test": "succeeded"}

    @foobar.delete(schema=SchemaFromHeader)
    def foobar_delete(request):
        return {"test": "succeeded"}

    class TestServiceDescription(TestCase):

        def setUp(self):
            self.config = testing.setUp()
            self.config.include("cornice")
            self.config.scan("cornice.tests.test_service_description")
            self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

        def tearDown(self):
            testing.tearDown()

        def test_get_from_colander(self):
            schema = CorniceSchema.from_colander(FooBarSchema)
            attrs = schema.as_dict()
            self.assertEqual(len(attrs), 6)

        def test_description_attached(self):
            # foobar should contain a schema argument containing the cornice
            # schema object, so it can be introspected if needed
            # accessing Service.schemas emits a warning
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                self.assertTrue('POST' in foobar.schemas)
                self.assertEqual(len(w), 1)

        def test_schema_validation(self):
            # using a colander schema for the service should automatically
            # validate the request calls. Let's make some of them here.
            resp = self.app.post('/foobar', status=400)
            self.assertEqual(resp.json['status'], 'error')

            errors = resp.json['errors']
            # we should at have 1 missing value in the QS...
            self.assertEqual(1, len([e for e in errors
                                    if e['location'] == "querystring"]))

            # ... and 2 in the body (a json error as well)
            self.assertEqual(2, len([e for e in errors
                                    if e['location'] == "body"]))

            # let's do the same request, but with information in the
            # querystring
            resp = self.app.post('/foobar?yeah=test', status=400)

            # we should have no missing value in the QS
            self.assertEqual(0, len([e for e in resp.json['errors']
                                    if e['location'] == "querystring"]))

            # and if we add the required values in the body of the post,
            # then we should be good
            data = {'foo': 'yeah', 'bar': 'open'}
            resp = self.app.post_json('/foobar?yeah=test',
                                      params=data, status=200)

            self.assertEqual(resp.json, {u'baz': None, "test": "succeeded"})

        def test_schema_validation2(self):
            resp = self.app.get('/foobar?yeah=test', status=200)
            self.assertEqual(resp.json, {"test": "succeeded"})

        def test_bar_validator(self):
            # test validator on bar attribute
            data = {'foo': 'yeah', 'bar': 'closed'}
            resp = self.app.post_json('/foobar?yeah=test', params=data,
                                      status=400)

            self.assertEqual(resp.json, {
                u'errors': [{u'description': u'The bar is not open.',
                             u'location': u'body',
                             u'name': u'bar'}],
                u'status': u'error'})

        def test_foo_required(self):
            # test required attribute
            data = {'bar': 'open'}
            resp = self.app.post_json('/foobar?yeah=test', params=data,
                                      status=400)

            self.assertEqual(resp.json, {
                u'errors': [{u'description': u'foo is missing',
                             u'location': u'body',
                             u'name': u'foo'}],
                u'status': u'error'})

        def test_default_baz_value(self):
            # test required attribute
            data = {'foo': 'yeah', 'bar': 'open'}
            resp = self.app.post_json('/foobar?yeah=test', params=data,
                                      status=200)

            self.assertEqual(resp.json, {u'baz': None, "test": "succeeded"})

        def test_ipsum_error_message(self):
            # test required attribute
            data = {'foo': 'yeah', 'bar': 'open', 'ipsum': 5}
            resp = self.app.post_json('/foobar?yeah=test',
                                      params=data,
                                      status=400)

            self.assertEqual(resp.json, {
                u'errors': [
                    {u'description': u'5 is greater than maximum value 3',
                     u'location': u'body',
                     u'name': u'ipsum'}],
                u'status': u'error'})

        def test_integers_fail(self):
            # test required attribute
            data = {'foo': 'yeah', 'bar': 'open', 'ipsum': 2,
                    'integers': ('a', '2')}
            resp = self.app.post_json('/foobar?yeah=test', data,
                                      status=400)

            self.assertEqual(resp.json, {
                u'errors': [
                    {u'description': u'"a" is not a number',
                     u'location': u'body',
                     u'name': u'integers.0'}],
                u'status': u'error'})

        def test_integers_ok(self):
            # test required attribute
            data = {'foo': 'yeah', 'bar': 'open', 'ipsum': 2,
                    'integers': ('1', '2')}
            self.app.post_json('/foobar?yeah=test', params=data,
                               status=200)

        def test_nested_schemas(self):

            data = {"title": "Mushroom",
                    "fields": [{"name": "genre", "description": "Genre"}]}

            nested_data = {"title": "Mushroom",
                           "fields": [{"schmil": "Blick"}]}

            self.app.post_json('/nested', params=data, status=200)
            self.app.post_json('/nested', params=nested_data,
                               status=400)

        def test_nested_schemas_with_flattened_values(self):

            data = {"title": "Mushroom",
                    "fields.0.name": "genre",
                    "fields.0.description": "Genre"}

            self.app.post('/nested', params=data, status=200)

        def test_qux_header(self):
            resp = self.app.delete('/foobar', status=400)
            self.assertEqual(resp.json, {
                u'errors': [
                    {u'description': u'X-Qux is missing',
                     u'location': u'header',
                     u'name': u'X-Qux'}],
                u'status': u'error'})

            self.app.delete('/foobar', headers={'X-Qux': 'Hotzenplotz'},
                            status=200)
