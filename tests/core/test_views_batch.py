import colander
import mock
import uuid
import unittest

from pyramid.response import Response

from kinto.core.views.batch import BatchPayloadSchema, batch as batch_service
from kinto.core.testing import DummyRequest
from kinto.core.utils import json

from .support import BaseWebTest


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

    def test_defaults_are_applied_to_requests(self):
        request = {'path': '/v0/'}
        defaults = {'method': 'POST'}
        result = self.app.post_json('/batch',
                                    {'requests': [request],
                                     'defaults': defaults})
        self.assertEqual(result.json['responses'][0]['status'], 405)

    def test_only_post_is_allowed(self):
        self.app.get('/batch', headers=self.headers, status=405)
        self.app.put('/batch', headers=self.headers, status=405)
        self.app.patch('/batch', headers=self.headers, status=405)
        self.app.delete('/batch', headers=self.headers, status=405)

    def test_batch_adds_missing_api_with_prefix(self):
        request = {'path': '/v0/'}
        body = {'requests': [request]}
        resp = self.app.post_json('/batch', body, headers=self.headers)
        hello = resp.json['responses'][0]
        self.assertEqual(hello['path'], '/v0/')
        self.assertEqual(hello['status'], 200)
        self.assertEqual(hello['body']['project_name'], 'myapp')
        self.assertIn('application/json', hello['headers']['Content-Type'])

    def test_empty_response_body_with_head(self):
        request = {'path': '/v0/', 'method': 'HEAD'}
        body = {'requests': [request]}
        resp = self.app.post_json('/batch', body, headers=self.headers)
        head = resp.json['responses'][0]
        self.assertEqual(head['body'], '')
        self.assertNotEqual(len(head['headers']), 0)

    def test_api_errors_are_json_formatted(self):
        request = {'path': '/unknown'}
        body = {'requests': [request]}
        resp = self.app.post_json('/batch', body, headers=self.headers)
        error = resp.json['responses'][0]
        self.assertEqual(error['body']['code'], 404)

    def test_internal_errors_makes_the_batch_fail(self):
        request = {'path': '/v0/'}
        body = {'requests': [request]}

        with mock.patch('kinto.core.views.hello.get_eos') as mocked:
            mocked.side_effect = AttributeError
            self.app.post_json('/batch', body, headers=self.headers,
                               status=500)

    def test_errors_handled_by_view_does_not_make_the_batch_fail(self):
        from requests.exceptions import HTTPError

        request = {'path': '/v0/'}
        body = {'requests': [request]}

        with mock.patch('kinto.core.views.hello.get_eos') as mocked:
            response = mock.MagicMock(status_code=404)
            mocked.side_effect = HTTPError(response=response)
            resp = self.app.post_json('/batch', body, headers=self.headers,
                                      status=200)
            subresponse = resp.json['responses'][0]['body']
            self.assertEqual(subresponse, {
                'errno': 999,
                'code': 404,
                'error': 'Not Found'
            })

    def test_batch_cannot_be_recursive(self):
        requests = {'requests': [{'path': '/v0/'}]}
        request = {'method': 'POST', 'path': '/v0/batch', 'body': requests}
        body = {'requests': [request]}
        resp = self.app.post_json('/batch', body, status=400)
        self.assertIn('Recursive', resp.json['message'])

    def test_batch_validates_json(self):
        body = """{"requests": [{"path": "/v0/"},]}"""
        resp = self.app.post('/batch', body, status=400,
                             headers={'Content-Type': 'application/json'})
        self.assertIn('Invalid JSON', resp.json['message'])

    def test_responses_are_resolved_with_api_with_prefix(self):
        request = {'path': '/'}
        body = {'requests': [request]}
        resp = self.app.post_json('/batch', body, headers=self.headers)
        hello = resp.json['responses'][0]
        self.assertEqual(hello['path'], '/v0/')
        self.assertEqual(hello['status'], 200)
        self.assertEqual(hello['body']['project_name'], 'myapp')
        self.assertIn('application/json', hello['headers']['Content-Type'])

    def test_redirect_responses_are_followed(self):
        request = {'path': '/mushrooms/'}  # trailing slash
        body = {'requests': [request]}
        resp = self.app.post_json('/batch', body, headers=self.headers)
        collection = resp.json['responses'][0]
        self.assertEqual(collection['status'], 200)
        self.assertEqual(collection['path'], '/v0/mushrooms')
        self.assertEqual(collection['body'], {'data': []})

    def test_body_is_transmitted_during_redirect(self):
        request = {
            'method': 'PUT',
            'path': '/mushrooms/{}/'.format(str(uuid.uuid4())),
            'body': {'data': {'name': 'Trompette de la mort'}}
        }
        body = {'requests': [request]}
        resp = self.app.post_json('/batch', body, headers=self.headers)
        response = resp.json['responses'][0]
        self.assertEqual(response['status'], 201)
        record = response['body']['data']
        self.assertEqual(record['name'], 'Trompette de la mort')

    def test_400_error_message_is_forwarded(self):
        headers = {**self.headers, 'If-Match': '"*"'}
        request = {
            'method': 'PUT',
            'path': '/mushrooms/{}'.format(str(uuid.uuid4())),
            'body': {'data': {'name': 'Trompette de la mort'}},
            'headers': headers
        }
        body = {'requests': [request, request]}
        resp = self.app.post_json('/batch', body, status=200)
        self.assertEqual(resp.json['responses'][1]['status'], 400)
        msg = 'If-Match in header: The value should be integer between double quotes.'
        self.assertEqual(resp.json['responses'][1]['body']['message'], msg)

    def test_412_errors_are_forwarded(self):
        headers = {**self.headers, 'If-None-Match': '*'}
        request = {
            'method': 'PUT',
            'path': '/mushrooms/{}'.format(str(uuid.uuid4())),
            'body': {'data': {'name': 'Trompette de la mort'}},
            'headers': headers
        }
        body = {'requests': [request, request]}
        resp = self.app.post_json('/batch', body, status=200)
        self.assertEqual(resp.json['responses'][0]['status'], 201)
        self.assertEqual(resp.json['responses'][1]['status'], 412)


class BatchSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = BatchPayloadSchema()

    def assertInvalid(self, payload):
        self.assertRaises(colander.Invalid, self.schema.deserialize, payload)

    def test_requests_is_mandatory(self):
        self.assertInvalid({})

    def test_raise_invalid_on_unknown_attributes(self):
        self.assertInvalid({'requests': [], 'unknown': 42})

    def test_list_of_requests_can_be_empty(self):
        self.schema.deserialize({'requests': []})

    def test_list_of_requests_must_be_a_list(self):
        self.assertInvalid({'requests': {}})

    def test_list_of_requests_must_be_dicts(self):
        request = 42
        self.assertInvalid({'defaults': {'path': '/'}, 'requests': [request]})

    def test_request_path_must_start_with_slash(self):
        request = {'path': 'http://localhost'}
        self.assertInvalid({'requests': [request]})

    def test_request_path_is_mandatory(self):
        request = {'method': 'HEAD'}
        self.assertInvalid({'requests': [request]})

    def test_request_method_must_be_known_uppercase_word(self):
        request = {'path': '/', 'method': 'get'}
        self.assertInvalid({'requests': [request]})

    def test_raise_invalid_on_request_unknown_attributes(self):
        request = {'path': '/', 'method': 'GET', 'foo': 42}
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

    def test_raise_invalid_on_default_unknown_attributes(self):
        request = {'path': '/'}
        defaults = {'foo': 'bar'}
        self.assertInvalid({'requests': [request], 'defaults': defaults})

    def test_defaults_can_be_specified_empty(self):
        request = {'path': '/'}
        defaults = {}
        batch_payload = {'requests': [request], 'defaults': defaults}
        self.schema.deserialize(batch_payload)

    def test_defaults_path_is_applied_to_requests(self):
        request = {'method': 'GET'}
        defaults = {'path': '/'}
        batch_payload = {'requests': [request], 'defaults': defaults}
        result = self.schema.deserialize(batch_payload)
        self.assertEqual(result['requests'][0]['path'], '/')

    def test_defaults_body_is_applied_to_requests(self):
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

    def test_defaults_values_for_path_must_start_with_slash(self):
        request = {}
        defaults = {'path': 'http://localhost'}
        batch_payload = {'requests': [request], 'defaults': defaults}
        self.assertInvalid(batch_payload)


class BatchServiceTest(unittest.TestCase):
    def setUp(self):
        self.method, self.view, self.options = batch_service.definitions[0]
        self.request = DummyRequest()

    def post(self, validated):
        self.request.validated = {'body': validated}
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
        self.assertEqual(result['responses'][0]['path'], '/v0/')

    def test_subrequests_have_parent_attribute(self):
        self.request.path = '/batch'
        self.post({'requests': [{'path': '/'}]})
        subrequest, = self.request.invoke_subrequest.call_args[0]
        self.assertEqual(subrequest.parent.path, '/batch')

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
        wanted = {"json": "payload"}
        subrequest, = self.request.invoke_subrequest.call_args[0]
        self.assertEqual(subrequest.body.decode('utf8'),
                         json.dumps(wanted))

    def test_subrequests_body_have_json_content_type(self):
        self.request.headers['Content-Type'] = 'text/xml'
        request = {'path': '/', 'body': {'json': 'payload'}}
        self.post({'requests': [request]})
        subrequest, = self.request.invoke_subrequest.call_args[0]
        self.assertIn('application/json',
                      subrequest.headers['Content-Type'])

    def test_subrequests_body_have_utf8_charset(self):
        request = {'path': '/', 'body': {'json': "😂"}}
        self.post({'requests': [request]})
        subrequest, = self.request.invoke_subrequest.call_args[0]
        self.assertIn('charset=utf-8', subrequest.headers['Content-Type'])
        wanted = {"json": "😂"}
        self.assertEqual(subrequest.body.decode('utf8'),
                         json.dumps(wanted))

    def test_subrequests_paths_are_url_encoded(self):
        request = {'path': '/test?param=©'}
        self.post({'requests': [request]})
        subrequest, = self.request.invoke_subrequest.call_args[0]
        self.assertEqual(subrequest.path, '/v0/test')
        self.assertEqual(subrequest.GET['param'], '©')

    def test_subrequests_responses_paths_are_url_decoded(self):
        request = {'path': '/test?param=©'}
        resp = self.post({'requests': [request]})
        path = resp['responses'][0]['path']
        self.assertEqual(path, '/v0/test')

    def test_response_body_is_string_if_remote_response_is_not_json(self):
        response = Response(body='Internal Error')
        self.request.invoke_subrequest.return_value = response
        request = {'path': '/test'}
        resp = self.post({'requests': [request]})
        body = resp['responses'][0]['body'].decode('utf-8')
        self.assertEqual(body, 'Internal Error')

    def test_number_of_requests_is_not_limited_when_settings_set_to_none(self):
        self.request.registry.settings['batch_max_requests'] = None
        requests = {}
        for i in range(30):
            requests.setdefault('requests', []).append({'path': '/'})
            self.post(requests)

    def test_number_of_requests_is_limited_to_25_by_default(self):
        requests = {}
        for i in range(26):
            requests.setdefault('requests', []).append({'path': '/'})
        result = self.post(requests)

        self.assertEqual(self.request.errors[0]['description'],
                         'Number of requests is limited to 25')
        self.assertIsNone(result)  # rest of view not executed

    def test_return_400_if_number_of_requests_is_greater_than_settings(self):
        self.request.registry.settings['batch_max_requests'] = 22

        requests = {}
        for i in range(23):
            requests.setdefault('requests', []).append({'path': '/'})
        result = self.post(requests)

        self.assertEqual(self.request.errors[0]['description'],
                         'Number of requests is limited to 22')
        self.assertIsNone(result)  # rest of view not executed
