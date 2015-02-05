import json

import colander
import mock

from readinglist.views.batch import BatchPayloadSchema, batch as batch_service
from readinglist.tests.support import BaseWebTest, unittest, DummyRequest


class BatchViewTest(BaseWebTest, unittest.TestCase):

    def test_requires_authentication(self):
        self.app.post('/batch', {}, status=401)

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

    def test_can_be_recursive(self):
        requests = json.dumps({'requests': [{'path': '/v0/'}]})

        request = {'method': 'POST', 'path': '/v0/batch', 'body': requests}
        body = {'requests': [request]}
        resp = self.app.post_json('/batch', body, headers=self.headers)

        hello = resp.json['responses'][0]['body']['responses'][0]
        self.assertEqual(hello['body']['hello'], 'readinglist')

    def test_path_not_url_encoded(self):
        pass


class BatchSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = BatchPayloadSchema()

    def assertInvalid(self, payload):
        self.assertRaises(colander.Invalid, self.schema.deserialize, payload)

    def test_requests_is_mandatory(self):
        self.assertInvalid({})

    def test_unknown_attributes_are_dropped(self):
        deserialized = self.schema.deserialize({'requests': [], 'unknown': 42})
        self.assertNotIn('unknown', deserialized)

    def test_list_of_requests_can_be_empty(self):
        self.schema.deserialize({'requests': []})

    def test_list_of_requests_must_be_a_list(self):
        self.assertInvalid({'requests': {}})

    def test_request_path_must_start_with_slash(self):
        request = {'path': 'http://localhost'}
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

    def test_body_is_an_arbitrary_string(self):
        payload = '{"json": "payload"}'
        request = {'path': '/', 'body': payload}
        deserialized = self.schema.deserialize({'requests': [request]})
        self.assertEqual(deserialized['requests'][0]['body'], payload)

    def test_body_is_dropped_if_empty_string(self):
        payload = ''
        request = {'path': '/', 'body': payload}
        deserialized = self.schema.deserialize({'requests': [request]})
        self.assertNotIn('body', deserialized['requests'][0])


class BatchServiceTest(unittest.TestCase):
    def setUp(self):
        self.method, self.view, self.options = batch_service.definitions[0]

    def post(self, validated):
        request = DummyRequest()
        request.validated = validated
        return self.view(request)

    def test_returns_empty_list_of_responses_if_requests_empty(self):
        result = self.post({'requests': []})
        self.assertEqual(result['responses'], [])

    def test_returns_one_response_per_request(self):
        requests = [{'path': '/'}]
        result = self.post({'requests': requests})
        self.assertEqual(len(result['responses']), len(requests))
