from pyramid import httpexceptions

from readinglist.errors import ERRORS
from readinglist.tests.resource import BaseTest


class FilteringTest(BaseTest):
    def setUp(self):
        super(FilteringTest, self).setUp()
        self.resource.known_fields = ['status', 'favorite', 'title']
        for i in range(6):
            record = {
                'title': 'MoFo',
                'status': i % 3,
                'favorite': (i % 4 == 0)
            }
            self.db.create(self.resource, 'bob', record)

    def test_filter_works_with_empty_list(self):
        self.resource.db_kwargs['user_id'] = 'alice'
        self.resource.request.GET = {'status': '1'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['items']), 0)

    def test_number_of_records_matches_filter(self):
        self.resource.request.GET = {'status': '1'}
        self.resource.collection_get()
        headers = self.last_response.headers
        self.assertEqual(int(headers['Total-Records']), 2)

    def test_single_basic_filter_by_attribute(self):
        self.resource.request.GET = {'status': '1'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['items']), 2)

    def test_filter_on_unknown_attribute_raises_error(self):
        self.resource.request.GET = {'foo': '1'}
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_filter_errors_are_json_formatted(self):
        self.resource.request.GET = {'foo': '1'}
        try:
            self.resource.collection_get()
        except httpexceptions.HTTPBadRequest as e:
            error = e
        self.assertEqual(error.json, {
            'errno': ERRORS.INVALID_PARAMETERS,
            'message': "querystring: Unknown filter field 'foo'",
            'code': 400,
            'error': 'Invalid parameters'})

    def test_regexp_is_strict_for_min_and_max(self):
        self.resource.request.GET = {'madmax_status': '1'}
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_double_basic_filter_by_attribute(self):
        self.resource.request.GET = {'status': '1', 'favorite': 'true'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['items']), 1)

    def test_string_filters_naively_by_value(self):
        self.resource.request.GET = {'title': 'MoF'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['items']), 0)
        self.resource.request.GET = {'title': 'MoFo'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['items']), 6)

    def test_filter_considers_string_if_syntaxically_invalid(self):
        self.resource.request.GET = {'status': '1.2.3'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['items']), 0)

    def test_filter_does_not_fail_with_complex_type_syntax(self):
        self.resource.request.GET = {'status': '(1,2,3)'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['items']), 0)

    def test_different_value(self):
        self.resource.request.GET = {'not_status': '2'}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['items']]
        self.assertTrue(all([value != 2 for value in values]))

    def test_minimal_value(self):
        self.resource.request.GET = {'min_status': '2'}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['items']]
        self.assertTrue(all([value >= 2 for value in values]))

    def test_gt_value(self):
        self.resource.request.GET = {'gt_status': '2'}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['items']]
        self.assertTrue(all([value > 2 for value in values]))

    def test_maximal_value(self):
        self.resource.request.GET = {'max_status': '2'}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['items']]
        self.assertTrue(all([value <= 2 for value in values]))

    def test_lt_value(self):
        self.resource.request.GET = {'lt_status': '2'}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['items']]
        self.assertTrue(all([value < 2 for value in values]))
