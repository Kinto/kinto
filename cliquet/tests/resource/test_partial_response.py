from pyramid import httpexceptions

from cliquet.resource import ShareableResource
from cliquet.tests.resource import BaseTest


class PartialResponseBase(BaseTest):
    def setUp(self):
        super(PartialResponseBase, self).setUp()
        self.resource._get_known_fields = lambda: ['field', 'other', 'orig']
        self.record = self.model.create_record(
            {
                'field': 'value',
                'other': 'val',
                'orig': {
                    'foo': 'food',
                    'bar': 'baz',
                    'nested': {
                        'size': 12546,
                        'hash': '0x1254',
                    }
                }
            })
        self.resource.record_id = self.record['id']
        self.resource.request = self.get_request()


class BasicTest(PartialResponseBase):

    def test_fields_parameter_do_projection_on_get(self):
        self.resource.request.GET['_fields'] = 'field'
        record = self.resource.get()
        self.assertIn('field', record['data'])
        self.assertNotIn('other', record['data'])

    def test_fields_parameter_do_projection_on_get_all(self):
        self.resource.request.GET['_fields'] = 'field'
        record = self.resource.collection_get()['data'][0]
        self.assertIn('field', record)
        self.assertNotIn('other', record)

    def test_fail_if_fields_parameter_is_invalid(self):
        self.resource.request.GET['_fields'] = 'invalid_field'
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.get)
        self.assertRaises(
            httpexceptions.HTTPBadRequest, self.resource.collection_get)

    def test_can_have_multiple_fields(self):
        self.resource.request.GET['_fields'] = 'field,other'
        record = self.resource.get()
        self.assertIn('field', record['data'])
        self.assertIn('other', record['data'])

    def test_id_and_last_modified_are_not_filtered(self):
        self.resource.request.GET['_fields'] = 'field'
        record = self.resource.get()
        self.assertIn('id', record['data'])
        self.assertIn('last_modified', record['data'])

    def test_nested_parameter_can_be_filtered(self):
        self.resource.request.GET['_fields'] = 'orig.foo'
        record = self.resource.get()
        self.assertIn('orig', record['data'])
        self.assertIn('foo', record['data']['orig'])
        self.assertNotIn('other', record['data'])
        self.assertNotIn('bar', record['data']['orig'])
        self.assertNotIn('nested', record['data']['orig'])

    def test_nested_parameter_can_be_filtered_on_multiple_levels(self):
        self.resource.request.GET['_fields'] = 'orig.nested.size'
        record = self.resource.get()
        self.assertIn('nested', record['data']['orig'])
        self.assertIn('size', record['data']['orig']['nested'])
        self.assertNotIn('hash', record['data']['orig']['nested'])


class PermissionTest(PartialResponseBase):
    resource_class = ShareableResource

    def test_permissions_are_not_displayed(self):
        self.resource.request.GET['_fields'] = 'field'
        result = self.resource.get()
        self.assertNotIn('permissions', result)
