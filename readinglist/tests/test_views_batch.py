import colander

from readinglist.views.batch import BatchRequestSchema, batch as batch_service
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


class BatchSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = BatchRequestSchema()

    def assertInvalid(self, payload):
        self.assertRaises(colander.Invalid, self.schema.deserialize, payload)

    def test_requests_is_mandatory(self):
        self.assertRaises({})

    def test_unknown_attributes_are_dropped(self):
        deserialized = self.schema.deserialize({'requests': [], 'unknown': 42})
        self.assertNotIn('unknown', deserialized)

    def test_list_of_requests_can_be_empty(self):
        self.schema.deserialize({'requests': []})

    def test_list_of_requests_must_be_a_list(self):
        self.assertRaises({'requests': {}})


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
        requests = [{}]
        result = self.post({'requests': requests})
        self.assertEqual(len(result['responses']), len(requests))
