from pyramid import httpexceptions

from kinto.core.errors import ERRORS
from . import BaseTest


class FilteringTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.validated = self.resource.request.validated
        self.patch_known_field.start()
        records = [
            {'title': 'MoFo', 'status': 0, 'favorite': True},
            {'title': 'MoFo', 'status': 1, 'favorite': False},
            {'title': 'MoFo', 'status': 2, 'favorite': False, 'sometimes': 'available'},
            {'title': 'MoFo', 'status': 0, 'favorite': False, 'sometimes': None},
            {'title': 'MoFo', 'status': 1, 'favorite': True},
            {'title': 'MoFo', 'status': 2, 'favorite': False},
            {'title': 'Foo', 'status': 3, 'favorite': False},
            {'title': 'Bar', 'status': 3, 'favorite': False, 'sometimes': 'present'},
        ]
        for r in records:
            self.model.create_record(r)

    def test_list_can_be_filtered_on_deleted_with_since(self):
        since = self.model.timestamp()
        r = self.model.create_record({})
        self.model.delete_record(r)
        self.validated['querystring'] = {'_since': since, 'deleted': True}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 1)
        self.assertTrue(result['data'][0]['deleted'])

    def test_filter_on_id_is_supported(self):
        self.patch_known_field.stop()
        r = self.model.create_record({})
        self.validated['querystring'] = {'id': '{}'.format(r['id'])}
        result = self.resource.collection_get()
        self.assertEqual(result['data'][0], r)

    def test_list_cannot_be_filtered_on_deleted_without_since(self):
        r = self.model.create_record({})
        self.model.delete_record(r)
        self.validated['querystring'] = {'deleted': True}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_filter_works_with_empty_list(self):
        self.resource.model.parent_id = 'alice'
        self.validated['querystring'] = {'status': 1}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_number_of_records_matches_filter(self):
        self.validated['querystring'] = {'status': 1}
        self.resource.collection_get()
        headers = self.last_response.headers
        self.assertEqual(int(headers['Total-Records']), 2)

    def test_single_basic_filter_by_attribute(self):
        self.validated['querystring'] = {'status': 1}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 2)

    def test_filter_on_unknown_attribute_raises_error(self):
        self.patch_known_field.stop()
        self.validated['querystring'] = {'foo': 1}
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_filter_errors_are_json_formatted(self):
        self.patch_known_field.stop()
        self.validated['querystring'] = {'foo': 1}
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
        self.validated['querystring'] = {'madmax_status': 1}
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_double_basic_filter_by_attribute(self):
        self.validated['querystring'] = {'status': 1, 'favorite': True}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 1)

    def test_string_filters_naively_by_value(self):
        self.validated['querystring'] = {'title': 'MoF'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)
        self.validated['querystring'] = {'title': 'MoFo'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 6)

    def test_string_filters_searching_by_value_not_matching(self):
        self.validated['querystring'] = {'like_title': 'MoFoo'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_string_filters_searching_by_value_matching_many(self):
        self.validated['querystring'] = {'like_title': 'Fo'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 7)

    def test_string_filters_searching_by_value_matching_one(self):
        self.validated['querystring'] = {'like_title': 'Bar'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 1)

    def test_string_filters_searching_by_value_matching_vary_case(self):
        self.validated['querystring'] = {'like_title': 'FoO'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 1)

    def test_filter_considers_string_if_syntaxically_invalid(self):
        self.validated['querystring'] = {'status': '1.2.3'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_filter_does_not_fail_with_complex_type_syntax(self):
        self.validated['querystring'] = {'status': '(1,2,3)'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_different_value(self):
        self.validated['querystring'] = {'not_status': 2}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertTrue(all([value != 2 for value in values]))

    def test_minimal_value(self):
        self.validated['querystring'] = {'min_status': 2}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertTrue(all([value >= 2 for value in values]))

    def test_gt_value(self):
        self.validated['querystring'] = {'gt_status': 2}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertTrue(all([value > 2 for value in values]))

    def test_maximal_value(self):
        self.validated['querystring'] = {'max_status': 2}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertTrue(all([value <= 2 for value in values]))

    def test_lt_value(self):
        self.validated['querystring'] = {'lt_status': 2}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertTrue(all([value < 2 for value in values]))

    def test_in_values(self):
        self.validated['querystring'] = {'in_status': [0, 1]}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertEqual(sorted(values), [0, 0, 1, 1])

    def test_exclude_values(self):
        self.validated['querystring'] = {'exclude_status': [0]}
        result = self.resource.collection_get()
        values = [item['status'] for item in result['data']]
        self.assertEqual(sorted(values), [1, 1, 2, 2, 3, 3])

    def test_has_values(self):
        self.validated['querystring'] = {'has_sometimes': True}
        result = self.resource.collection_get()
        values = [item['sometimes'] for item in result['data']]
        assert None in values
        self.assertEqual(sorted([v for v in values if v]), ['available', 'present'])

    def test_has_values_false(self):
        self.validated['querystring'] = {'has_sometimes': False}
        result = self.resource.collection_get()
        values = ['sometimes' in item for item in result['data']]
        self.assertEqual(sorted(values), [False, False, False, False, False])

    def test_include_returns_400_if_value_has_wrong_type(self):
        self.validated['querystring'] = {'in_id': [0, 1]}
        with self.assertRaises(httpexceptions.HTTPBadRequest) as cm:
            self.resource.collection_get()
        self.assertIn('in_id', cm.exception.json['message'])

        self.validated['querystring'] = {'in_last_modified': ['a', 'b']}
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_exclude_returns_400_if_value_has_wrong_type(self):
        self.validated['querystring'] = {'exclude_id': [0, 1]}
        with self.assertRaises(httpexceptions.HTTPBadRequest) as cm:
            self.resource.collection_get()
        self.assertIn('exclude_id', cm.exception.json['message'])

        self.validated['querystring'] = {'exclude_last_modified': ['a', 'b']}
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)


class SubobjectFilteringTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.validated = self.resource.request.validated
        self.patch_known_field.start()
        for i in range(6):
            record = {
                'party': {'candidate': 'Marie', 'voters': i},
                'location': 'Creuse'
            }
            self.model.create_record(record)

    def test_records_can_be_filtered_by_subobjects(self):
        self.validated['querystring'] = {'party.voters': 1}
        result = self.resource.collection_get()
        values = [item['party']['voters'] for item in result['data']]
        self.assertEqual(sorted(values), [1])

    def test_subobjects_filters_are_ignored_if_not_object(self):
        self.validated['querystring'] = {'location.city': 'barcelona'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_subobjects_filters_works_with_directives(self):
        self.validated['querystring'] = {'in_party.voters': [1, 2, 3]}
        result = self.resource.collection_get()
        values = [item['party']['voters'] for item in result['data']]
        self.assertEqual(sorted(values), [1, 2, 3])


class JSONFilteringTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.validated = self.resource.request.validated
        self.patch_known_field.start()
        records = [
            {
                "id": "strawberry",
                "flavor": "strawberry",
                "orders": [],
                "attributes": {"ibu": 25, "seen_on": "2017-06-01"},
                "author": None,
            },
            {"id": "blueberry-1", "flavor": "blueberry", "orders": [1]},
            {"id": "blueberry-2", "flavor": "blueberry", "orders": ""},
            {"id": "raspberry-1", "flavor": "raspberry", "attributes": {}},
            {"id": "raspberry-2", "flavor": "raspberry", "attributes": []},
            {
                "id": "raspberry-3",
                "flavor": "raspberry",
                "attributes": {"ibu": 25, "seen_on": "2017-06-01", "price": 9.99},
            },
            {"id": "watermelon-1", "flavor": "watermelon", "author": "null"},
            {"id": "watermelon-2", "flavor": "watermelon", "author": 0},
        ]
        for r in records:
            self.model.create_record(r)

    def test_filter_by_empty_array(self):
        self.validated['querystring'] = {'orders': []}
        result = self.resource.collection_get()
        assert len(result['data']) == 1
        assert result['data'][0]['id'] == 'strawberry'

    def test_filter_by_nonempty_array(self):
        self.validated['querystring'] = {'orders': [1]}
        result = self.resource.collection_get()
        assert len(result['data']) == 1
        assert result['data'][0]['id'] == 'blueberry-1'

    def test_filter_by_empty_object(self):
        self.validated['querystring'] = {'attributes': {}}
        result = self.resource.collection_get()
        assert len(result['data']) == 1
        assert result['data'][0]['id'] == 'raspberry-1'

    def test_filter_by_nonempty_object(self):
        self.validated['querystring'] = {'attributes': {'ibu': 25, 'seen_on': '2017-06-01'}}
        result = self.resource.collection_get()
        assert len(result['data']) == 1
        assert result['data'][0]['id'] == 'strawberry'

    def test_filter_by_null(self):
        self.validated['querystring'] = {'author': None}
        result = self.resource.collection_get()
        assert len(result['data']) == 1
        assert result['data'][0]['id'] == 'strawberry'
