# -*- coding: utf-8 -*-
import colander
import mock

from readinglist.views.batch import BatchPayloadSchema, batch as batch_service
from readinglist.tests.support import BaseWebTest, unittest, DummyRequest


class BatchViewTest(BaseWebTest, unittest.TestCase):

    def test_does_not_require_authentication(self):
        body = {'requests': []}
        self.app.post_json('/batch', body)

    def test_returns_400_if_body_has_missing_requests(self):
        self.app.post('/batch', {}, headers=self.headers, status=400)

    def test_returns_responses_if_schema_is_valid(self):
        body = {'requests': []}
        resp = self.app.post_json('/batch', body, headers=self.headers)
        self.assertIn('responses', resp.json)

    def test_only_post_is_allowed(self):
        self.app.get('/batch', headers=self.headers, status=405)
        self.app.put('/batch', headers=self.headers, status=405)
        self.app.patch('/batch', headers=self.headers, status=405)
        self.app.delete('/batch', headers=self.headers, status=405)

    def test_responses_are_redirects_if_no_prefix(self):
        request = {'path': '/'}
        body = {'requests': [request]}
        resp = self.app.post_json('/batch', body, headers=self.headers)
        redirect = resp.json['responses'][0]
        self.assertEqual(redirect['path'], '/')
        self.assertEqual(redirect['status'], 307)
        self.assertEqual(redirect['body'], '')
        self.assertEqual(redirect['headers']['Location'], '/v0/')

    def test_responses_are_resolved_on_api_with_prefix(self):
        request = {'path': '/v0/'}
        body = {'requests': [request]}
        resp = self.app.post_json('/batch', body, headers=self.headers)
        hello = resp.json['responses'][0]
        self.assertEqual(hello['path'], '/v0/')
        self.assertEqual(hello['status'], 200)
        self.assertEqual(hello['body']['hello'], 'readinglist')
        self.assertIn('application/json', hello['headers']['Content-Type'])

    def test_empty_response_body_with_head(self):
        request = {'path': '/v0/', 'method': 'HEAD'}
        body = {'requests': [request]}
        resp = self.app.post_json('/batch', body, headers=self.headers)
        head = resp.json['responses'][0]
        self.assertEqual(head['body'], '')
        self.assertNotEqual(len(head['headers']), 0)

    def test_internal_errors_are_returned_within_responses(self):
        request = {'path': '/v0/'}
        body = {'requests': [request]}

        with mock.patch('readinglist.views.hello.get_eos') as mocked:
            mocked.side_effect = AttributeError
            resp = self.app.post_json('/batch', body, headers=self.headers)

        error = resp.json['responses'][0]
        self.assertEqual(error['status'], 500)
        self.assertEqual(error['body']['errno'], 999)

    def test_batch_cannot_be_recursive(self):
        requests = {'requests': [{'path': '/v0/'}]}
        request = {'method': 'POST', 'path': '/v0/batch', 'body': requests}
        body = {'requests': [request]}
        resp = self.app.post_json('/batch', body, status=400)
        self.assertIn('Recursive', resp.json['message'])


class BatchSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = BatchPayloadSchema()

    def assertInvalid(self, payload):
        self.assertRaises(colander.Invalid, self.schema.deserialize, payload)

    def test_requests_is_mandatory(self):
        self.assertInvalid({})

    def test_requests_schema_supports_null(self):
        self.schema.deserialize(colander.null)

    def test_unknown_attributes_are_dropped(self):
        deserialized = self.schema.deserialize({'requests': [], 'unknown': 42})
        self.assertNotIn('unknown', deserialized)

    def test_list_of_requests_can_be_empty(self):
        self.schema.deserialize({'requests': []})

    def test_list_of_requests_must_be_a_list(self):
        self.assertInvalid({'requests': {}})

    def test_list_of_requests_must_be_dicts(self):
        request = 42
        self.assertInvalid({'requests': [request]})

    def test_request_path_must_start_with_slash(self):
        request = {'path': 'http://localhost'}
        self.assertInvalid({'requests': [request]})

    def test_request_path_is_mandatory(self):
        request = {'method': 'HEAD'}
        self.assertInvalid({'requests': [request]})

    def test_request_method_must_be_known_uppercase_word(self):
        request = {'path': '/', 'method': 'get'}
        self.assertInvalid({'requests': [request]})

    #
    # headers
    #

    def test_request_headers_should_be_strings(self):
        headers = {'Accept': 3.14}
        request = {'path': '/', 'headers': headers}
        self.assertInvalid({'requests': [request]})

    def test_request_headers_cannot_be_recursive(self):
        headers = {'Accept': {'sub': 'dict'}}
        request = {'path': '/', 'headers': headers}
        self.assertInvalid({'requests': [request]})

    def test_request_headers_are_preserved(self):
        headers = {'Accept': 'audio/*'}
        request = {'path': '/', 'headers': headers}
        deserialized = self.schema.deserialize({'requests': [request]})
        self.assertEqual(deserialized['requests'][0]['headers']['Accept'],
                         'audio/*')

    #
    # body
    #

    def test_body_is_an_arbitrary_mapping(self):
        payload = {"json": "payload"}
        request = {'path': '/', 'body': payload}
        deserialized = self.schema.deserialize({'requests': [request]})
        self.assertEqual(deserialized['requests'][0]['body'], payload)

    #
    # defaults
    #

    def test_defaults_must_be_a_mapping_if_specified(self):
        request = {'path': '/'}
        batch_payload = {'requests': [request], 'defaults': 42}
        self.assertInvalid(batch_payload)

    def test_defaults_must_be_a_request_schema_if_specified(self):
        request = {'path': '/'}
        defaults = {'body': 3}
        batch_payload = {'requests': [request], 'defaults': defaults}
        self.assertInvalid(batch_payload)

    def test_unknown_defaults_are_ignored_silently(self):
        request = {'path': '/'}
        defaults = {'foo': 'bar'}
        batch_payload = {'requests': [request], 'defaults': defaults}
        result = self.schema.deserialize(batch_payload)
        self.assertNotIn('foo', result['requests'][0])

    def test_defaults_can_be_specified_empty(self):
        request = {'path': '/'}
        defaults = {}
        batch_payload = {'requests': [request], 'defaults': defaults}
        self.schema.deserialize(batch_payload)

    def test_defaults_values_are_applied_to_requests(self):
        request = {'path': '/'}
        defaults = {'body': {'json': 'payload'}}
        batch_payload = {'requests': [request], 'defaults': defaults}
        result = self.schema.deserialize(batch_payload)
        self.assertEqual(result['requests'][0]['body'], {'json': 'payload'})

    def test_defaults_headers_are_applied_to_requests(self):
        request = {'path': '/'}
        defaults = {'headers': {'Content-Type': 'text/html'}}
        batch_payload = {'requests': [request], 'defaults': defaults}
        result = self.schema.deserialize(batch_payload)
        self.assertEqual(result['requests'][0]['headers']['Content-Type'],
                         'text/html')

    def test_defaults_values_do_not_overwrite_requests_values(self):
        request = {'path': '/', 'headers': {'Authorization': 'me'}}
        defaults = {'headers': {'Authorization': 'you', 'Accept': '*/*'}}
        batch_payload = {'requests': [request], 'defaults': defaults}
        result = self.schema.deserialize(batch_payload)
        self.assertEqual(result['requests'][0]['headers'],
                         {'Authorization': 'me', 'Accept': '*/*'})

    def test_defaults_values_can_be_path(self):
        request = {}
        defaults = {'path': '/'}
        batch_payload = {'requests': [request], 'defaults': defaults}
        result = self.schema.deserialize(batch_payload)
        self.assertEqual(result['requests'][0]['path'], '/')

    def test_defaults_values_for_path_must_start_with_slash(self):
        request = {}
        defaults = {'path': 'http://localhost'}
        batch_payload = {'requests': [request], 'defaults': defaults}
        self.assertInvalid(batch_payload)


class BatchServiceTest(unittest.TestCase):
    def setUp(self):
        self.method, self.view, self.options = batch_service.definitions[0]
        self.request = DummyRequest()
        self.request.registry = mock.Mock(settings={})

    def post(self, validated):
        self.request.validated = validated
        return self.view(self.request)

    def test_returns_empty_list_of_responses_if_requests_empty(self):
        result = self.post({'requests': []})
        self.assertEqual(result['responses'], [])

    def test_returns_one_response_per_request(self):
        requests = [{'path': '/'}]
        result = self.post({'requests': requests})
        self.assertEqual(len(result['responses']), len(requests))

    def test_relies_on_pyramid_invoke_subrequest(self):
        self.post({'requests': [{'path': '/'}]})
        self.assertTrue(self.request.invoke_subrequest.called)

    def test_returns_requests_path_in_responses(self):
        result = self.post({'requests': [{'path': '/'}]})
        self.assertEqual(result['responses'][0]['path'], '/')

    def test_subrequests_are_GET_by_default(self):
        self.post({'requests': [{'path': '/'}]})
        subrequest, = self.request.invoke_subrequest.call_args[0]
        self.assertEqual(subrequest.method, 'GET')

    def test_original_request_headers_are_passed_to_subrequests(self):
        self.request.headers['Authorization'] = 'Basic ertyfghjkl'
        self.post({'requests': [{'path': '/'}]})
        subrequest, = self.request.invoke_subrequest.call_args[0]
        self.assertIn('Basic', subrequest.headers['Authorization'])

    def test_subrequests_body_are_json_serialized(self):
        request = {'path': '/', 'body': {'json': 'payload'}}
        self.post({'requests': [request]})
        subrequest, = self.request.invoke_subrequest.call_args[0]
        self.assertEqual(subrequest.body.decode('utf8'),
                         '{"json": "payload"}')

    def test_subrequests_body_have_json_content_type(self):
        self.request.headers['Content-Type'] = 'text/xml'
        request = {'path': '/', 'body': {'json': 'payload'}}
        self.post({'requests': [request]})
        subrequest, = self.request.invoke_subrequest.call_args[0]
        self.assertIn('application/json',
                      subrequest.headers['Content-Type'])

    def test_subrequests_body_have_utf8_charset(self):
        request = {'path': '/', 'body': {'json': u"😂"}}
        self.post({'requests': [request]})
        subrequest, = self.request.invoke_subrequest.call_args[0]
        self.assertIn('charset=utf-8', subrequest.headers['Content-Type'])
        self.assertEqual(subrequest.body.decode('utf8'),
                         '{"json": "\\ud83d\\ude02"}')

    def test_subrequests_paths_are_url_encoded(self):
        request = {'path': u'/ð ® ©'}
        self.post({'requests': [request]})
        subrequest, = self.request.invoke_subrequest.call_args[0]
        self.assertEqual(subrequest.path, '/%C3%B0%20%C2%AE%20%C2%A9')

    def test_number_of_requests_is_not_limited_by_default(self):
        requests = {}
        for i in range(500):
            requests.setdefault('requests', []).append({'path': '/'})
        self.post(requests)

    def test_return_400_if_number_of_requests_is_greater_than_settings(self):
        self.request.registry.settings['readinglist.batch_max_requests'] = 25

        requests = {}
        for i in range(26):
            requests.setdefault('requests', []).append({'path': '/'})
        result = self.post(requests)

        self.assertEqual(self.request.errors[0]['description'],
                         'Number of requests is limited to 25')
        self.assertIsNone(result)  # rest of view not executed
