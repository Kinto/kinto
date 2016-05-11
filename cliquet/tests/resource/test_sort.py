import random

from pyramid import httpexceptions

from cliquet.errors import ERRORS
from cliquet.tests.resource import BaseTest


class SortingTest(BaseTest):
    def setUp(self):
        super(SortingTest, self).setUp()
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

    def test_sort_works_with_empty_list(self):
        self.resource.model.parent_id = 'alice'
        self.resource.request.GET = {'_sort': 'unread'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_sort_on_unknown_attribute_raises_error(self):
        self.patch_known_field.stop()
        self.resource.request.GET = {'_sort': 'foo'}
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_filter_errors_are_json_formatted(self):
        self.patch_known_field.stop()
        self.resource.request.GET = {'_sort': 'foo'}
        try:
            self.resource.collection_get()
        except httpexceptions.HTTPBadRequest as e:
            error = e
        self.assertEqual(error.json, {
            'errno': ERRORS.INVALID_PARAMETERS.value,
            'message': "querystring: Unknown sort field 'foo'",
            'code': 400,
            'error': 'Invalid parameters',
            'details': [{'description': "Unknown sort field 'foo'",
                         'location': 'querystring',
                         'name': None}]})

    def test_sort_on_last_modified_is_supported(self):
        self.patch_known_field.stop()
        self.resource.request.GET = {'_sort': '-last_modified'}
        result = self.resource.collection_get()
        tstamp = self.model.timestamp()
        self.assertEqual(result['data'][0]['last_modified'], tstamp)

    def test_single_basic_sort_by_attribute(self):
        self.resource.request.GET = {'_sort': 'title'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 20)
        self.assertEqual(result['data'][0]['title'], 'MoFo #00')
        self.assertEqual(result['data'][-1]['title'], 'MoFo #19')

    def test_single_basic_sort_by_attribute_reversed(self):
        self.resource.request.GET = {'_sort': '-title'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 20)
        self.assertEqual(result['data'][0]['title'], 'MoFo #19')
        self.assertEqual(result['data'][-1]['title'], 'MoFo #00')

    def test_multiple_sort(self):
        self.resource.request.GET = {'_sort': 'status,title'}
        result = self.resource.collection_get()
        self.assertEqual(result['data'][0]['status'], 0)
        self.assertEqual(result['data'][0]['title'], 'MoFo #00')
        self.assertEqual(result['data'][1]['status'], 0)
        self.assertEqual(result['data'][1]['title'], 'MoFo #04')
        self.assertEqual(result['data'][-2]['status'], 3)
        self.assertEqual(result['data'][-2]['title'], 'MoFo #15')
        self.assertEqual(result['data'][-1]['status'], 3)
        self.assertEqual(result['data'][-1]['title'], 'MoFo #19')

    def test_multiple_sort_with_order(self):
        self.resource.request.GET = {'_sort': 'status,-title'}
        result = self.resource.collection_get()
        self.assertEqual(result['data'][0]['status'], 0)
        self.assertEqual(result['data'][0]['title'], 'MoFo #16')
        self.assertEqual(result['data'][1]['status'], 0)
        self.assertEqual(result['data'][1]['title'], 'MoFo #12')
        self.assertEqual(result['data'][-2]['status'], 3)
        self.assertEqual(result['data'][-2]['title'], 'MoFo #07')
        self.assertEqual(result['data'][-1]['status'], 3)
        self.assertEqual(result['data'][-1]['title'], 'MoFo #03')

    def test_boolean_sort_brings_true_last(self):
        self.resource.request.GET = {'_sort': 'unread'}
        result = self.resource.collection_get()
        self.assertEqual(result['data'][0]['unread'], False)
        self.assertEqual(result['data'][-1]['unread'], True)

    def test_default_sort_is_last_modified_desc_by_default(self):
        self.resource.request.GET = {'_sort': ''}
        result = self.resource.collection_get()
        tstamp = self.model.timestamp()
        self.assertEqual(result['data'][0]['last_modified'], tstamp)

    def test_default_sort_is_last_modified_records_have_same_status(self):
        self.resource.request.GET = {'_sort': 'status'}
        result = self.resource.collection_get()
        self.assertEqual(result['data'][0]['status'], 0)
        self.assertEqual(result['data'][1]['status'], 0)
        self.assertGreater(result['data'][0]['last_modified'],
                           result['data'][1]['last_modified'])
