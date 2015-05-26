from .support import BaseWebTest, unittest


SCHEMA_URL = '/buckets/default/collections/articles/schema'
RECORDS_URL = '/buckets/default/collections/articles/records'


SCHEMA = {
    "title": "Blog post schema",
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["title"]
}

VALID_RECORD = {'title': 'About us', 'body': '<h1>About</h1>'}


class MissingSchemaTest(BaseWebTest, unittest.TestCase):
    def test_returns_404_if_no_schema_defined(self):
        self.app.get(SCHEMA_URL,
                     headers=self.headers,
                     status=404)

    def test_accepts_any_kind_of_record(self):
        record = {'title': 'Troll'}
        self.app.post_json(RECORDS_URL,
                           {'data': record},
                           headers=self.headers,
                           status=201)
        record = {'author': {'age': 32, 'status': 'captain'}}
        self.app.post_json(RECORDS_URL,
                           {'data': record},
                           headers=self.headers,
                           status=201)


class MethodsTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(MethodsTest, self).setUp()
        resp = self.app.put_json(SCHEMA_URL,
                                 {'data': SCHEMA},
                                 headers=self.headers)
        self.schema = resp.json['data']

    def test_get_retrieves_current_schema(self):
        resp = self.app.get(SCHEMA_URL, headers=self.headers)
        response = resp.json['data']
        response.pop('id')
        response.pop('last_modified')
        self.assertEqual(response, SCHEMA)

    def test_put_replaces_current_schema(self):
        newschema = SCHEMA.copy()
        newschema['properties']['category'] = {"type": "string"}
        resp = self.app.put_json(SCHEMA_URL,
                                 {'data': newschema},
                                 headers=self.headers)
        resp = self.app.get(SCHEMA_URL, headers=self.headers)
        response = resp.json['data']
        response.pop('id')
        response.pop('last_modified')
        self.assertEqual(response, newschema)

    def test_post_is_not_allowed(self):
        self.app.post(SCHEMA_URL, status=405, headers=self.headers)

    def test_patch_is_not_allowed(self):
        self.app.patch(SCHEMA_URL, status=405, headers=self.headers)

    def test_delete_removes_schema(self):
        self.app.delete(SCHEMA_URL, headers=self.headers)
        self.app.get(SCHEMA_URL,
                     headers=self.headers,
                     status=404)


class InvalidSchemaTest(BaseWebTest, unittest.TestCase):
    def test_empty_body_is_invalid(self):
        resp = self.app.put_json(SCHEMA_URL,
                                 headers=self.headers,
                                 status=400)
        self.assertIn(resp.json['message'],
                      ('No JSON object could be decoded',  # PY2
                       'Expecting value: line 1 column 1 (char 0)'))  # PY3

    def test_empty_schema_is_invalid(self):
        resp = self.app.put_json(SCHEMA_URL,
                                 {'data': {}},
                                 headers=self.headers,
                                 status=400)
        self.assertEqual(resp.json['message'],
                         'Schema is empty')

    def test_schema_should_be_json_schema(self):
        newschema = SCHEMA.copy()
        newschema['type'] = 'Washmachine'
        resp = self.app.put_json(SCHEMA_URL,
                                 {'data': newschema},
                                 headers=self.headers,
                                 status=400)
        error_msg = "'Washmachine' is not valid under any of the given schemas"
        self.assertIn(error_msg, resp.json['message'])


class RecordsValidationTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(RecordsValidationTest, self).setUp()
        resp = self.app.put_json(SCHEMA_URL,
                                 {'data': SCHEMA},
                                 headers=self.headers)
        self.schema = resp.json['data']

    def test_records_are_valid_if_match_schema(self):
        self.app.post_json(RECORDS_URL,
                           {'data': VALID_RECORD},
                           headers=self.headers,
                           status=201)

    def test_records_are_invalid_if_do_not_match_schema(self):
        self.app.post_json(RECORDS_URL,
                           {'data': {'body': '<h1>Without title</h1>'}},
                           headers=self.headers,
                           status=400)

    def test_records_are_validated_on_patch(self):
        resp = self.app.post_json(RECORDS_URL,
                                  {'data': VALID_RECORD},
                                  headers=self.headers,
                                  status=201)
        record_id = resp.json['data']['id']
        self.app.patch_json('%s/%s' % (RECORDS_URL, record_id),
                            {'data': {'title': 3.14}},
                            headers=self.headers,
                            status=400)

    def test_records_are_validated_on_put(self):
        resp = self.app.post_json(RECORDS_URL,
                                  {'data': VALID_RECORD},
                                  headers=self.headers,
                                  status=201)
        record_id = resp.json['data']['id']
        self.app.put_json('%s/%s' % (RECORDS_URL, record_id),
                          {'data': {'body': '<h1>Without title</h1>'}},
                          headers=self.headers,
                          status=400)

    def test_validation_error_response_provides_details(self):
        resp = self.app.post_json(RECORDS_URL,
                                  {'data': {'body': '<h1>Without title</h1>'}},
                                  headers=self.headers,
                                  status=400)
        self.assertIn("'title' is a required property", resp.json['message'])
        self.assertEqual(resp.json['details'][0]['name'], 'title')

    def test_records_of_other_bucket_are_not_impacted(self):
        self.app.put_json('/buckets/blog', headers=self.headers)
        self.app.put_json('/buckets/blog/collections/articles',
                          headers=self.headers)
        self.app.post_json('/buckets/blog/collections/articles/records',
                           {'data': {'body': '<h1>Without title</h1>'}},
                           headers=self.headers)

    def test_records_receive_the_schema_revision_as_attribute(self):
        resp = self.app.post_json(RECORDS_URL,
                                  {'data': VALID_RECORD},
                                  headers=self.headers,
                                  status=201)
        self.assertEqual(resp.json['data']['schema'],
                         self.schema['last_modified'])

    def test_records_can_filtered_by_schema_version(self):
        self.app.post_json(RECORDS_URL,
                           {'data': VALID_RECORD},
                           headers=self.headers)
        resp = self.app.put_json(SCHEMA_URL,
                                 {'data': SCHEMA},
                                 headers=self.headers)
        schema_version = resp.json['data']['last_modified']
        self.app.post_json(RECORDS_URL,
                           {'data': VALID_RECORD},
                           headers=self.headers)

        resp = self.app.get(RECORDS_URL + '?min_schema=%s' % schema_version,
                            headers=self.headers)
        self.assertEqual(len(resp.json['data']), 1)
