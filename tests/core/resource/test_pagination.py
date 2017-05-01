import random
from base64 import b64encode, b64decode

import mock
from urllib.parse import parse_qs, urlparse
from pyramid.httpexceptions import HTTPBadRequest

from kinto.core.utils import json

from . import BaseTest


class BasePaginationTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.patch_known_field.start()

        indices = list(range(20))
        random.shuffle(indices)
        for i in indices:
            record = {
                'title': 'MoFo #{0:02}'.format(i),
                'status': i % 4,
                'unread': (i % 2 == 0)
            }
            self.model.create_record(record)

        self.validated = self.resource.request.validated

    def _setup_next_page(self):
        next_page = self.last_response.headers['Next-Page']
        url_fragments = urlparse(next_page)
        queryparams = parse_qs(url_fragments.query)
        self.validated['querystring']['_token'] = queryparams['_token'][0]
        self.validated['querystring']['_limit'] = int(queryparams['_limit'][0])
        self.last_response.headers = {}
        return queryparams


class PaginationTest(BasePaginationTest):
    def test_return_data(self):
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 20)

    def test_handle_limit(self):
        self.validated['querystring'] = {'_limit': 10}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 10)

    def test_handle_forced_limit(self):
        with mock.patch.dict(self.resource.request.registry.settings, [
                ('paginate_by', 10)]):
            result = self.resource.collection_get()
            self.assertEqual(len(result['data']), 10)

    def test_forced_limit_has_precedence_over_provided_limit(self):
        with mock.patch.dict(self.resource.request.registry.settings, [
                ('paginate_by', 5)]):
            self.validated['querystring'] = {'_limit': 10}
            result = self.resource.collection_get()
            self.assertEqual(len(result['data']), 5)

    def test_return_total_records_in_headers(self):
        self.validated['querystring'] = {'_limit': 5}
        self.resource.collection_get()
        headers = self.last_response.headers
        count = headers['Total-Records']
        self.assertEquals(int(count), 20)

    def test_return_next_page_url_is_given_in_headers(self):
        self.validated['querystring'] = {'_limit': 10}
        self.resource.collection_get()
        self.assertIn('Next-Page', self.last_response.headers)

    def test_next_page_url_has_got_querystring(self):
        self.validated['querystring'] = {'_limit': 10}
        self.resource.collection_get()
        queryparams = self._setup_next_page()
        self.assertIn('_limit', queryparams)
        self.assertIn('_token', queryparams)

    def test_next_page_url_gives_distinct_records(self):
        self.validated['querystring'] = {'_limit': 10}
        results1 = self.resource.collection_get()
        self._setup_next_page()
        results2 = self.resource.collection_get()
        results_id1 = set([x['id'] for x in results1['data']])
        results_id2 = set([x['id'] for x in results2['data']])
        self.assertFalse(results_id1.intersection(results_id2))

    def test_next_page_url_gives_distinct_records_with_forced_limit(self):
        with mock.patch.dict(self.resource.request.registry.settings, [
                ('paginate_by', 5)]):
            results1 = self.resource.collection_get()
            self._setup_next_page()
            results2 = self.resource.collection_get()

            results_id1 = set([x['id'] for x in results1['data']])
            results_id2 = set([x['id'] for x in results2['data']])
            self.assertFalse(results_id1.intersection(results_id2))

    def test_twice_the_same_next_page(self):
        self.validated['querystring'] = {'_limit': 10}
        self.resource.collection_get()
        first_next = self.last_response.headers['Next-Page']
        self.resource.collection_get()
        second_next = self.last_response.headers['Next-Page']
        self.assertEqual(first_next, second_next)

    def test_stops_giving_next_page_at_the_end_of_first_page(self):
        self.resource.collection_get()
        self.assertNotIn('Next-Page', self.last_response.headers)

    def test_stops_giving_next_page_at_the_end_sets(self):
        self.validated['querystring'] = {'_limit': 11}
        self.resource.collection_get()
        self._setup_next_page()
        self.resource.collection_get()
        self.assertNotIn('Next-Page', self.last_response.headers)

    def test_stops_giving_next_page_at_the_end_sets_on_exact_limit(self):
        self.validated['querystring'] = {'_limit': 10}
        self.resource.collection_get()
        self._setup_next_page()
        self.resource.collection_get()
        self.assertNotIn('Next-Page', self.last_response.headers)

    def test_handle_simple_sorting(self):
        self.validated['querystring'] = {'_sort': ['-status'], '_limit': 20}
        expected_results = self.resource.collection_get()
        self.validated['querystring']['_limit'] = 10
        results1 = self.resource.collection_get()
        self._setup_next_page()
        results2 = self.resource.collection_get()
        self.assertEqual(expected_results['data'],
                         results1['data'] + results2['data'])

    def test_handle_multiple_sorting(self):
        self.validated['querystring'] = {'_sort': ['-status', 'title'], '_limit': 20}
        expected_results = self.resource.collection_get()
        self.validated['querystring']['_limit'] = 10
        results1 = self.resource.collection_get()
        self._setup_next_page()
        results2 = self.resource.collection_get()
        self.assertEqual(expected_results['data'],
                         results1['data'] + results2['data'])

    def test_handle_filtering_sorting(self):
        self.validated['querystring'] = {'_sort': ['-status', 'title'], 'status': 2,
                                         '_limit': 20}
        expected_results = self.resource.collection_get()
        self.validated['querystring']['_limit'] = 3
        results1 = self.resource.collection_get()
        self._setup_next_page()
        results2 = self.resource.collection_get()
        self.assertEqual(expected_results['data'],
                         results1['data'] + results2['data'])

    def test_handle_sorting_desc(self):
        self.validated['querystring'] = {'_sort': ['status', '-title'], '_limit': 20}
        expected_results = self.resource.collection_get()
        self.validated['querystring']['_limit'] = 10
        results1 = self.resource.collection_get()
        self._setup_next_page()
        results2 = self.resource.collection_get()
        self.assertEqual(expected_results['data'],
                         results1['data'] + results2['data'])

    def test_handle_since(self):
        self.validated['querystring'] = {'_since': 123, '_limit': 20}
        expected_results = self.resource.collection_get()
        self.validated['querystring']['_limit'] = 10
        results1 = self.resource.collection_get()
        self._setup_next_page()
        results2 = self.resource.collection_get()
        self.assertEqual(expected_results['data'],
                         results1['data'] + results2['data'])

    def test_token_wrong_base64(self):
        self.validated['querystring'] = {
            '_since': 123, '_limit': 20, '_token': '123'}
        self.assertRaises(HTTPBadRequest, self.resource.collection_get)

    def test_token_wrong_json(self):
        self.validated['querystring'] = {
            '_since': 123, '_limit': 20,
            '_token': b64encode('{"toto":'.encode('ascii')).decode('ascii')}
        self.assertRaises(HTTPBadRequest, self.resource.collection_get)

    def test_token_wrong_json_fields(self):
        badtoken = '{"toto": {"tutu": 1}}'
        self.validated['querystring'] = {
            '_since': 123, '_limit': 20,
            '_token': b64encode(badtoken.encode('ascii')).decode('ascii')}
        self.assertRaises(HTTPBadRequest, self.resource.collection_get)

    def test_raises_bad_request_if_token_has_bad_data_structure(self):
        invalid_token = json.dumps([[('last_modified', 0, '>')]])
        self.validated['querystring'] = {
            '_since': 123, '_limit': 20,
            '_token': b64encode(invalid_token.encode('ascii')).decode('ascii')}
        self.assertRaises(HTTPBadRequest, self.resource.collection_get)


class PaginatedDeleteTest(BasePaginationTest):
    def test_handle_limit_on_delete(self):
        self.validated['querystring'] = {'_limit': 3}
        result = self.resource.collection_delete()
        self.assertEqual(len(result['data']), 3)

    def test_paginated_delete(self):
        all_records = self.resource.collection_get()
        expected_ids = [r['id'] for r in all_records['data']]
        # Page 1
        self.validated['querystring']['_limit'] = 10
        results1 = self.resource.collection_delete()
        results1_ids = [r['id'] for r in results1['data']]
        self._setup_next_page()
        # Page 2
        results2 = self.resource.collection_delete()
        results2_ids = [r['id'] for r in results2['data']]
        self.assertEqual(expected_ids, results1_ids + results2_ids)

    def test_return_total_records_in_headers_matching_deletable(self):
        self.validated['querystring'] = {'_limit': 5}
        self.resource.collection_delete()
        headers = self.last_response.headers
        count = headers['Total-Records']
        self.assertEquals(int(count), 20)


class BuildPaginationTokenTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.patch_known_field.start()
        self.record = {
            'id': 1, 'status': 2, 'unread': True,
            'last_modified': 1234, 'title': 'Title',
            'nested': {'subvalue': 42},
            'nested.other': {'subvalue': 43},
        }

    def test_token_contains_current_offset(self):
        token = self.resource._build_pagination_token([('last_modified', -1)],
                                                      self.record,
                                                      42)
        tokeninfo = json.loads(b64decode(token).decode('ascii'))
        self.assertEqual(tokeninfo['offset'], 42)

    def test_no_sorting_default_to_modified_field(self):
        token = self.resource._build_pagination_token([('last_modified', -1)],
                                                      self.record,
                                                      42)
        tokeninfo = json.loads(b64decode(token).decode('ascii'))
        self.assertDictEqual(tokeninfo['last_record'],
                             {"last_modified": 1234})

    def test_sorting_handle_both_rules(self):
        token = self.resource._build_pagination_token([
            ('status', -1),
            ('last_modified', -1)
        ], self.record, 34)
        tokeninfo = json.loads(b64decode(token).decode('ascii'))
        self.assertDictEqual(tokeninfo['last_record'],
                             {"last_modified": 1234, "status": 2})

    def test_sorting_handle_ordering_direction(self):
        token = self.resource._build_pagination_token([
            ('status', 1),
            ('last_modified', 1)
        ], self.record, 32)
        tokeninfo = json.loads(b64decode(token).decode('ascii'))
        self.assertEqual(tokeninfo['last_record'],
                         {"last_modified": 1234, "status": 2})

    def test_multiple_sorting_keep_all(self):
        token = self.resource._build_pagination_token([
            ('status', 1),
            ('title', -1),
            ('last_modified', -1)
        ], self.record, 31)
        tokeninfo = json.loads(b64decode(token).decode('ascii'))
        self.assertEqual(tokeninfo['last_record'],
                         {"last_modified": 1234, "status": 2,
                          'title': 'Title'})

    def test_sorting_on_nested_field(self):
        token = self.resource._build_pagination_token([
            ('nested.subvalue', -1),
            ('title', 1),
        ], self.record, 88)
        tokeninfo = json.loads(b64decode(token).decode('ascii'))
        self.assertEqual(tokeninfo['last_record'],
                         {'title': 'Title', 'nested.subvalue': 42})

    def test_disambiguate_fieldname_containing_dots(self):
        token = self.resource._build_pagination_token([
            ('nested.other.subvalue', -1),
            ('title', 1),
        ], self.record, 88)
        tokeninfo = json.loads(b64decode(token).decode('ascii'))
        self.assertEqual(tokeninfo['last_record'],
                         {'title': 'Title', 'nested.other.subvalue': 43})

    def test_strip_malformed_sort_field(self):
        token = self.resource._build_pagination_token([
            ('non.existent', -1),
            ('title', 1),
        ], self.record, 88)
        tokeninfo = json.loads(b64decode(token).decode('ascii'))
        self.assertEqual(tokeninfo['last_record'],
                         {'title': 'Title'})
