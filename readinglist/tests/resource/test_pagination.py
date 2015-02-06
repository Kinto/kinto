import random
from six.moves.urllib.parse import parse_qs, urlparse

from readinglist.tests.resource import BaseTest


class PaginationTest(BaseTest):
    def setUp(self):
        super(PaginationTest, self).setUp()

        indices = list(range(20))
        random.shuffle(indices)

        self.resource.known_fields = ['status', 'unread', 'title']
        for i in indices:
            record = {
                'title': 'MoFo #{0:02}'.format(i),
                'status': i % 4,
                'unread': (i % 2 == 0)
            }
            self.db.create(self.resource, 'bob', record)

    def _setup_next_page(self):
        next_page = self.last_response.headers['Next-Page'].decode('utf-8')
        url_fragments = urlparse(next_page)
        queryparams = parse_qs(url_fragments.query)
        self.resource.request.GET['_token'] = queryparams['_token'][0]
        self.resource.request.GET['_limit'] = queryparams['_limit'][0]
        self.last_response.headers = {}
        return queryparams

    def test_return_items(self):
        result = self.resource.collection_get()
        self.assertEqual(len(result['items']), 20)

    def test_handle_limit(self):
        self.resource.request.GET = {'_limit': '10'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['items']), 10)

    def test_return_next_page_url_is_given_in_headers(self):
        self.resource.request.GET = {'_limit': '10'}
        self.resource.collection_get()
        self.assertIn('Next-Page', self.last_response.headers)

    def test_next_page_url_has_got_querystring(self):
        self.resource.request.GET = {'_limit': '10'}
        self.resource.collection_get()
        queryparams = self._setup_next_page()
        self.assertIn('_limit', queryparams)
        self.assertIn('_token', queryparams)

    def test_next_page_url_gives_next_page(self):
        self.resource.request.GET = {'_limit': '10'}
        results1 = self.resource.collection_get()
        self._setup_next_page()
        results2 = self.resource.collection_get()
        self.assertFalse(
            set([x['_id'] for x in results1['items']]).intersection(
                set([x['_id'] for x in results2['items']])))

    def test_twice_the_same_next_page(self):
        self.resource.request.GET = {'_limit': '10'}
        self.resource.collection_get()
        first_next = self.last_response.headers['Next-Page']
        self.resource.collection_get()
        second_next = self.last_response.headers['Next-Page']
        self.assertEqual(first_next, second_next)

    def test_stops_giving_next_page_at_the_end_of_first_page(self):
        self.resource.collection_get()
        self.assertNotIn('Next-Page', self.last_response.headers)

    def test_stops_giving_next_page_at_the_end_sets(self):
        self.resource.request.GET = {'_limit': '11'}
        self.resource.collection_get()
        self._setup_next_page()
        self.resource.collection_get()
        self.assertNotIn('Next-Page', self.last_response.headers)

    # def test_stops_giving_next_page_at_the_end_sets_on_exact_limit(self):
    #     self.resource.request.GET = {'_limit': '10'}
    #     self.resource.collection_get()
    #     self._setup_next_page()
    #     self.resource.collection_get()
    #     self.assertNotIn('Next-Page', self.last_response.headers)

    def test_handle_simple_sorting(self):
        self.resource.request.GET = {'_sort': '-status'}
        expected_results = self.resource.collection_get()
        self.resource.request.GET['_limit'] = '10'
        results1 = self.resource.collection_get()
        self._setup_next_page()
        results2 = self.resource.collection_get()
        self.assertEqual(expected_results['items'],
                         results1['items'] + results2['items'])

    def test_handle_multiple_sorting(self):
        self.resource.request.GET = {'_sort': '-status,title'}
        expected_results = self.resource.collection_get()
        self.resource.request.GET['_limit'] = '10'
        results1 = self.resource.collection_get()
        self._setup_next_page()
        results2 = self.resource.collection_get()
        self.assertEqual(expected_results['items'],
                         results1['items'] + results2['items'])

    def test_handle_filtering_sorting(self):
        self.resource.request.GET = {'_sort': '-status,title', 'status': '2'}
        expected_results = self.resource.collection_get()
        self.resource.request.GET['_limit'] = '3'
        results1 = self.resource.collection_get()
        self._setup_next_page()
        results2 = self.resource.collection_get()
        self.assertEqual(expected_results['items'],
                         results1['items'] + results2['items'])

    def test_handle_sorting_desc(self):
        self.resource.request.GET = {'_sort': 'status,-title'}
        expected_results = self.resource.collection_get()
        self.resource.request.GET['_limit'] = '10'
        results1 = self.resource.collection_get()
        self._setup_next_page()
        results2 = self.resource.collection_get()
        self.assertEqual(expected_results['items'],
                         results1['items'] + results2['items'])

    def test_handle_since(self):
        self.resource.request.GET = {'_since': '123'}
        expected_results = self.resource.collection_get()
        self.resource.request.GET['_limit'] = '10'
        results1 = self.resource.collection_get()
        self._setup_next_page()
        results2 = self.resource.collection_get()
        self.assertEqual(expected_results['items'],
                         results1['items'] + results2['items'])
