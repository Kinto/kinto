from pyramid import httpexceptions

from cliquet.errors import ERRORS
from cliquet.tests.resource import BaseTest


class FilteringTest(BaseTest):
    def setUp(self):
        super(FilteringTest, self).setUp()
        self.patch_known_field.start()
        for i in range(6):
            record = {
                'title': 'MoFo',
                'status': i % 3,
                'favorite': (i % 4 == 0)
            }
            self.model.create_record(record)

    def test_list_can_be_filtered_on_deleted_with_since(self):
        since = self.model.timestamp()
        r = self.model.create_record({})
        self.model.delete_record(r)
        self.resource.request.GET = {'_since': '%s' % since, 'deleted': 'true'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 1)
        self.assertTrue(result['data'][0]['deleted'])

    def test_filter_on_id_is_supported(self):
        self.patch_known_field.stop()
        r = self.model.create_record({})
        self.resource.request.GET = {'id': '%s' % r['id']}
        result = self.resource.collection_get()
        self.assertEqual(result['data'][0], r)

    def test_list_cannot_be_filtered_on_deleted_without_since(self):
        r = self.model.create_record({})
        self.model.delete_record(r)
        self.resource.request.GET = {'deleted': 'true'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_filter_works_with_empty_list(self):
        self.resource.model.parent_id = 'alice'
        self.resource.request.GET = {'status': '1'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_number_of_records_matches_filter(self):
        self.resource.request.GET = {'status': '1'}
        self.resource.collection_get()
        headers = self.last_response.headers
        self.assertEqual(int(headers['Total-Records']), 2)

    def test_single_basic_filter_by_attribute(self):
        self.resource.request.GET = {'status': '1'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 2)

    def test_filter_on_unknown_attribute_raises_error(self):
        self.patch_known_field.stop()
        self.resource.request.GET = {'foo': '1'}
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_filter_errors_are_json_formatted(self):
        self.patch_known_field.stop()
        self.resource.request.GET = {'foo': '1'}
        try:
            self.resource.collection_get()
        except httpexceptions.HTTPBadRequest as e:
            error = e
        self.assertEqual(error.json, {
            'errno': ERRORS.INVALID_PARAMETERS.value,
            'message': "Unknown filter field 'foo'",
            'code': 400,
            'error': 'Invalid parameters',
            'details': [{'description': "Unknown filter field 'foo'",
                         'location': 'querystring',
                         'name': 'foo'}]})

    def test_regexp_is_strict_for_min_and_max(self):
        self.patch_known_field.stop()
        self.resource.request.GET = {'madmax_status': '1'}
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_double_basic_filter_by_attribute(self):
        self.resource.request.GET = {'status': '1', 'favorite': 'true'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 1)

    def test_string_filters_naively_by_value(self):
        self.resource.request.GET = {'title': 'MoF'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)
        self.resource.request.GET = {'title': 'MoFo'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 6)

    def test_filter_considers_string_if_syntaxically_invalid(self):
        self.resource.request.GET = {'status': '1.2.3'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_filter_does_not_fail_with_complex_type_syntax(self):
        self.resource.request.GET = {'status': '(1,2,3)'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_different_value(self):
        self.resource.request.GET = {'not_status': '2'}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertTrue(all([value != 2 for value in values]))

    def test_minimal_value(self):
        self.resource.request.GET = {'min_status': '2'}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertTrue(all([value >= 2 for value in values]))

    def test_gt_value(self):
        self.resource.request.GET = {'gt_status': '2'}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertTrue(all([value > 2 for value in values]))

    def test_maximal_value(self):
        self.resource.request.GET = {'max_status': '2'}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertTrue(all([value <= 2 for value in values]))

    def test_lt_value(self):
        self.resource.request.GET = {'lt_status': '2'}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertTrue(all([value < 2 for value in values]))

    def test_in_values(self):
        self.resource.request.GET = {'in_status': '0,1'}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertEqual(sorted(values), [0, 0, 1, 1])

    def test_exclude_values(self):
        self.resource.request.GET = {'exclude_status': '0'}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertEqual(sorted(values), [1, 1, 2, 2])

    def test_include_returns_400_if_value_has_wrong_type(self):
        self.resource.request.GET = {'in_id': '0,1'}
        with self.assertRaises(httpexceptions.HTTPBadRequest) as cm:
            self.resource.collection_get()
        self.assertIn('in_id', cm.exception.json['message'])

        self.resource.request.GET = {'in_last_modified': 'a,b'}
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_exclude_returns_400_if_value_has_wrong_type(self):
        self.resource.request.GET = {'exclude_id': '0,1'}
        with self.assertRaises(httpexceptions.HTTPBadRequest) as cm:
            self.resource.collection_get()
        self.assertIn('exclude_id', cm.exception.json['message'])

        self.resource.request.GET = {'exclude_last_modified': 'a,b'}
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)
