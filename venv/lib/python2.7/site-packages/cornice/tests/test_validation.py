# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid.config import Configurator
import simplejson as json

from webtest import TestApp

from cornice.errors import Errors
from cornice.tests.validationapp import main, includeme, dummy_deserializer
from cornice.tests.support import LoggingCatcher, TestCase, CatchErrors


class TestServiceDefinition(LoggingCatcher, TestCase):

    def test_validation(self):
        app = TestApp(main({}))
        app.get('/service', status=400)

        response = app.post('/service', params='buh', status=400)
        self.assertTrue(b'Not a json body' in response.body)

        response = app.post('/service', params=json.dumps('buh'))

        expected = json.dumps({'body': '"buh"'}).encode('ascii')
        self.assertEqual(response.body, expected)

        app.get('/service?paid=yup')

        # valid = foo is one
        response = app.get('/service?foo=1&paid=yup')
        self.assertEqual(response.json['foo'], 1)

        # invalid value for foo
        response = app.get('/service?foo=buh&paid=yup', status=400)

        # check that json is returned
        errors = Errors.from_json(response.body)
        self.assertEqual(len(errors), 1)

    def test_validation_hooked_error_response(self):
        app = TestApp(main({}))

        response = app.post('/service4', status=400)
        self.assertTrue(b'<errors>' in response.body)

    def test_accept(self):
        # tests that the accept headers are handled the proper way
        app = TestApp(main({}))

        # requesting the wrong accept header should return a 406 ...
        response = app.get('/service2', headers={'Accept': 'audio/*'},
                           status=406)

        # ... with the list of accepted content-types
        error_location = response.json['errors'][0]['location']
        error_name = response.json['errors'][0]['name']
        error_description = response.json['errors'][0]['description']
        self.assertEquals('header', error_location)
        self.assertEquals('Accept', error_name)
        self.assertTrue('application/json' in error_description)
        self.assertTrue('text/json' in error_description)
        self.assertTrue('text/plain' in error_description)

        # requesting a supported type should give an appropriate response type
        response = app.get('/service2', headers={'Accept': 'application/*'})
        self.assertEqual(response.content_type, "application/json")

        response = app.get('/service2', headers={'Accept': 'text/plain'})
        self.assertEqual(response.content_type, "text/plain")

        # it should also work with multiple Accept headers
        response = app.get('/service2', headers={
            'Accept': 'audio/*, application/*'
        })
        self.assertEqual(response.content_type, "application/json")

        # and requested preference order should be respected
        headers = {'Accept': 'application/json; q=1.0, text/plain; q=0.9'}
        response = app.get('/service2', headers=headers)
        self.assertEqual(response.content_type, "application/json")

        headers = {'Accept': 'application/json; q=0.9, text/plain; q=1.0'}
        response = app.get('/service2', headers=headers)
        self.assertEqual(response.content_type, "text/plain")

        # test that using a callable to define what's accepted works as well
        response = app.get('/service3', headers={'Accept': 'audio/*'},
                           status=406)
        error_description = response.json['errors'][0]['description']
        self.assertTrue('text/json' in error_description)

        response = app.get('/service3', headers={'Accept': 'text/*'})
        self.assertEqual(response.content_type, "text/json")

        # if we are not asking for a particular content-type,
        # we should get one of the two types that the service supports.
        response = app.get('/service2')
        self.assertTrue(response.content_type
                        in ("application/json", "text/plain"))

    def test_accept_issue_113_text_star(self):
        app = TestApp(main({}))

        response = app.get('/service3', headers={'Accept': 'text/*'})
        self.assertEqual(response.content_type, "text/json")

    def test_accept_issue_113_text_application_star(self):
        app = TestApp(main({}))

        response = app.get('/service3', headers={'Accept': 'application/*'})
        self.assertEqual(response.content_type, "application/json")

    def test_accept_issue_113_text_application_json(self):
        app = TestApp(main({}))

        response = app.get('/service3', headers={'Accept': 'application/json'})
        self.assertEqual(response.content_type, "application/json")

    def test_accept_issue_113_text_html_not_acceptable(self):
        app = TestApp(main({}))

        # requesting an unsupported content type should return a HTTP 406 (Not
        # Acceptable)
        app.get('/service3', headers={'Accept': 'text/html'}, status=406)

    def test_accept_issue_113_audio_or_text(self):
        app = TestApp(main({}))

        response = app.get('/service2', headers={
            'Accept': 'audio/mp4; q=0.9, text/plain; q=0.5'
        })
        self.assertEqual(response.content_type, "text/plain")

        # if we are not asking for a particular content-type,
        # we should get one of the two types that the service supports.
        response = app.get('/service2')
        self.assertTrue(response.content_type
                        in ("application/json", "text/plain"))

    def test_override_default_accept_issue_252(self):
        # override default acceptable content_types for interoperate with
        # legacy applications i.e. ExtJS 3
        from cornice.util import _JsonRenderer
        _JsonRenderer.acceptable += ('text/html',)

        app = TestApp(main({}))

        response = app.get('/service5', headers={'Accept': 'text/html'})
        self.assertEqual(response.content_type, "text/html")
        # revert the override
        _JsonRenderer.acceptable = _JsonRenderer.acceptable[:-1]

    def test_filters(self):
        app = TestApp(main({}))

        # filters can be applied to all the methods of a service
        self.assertTrue(b"filtered response" in app.get('/filtered').body)
        self.assertTrue(b"unfiltered" in app.post('/filtered').body)

    def test_multiple_querystrings(self):
        app = TestApp(main({}))

        # it is possible to have more than one value with the same name in the
        # querystring
        self.assertEquals(b'{"field": ["5"]}', app.get('/foobaz?field=5').body)
        self.assertEquals(b'{"field": ["5", "2"]}',
                          app.get('/foobaz?field=5&field=2').body)

    def test_email_field(self):
        app = TestApp(main({}))
        content = {'email': 'alexis@notmyidea.org'}
        app.post_json('/newsletter', params=content)

    def test_content_type_missing(self):
        # test that a Content-Type request headers is present
        app = TestApp(main({}))

        # requesting without a Content-Type header should return a 415 ...
        request = app.RequestClass.blank('/service5', method='POST')
        response = app.do_request(request, 415, True)

        # ... with an appropriate json error structure
        error_location = response.json['errors'][0]['location']
        error_name = response.json['errors'][0]['name']
        error_description = response.json['errors'][0]['description']
        self.assertEqual('header', error_location)
        self.assertEqual('Content-Type', error_name)
        self.assertTrue('application/json' in error_description)

    def test_content_type_wrong_single(self):
        # tests that the Content-Type request header satisfies the requirement
        app = TestApp(main({}))

        # requesting the wrong Content-Type header should return a 415 ...
        response = app.post('/service5',
                            headers={'Content-Type': 'text/plain'},
                            status=415)

        # ... with an appropriate json error structure
        error_description = response.json['errors'][0]['description']
        self.assertTrue('application/json' in error_description)

    def test_content_type_wrong_multiple(self):
        # tests that the Content-Type request header satisfies the requirement
        app = TestApp(main({}))

        # requesting the wrong Content-Type header should return a 415 ...
        response = app.put('/service5',
                           headers={'Content-Type': 'text/xml'},
                           status=415)

        # ... with an appropriate json error structure
        error_description = response.json['errors'][0]['description']
        self.assertTrue('text/plain' in error_description)
        self.assertTrue('application/json' in error_description)

    def test_content_type_correct(self):
        # tests that the Content-Type request header satisfies the requirement
        app = TestApp(main({}))

        # requesting with one of the allowed Content-Type headers should work,
        # even when having a charset parameter as suffix
        response = app.put('/service5', headers={
            'Content-Type': 'text/plain; charset=utf-8'
        })
        self.assertEqual(response.json, "some response")

    def test_content_type_on_get(self):
        # test that a Content-Type request header is not
        # checked on GET requests, they don't usually have a body
        app = TestApp(main({}))
        response = app.get('/service5')
        self.assertEqual(response.json, "some response")

    def test_content_type_with_callable(self):
        # test that using a callable for content_type works as well
        app = TestApp(main({}))
        response = app.post('/service6', headers={'Content-Type': 'audio/*'},
                            status=415)
        error_description = response.json['errors'][0]['description']
        self.assertTrue('text/xml' in error_description)
        self.assertTrue('application/json' in error_description)

        app.post('/service6', headers={'Content-Type': 'text/xml'})

    def test_accept_and_content_type(self):
        # tests that giving both Accept and Content-Type
        # request headers satisfy the requirement
        app = TestApp(main({}))

        # POST endpoint just has one accept and content_type definition
        response = app.post('/service7', headers={
            'Accept': 'text/xml, application/json',
            'Content-Type': 'application/json; charset=utf-8'
        })
        self.assertEqual(response.json, "some response")

        response = app.post(
            '/service7',
            headers={
                'Accept': 'text/plain, application/json',
                'Content-Type': 'application/json; charset=utf-8'
            },
            status=406)

        response = app.post(
            '/service7',
            headers={
                'Accept': 'text/xml, application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            status=415)

        # PUT endpoint has a list of accept and content_type definitions
        response = app.put('/service7', headers={
            'Accept': 'text/xml, application/json',
            'Content-Type': 'application/json; charset=utf-8'
        })
        self.assertEqual(response.json, "some response")

        response = app.put(
            '/service7',
            headers={
                'Accept': 'audio/*',
                'Content-Type': 'application/json; charset=utf-8'
            },
            status=406)

        response = app.put(
            '/service7',
            headers={
                'Accept': 'text/xml, application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }, status=415)


class TestRequestDataExtractors(LoggingCatcher, TestCase):

    def make_ordinary_app(self):
        return TestApp(main({}))

    def make_app_with_deserializer(self, deserializer):
        config = Configurator(settings={})
        config.include(includeme)
        config.add_cornice_deserializer('text/dummy', deserializer)
        return TestApp(CatchErrors(config.make_wsgi_app()))

    def test_valid_json(self):
        app = self.make_ordinary_app()
        response = app.post_json('/foobar?yeah=test', {
            'foo': 'hello',
            'bar': 'open',
            'yeah': 'man',
        })
        self.assertEqual(response.json['test'], 'succeeded')

    def test_invalid_json(self):
        app = self.make_ordinary_app()
        response = app.post('/foobar?yeah=test',
                            "invalid json input",
                            headers={'content-type': 'application/json'},
                            status=400)
        self.assertEqual(response.json['status'], 'error')
        error_description = response.json['errors'][0]['description']
        self.assertIn('Invalid JSON', error_description)

    def test_json_text(self):
        app = self.make_ordinary_app()
        response = app.post('/foobar?yeah=test',
                            '"invalid json input"',
                            headers={'content-type': 'application/json'},
                            status=400)
        self.assertEqual(response.json['status'], 'error')
        error_description = response.json['errors'][0]['description']
        self.assertIn('Should be a JSON object', error_description)

    def test_www_form_urlencoded(self):
        app = self.make_ordinary_app()
        response = app.post('/foobar?yeah=test', {
            'foo': 'hello',
            'bar': 'open',
            'yeah': 'man',
        })
        self.assertEqual(response.json['test'], 'succeeded')

    def test_deserializer_from_global_config(self):
        app = self.make_app_with_deserializer(dummy_deserializer)
        response = app.post('/foobar?yeah=test', "hello,open,yeah",
                            headers={'content-type': 'text/dummy'})
        self.assertEqual(response.json['test'], 'succeeded')

    def test_deserializer_from_view_config(self):
        app = self.make_ordinary_app()
        response = app.post('/custom_deserializer?yeah=test',
                            "hello,open,yeah",
                            headers={'content-type': 'text/dummy'})
        self.assertEqual(response.json['test'], 'succeeded')

    def test_view_config_has_priority_over_global_config(self):
        def low_priority_deserializer(request):
            return "we don't want this"
        app = self.make_app_with_deserializer(low_priority_deserializer)
        response = app.post('/custom_deserializer?yeah=test',
                            "hello,open,yeah",
                            headers={'content-type': 'text/dummy'})
        self.assertEqual(response.json['test'], 'succeeded')
