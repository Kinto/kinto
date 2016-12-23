from bravado_core.validate import validate_object
from bravado_core.swagger20_validator import ValidationError

from .support import SwaggerTest


class SwaggerDefinitionsTest(SwaggerTest):

    def setUp(self):
        super(SwaggerDefinitionsTest, self).setUp()

    def test_definitions_validate_id(self):
        schema = self.spec.deref(self.spec_dict['definitions']['Bucket'])
        obj = {'data': {'id': False}}
        self.assertRaises(ValidationError,
                          validate_object, self.spec, schema, obj)

    def test_definitions_validate_last_modified(self):
        schema = self.spec.deref(self.spec_dict['definitions']['Bucket'])
        obj = {'data': {'last_modified': 0.123}}
        self.assertRaises(ValidationError,
                          validate_object, self.spec, schema, obj)

    def test_definitions_validate_permissions(self):
        schema = self.spec.deref(self.spec_dict['definitions']['Bucket'])
        obj = {'permissions': []}
        self.assertRaises(ValidationError,
                          validate_object, self.spec, schema, obj)
        obj = {'permissions': {'read': {}}}
        self.assertRaises(ValidationError,
                          validate_object, self.spec, schema, obj)
        obj = {'permissions': {'read': ['bob', False]}}
        self.assertRaises(ValidationError,
                          validate_object, self.spec, schema, obj)

    def test_bucket_definition(self):
        schema = self.spec.deref(self.spec_dict['definitions']['Bucket'])
        validate_object(self.spec, schema, self.bucket)

    def test_group_definition(self):
        schema = self.spec.deref(self.spec_dict['definitions']['Group'])
        validate_object(self.spec, schema, self.group)

    def test_collection_definition(self):
        schema = self.spec.deref(self.spec_dict['definitions']['Collection'])
        validate_object(self.spec, schema, self.collection)

    def test_record_definition(self):
        schema = self.spec.deref(self.spec_dict['definitions']['Record'])
        validate_object(self.spec, schema, self.record)

    def test_list_definition(self):
        buckets = self.app.get('/buckets', headers=self.headers).json
        schema = self.spec.deref(self.spec_dict['definitions']['List'])
        validate_object(self.spec, schema, buckets)

    def test_error_definition(self):
        buckets = self.app.get('/buckets', status=401).json
        schema = self.spec.deref(self.spec_dict['definitions']['Error'])
        validate_object(self.spec, schema, buckets)
