from .support import BaseWebTest, unittest


BUCKET_URL = '/buckets/blog'
COLLECTION_URL = '/buckets/blog/collections/articles'
RECORDS_URL = '/buckets/blog/collections/articles/records'


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


class DeactivatedSchemaTest(BaseWebTest, unittest.TestCase):
    def test_schema_should_be_json_schema(self):
        newschema = SCHEMA.copy()
        newschema['type'] = 'Washmachine'
        self.app.put_json(BUCKET_URL, headers=self.headers)
        self.app.put(COLLECTION_URL, headers=self.headers)
        resp = self.app.put_json(COLLECTION_URL,
                                 {'data': {'schema': newschema}},
                                 headers=self.headers,
                                 status=400)
        error_msg = "'Washmachine' is not valid under any of the given schemas"
        self.assertIn(error_msg, resp.json['message'])

    def test_records_are_not_invalid_if_do_not_match_schema(self):
        self.app.put_json(BUCKET_URL, headers=self.headers)
        self.app.put(COLLECTION_URL, headers=self.headers)
        resp = self.app.put_json(COLLECTION_URL,
                                 {'data': {'schema': SCHEMA}},
                                 headers=self.headers)
        self.collection = resp.json['data']

        self.app.post_json(RECORDS_URL,
                           {'data': {'body': '<h1>Without title</h1>'}},
                           headers=self.headers,
                           status=201)


class BaseWebTestWithSchema(BaseWebTest):
    def get_app_settings(self, additional_settings=None):
        settings = super(BaseWebTestWithSchema, self).get_app_settings(
            additional_settings)
        settings['experimental_collection_schema_validation'] = 'True'
        return settings

    def setUp(self):
        super(BaseWebTestWithSchema, self).setUp()
        self.app.put_json(BUCKET_URL, headers=self.headers)
        self.app.put_json(COLLECTION_URL, headers=self.headers)


class MissingSchemaTest(BaseWebTestWithSchema, unittest.TestCase):
    def test_attribute_is_none_if_no_schema_defined(self):
        resp = self.app.get(COLLECTION_URL,
                            headers=self.headers)
        self.assertIsNone(resp.json['data'].get(''))

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


class InvalidSchemaTest(BaseWebTestWithSchema, unittest.TestCase):
    def test_schema_should_be_json_schema(self):
        newschema = SCHEMA.copy()
        newschema['type'] = 'Washmachine'
        resp = self.app.put_json(COLLECTION_URL,
                                 {'data': {'schema': newschema}},
                                 headers=self.headers,
                                 status=400)
        error_msg = "'Washmachine' is not valid under any of the given schemas"
        self.assertIn(error_msg, resp.json['message'])


class RecordsValidationTest(BaseWebTestWithSchema, unittest.TestCase):
    def setUp(self):
        super(RecordsValidationTest, self).setUp()
        resp = self.app.put_json(COLLECTION_URL,
                                 {'data': {'schema': SCHEMA}},
                                 headers=self.headers)
        self.collection = resp.json['data']

    def test_empty_record_can_be_validated(self):
        self.app.post_json(RECORDS_URL,
                           {'data': {}},
                           headers=self.headers,
                           status=400)

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

    def test_records_receive_the_schema_as_attribute(self):
        resp = self.app.post_json(RECORDS_URL,
                                  {'data': VALID_RECORD},
                                  headers=self.headers,
                                  status=201)
        self.assertEqual(resp.json['data']['schema'],
                         self.collection['last_modified'])

    def test_records_can_filtered_by_schema_version(self):
        self.app.post_json(RECORDS_URL,
                           {'data': VALID_RECORD},
                           headers=self.headers)
        resp = self.app.put_json(COLLECTION_URL,
                                 {'data': {'schema': SCHEMA}},
                                 headers=self.headers)
        schema_version = resp.json['data']['last_modified']
        self.app.post_json(RECORDS_URL,
                           {'data': VALID_RECORD},
                           headers=self.headers)

        resp = self.app.get(RECORDS_URL + '?min_schema=%s' % schema_version,
                            headers=self.headers)
        self.assertEqual(len(resp.json['data']), 1)


class ExtraPropertiesValidationTest(BaseWebTestWithSchema, unittest.TestCase):
    def setUp(self):
        super(ExtraPropertiesValidationTest, self).setUp()
        schema = SCHEMA.copy()
        schema['additionalProperties'] = False
        resp = self.app.put_json(COLLECTION_URL,
                                 {'data': {'schema': schema}},
                                 headers=self.headers)
        self.collection = resp.json['data']

    def test_record_can_be_validated_on_post(self):
        self.app.post_json(RECORDS_URL,
                           {'data': VALID_RECORD},
                           headers=self.headers)

    def test_record_can_be_validated_on_put(self):
        record_id = '5443d83f-852a-481a-8e9d-5aa804b05b08'
        self.app.put_json('%s/%s' % (RECORDS_URL, record_id),
                          {'data': VALID_RECORD},
                          headers=self.headers)

    def test_records_are_validated_on_patch(self):
        record_id = '5443d83f-852a-481a-8e9d-5aa804b05b08'
        record_url = '%s/%s' % (RECORDS_URL, record_id)
        resp = self.app.put_json(record_url,
                                 {'data': VALID_RECORD},
                                 headers=self.headers)
        record = resp.json['data']
        assert 'schema' in record
        record['title'] = 'hey'
        self.app.patch_json(record_url,
                            {'data': record},
                            headers=self.headers)

    def test_additional_properties_are_rejected(self):
        record_id = '5443d83f-852a-481a-8e9d-5aa804b05b08'
        record = VALID_RECORD.copy()
        record['extra'] = 'blah!'
        resp = self.app.put_json('%s/%s' % (RECORDS_URL, record_id),
                                 {'data': record},
                                 headers=self.headers,
                                 status=400)
        assert "'extra' was unexpected)" in resp.json['message']
