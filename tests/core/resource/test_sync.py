import json
import mock
import time

from kinto.core.testing import ThreadMixin

from . import BaseTest


class SinceModifiedTest(ThreadMixin, BaseTest):

    def setUp(self):
        super().setUp()
        self.validated['body'] = {'data': {}}

        with mock.patch.object(self.model.storage,
                               '_bump_timestamp') as msec_mocked:
            for i in range(6):
                msec_mocked.return_value = i
                self.resource.collection_post()

    def test_filter_with_since_is_exclusive(self):
        self.validated['querystring'] = {'_since': 3}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 2)

    def test_filter_with__to_is_exclusive(self):
        self.validated['querystring'] = {'_to': 3}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 3)

    def test_filter_with__before_is_exclusive(self):
        self.validated['querystring'] = {'_before': 3}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 3)

    def test_filter_with__to_return_an_alert_header(self):
        self.validated['querystring'] = {'_to': 3}
        self.resource.collection_get()
        self.assertIn('Alert', self.resource.request.response.headers)
        alert = self.resource.request.response.headers['Alert']
        self.assertDictEqual(
            json.loads(alert),
            {
                'code': 'soft-eol',
                'message': ('_to is now deprecated, '
                            'you should use _before instead'),
                'url': ('https://kinto.readthedocs.io/en/2.4.0/api/resource'
                        '.html#list-of-available-url-parameters')
            })

    def test_get_timestamp_header_is_equal_to_last_modification(self):
        result = self.resource.collection_post()['data']
        modification = result['last_modified']
        self.resource = self.resource_class(request=self.get_request(),
                                            context=self.get_context())
        self.resource.request.validated = self.validated
        self.resource.collection_get()
        header = int(self.last_response.headers['ETag'][1:-1])
        self.assertEqual(header, modification)

    def test_delete_timestamp_header_is_equal_to_last_deleted(self):
        self.resource.collection_post()['data']
        self.resource = self.resource_class(request=self.get_request(),
                                            context=self.get_context())
        self.resource.request.validated = self.validated
        result = self.resource.collection_delete()
        modification = max([record['last_modified'] for record in result['data']])
        header = int(self.last_response.headers['ETag'][1:-1])
        self.assertEqual(header, modification)

    def test_post_timestamp_header_is_equal_to_creation(self):
        result = self.resource.collection_post()['data']
        modification = result['last_modified']
        header = int(self.last_response.headers['ETag'][1:-1])
        self.assertEqual(header, modification)

    def test_filter_with_since_accepts_numeric_value(self):
        self.validated['querystring'] = {'_since': 6}
        self.resource.collection_post()
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 1)

    def test_filter_from_last_modified_is_exclusive(self):
        result = self.resource.collection_post()['data']
        current = result['last_modified']

        self.validated['querystring'] = {'_since': current}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_filter_with_last_modified_includes_deleted_data(self):
        self.resource.collection_post()
        result = self.resource.collection_post()['data']
        current = result['last_modified']

        self.resource.record_id = result['id']
        self.resource.delete()

        self.validated['querystring'] = {'_since': current}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 1)
        self.assertTrue(result['data'][0]['deleted'])

    def test_filter_from_last_header_value_is_exclusive(self):
        self.resource.collection_get()
        current = int(self.last_response.headers['ETag'][1:-1])

        self.validated['querystring'] = {'_since': current}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_filter_works_with_empty_list(self):
        self.resource.model.parent_id = 'alice'
        self.validated['querystring'] = {'_since': 3}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_timestamp_are_always_identical_on_read(self):

        def read_timestamp():
            self.resource.collection_get()
            return int(self.last_response.headers['ETag'][1:-1])

        before = read_timestamp()
        now = read_timestamp()
        after = read_timestamp()
        self.assertEqual(before, now)
        self.assertEqual(now, after)

    def test_timestamp_are_always_incremented_on_creation(self):

        def read_timestamp():
            record = self.resource.collection_post()['data']
            return record['last_modified']

        before = read_timestamp()
        now = read_timestamp()
        after = read_timestamp()
        self.assertTrue(before < now < after)

    def test_records_created_during_fetch_are_above_fetch_timestamp(self):

        timestamps = {}

        def long_fetch():
            """Simulate a overhead while reading on storage."""

            def delayed_get(*args, **kwargs):
                time.sleep(.100)  # 100 msec
                return [], 0

            with mock.patch.object(self.model.storage,
                                   'get_all', delayed_get):
                self.resource.collection_get()
                fetch_at = self.last_response.headers['ETag'][1:-1]
                timestamps['fetch'] = int(fetch_at)

        # Create a real record with no patched timestamp
        self.resource.collection_post()

        # Some client start fetching
        thread = self._create_thread(target=long_fetch)
        thread.start()

        # Create record while other is fetching
        time.sleep(.020)  # 20 msec
        # Instantiate a new resource/request to avoid shared references with
        # the other one running in a thread:
        resource = self.resource_class(request=self.get_request(),
                                       context=self.get_context())
        resource.request.validated = self.validated
        resource.request.validated['body'] = {'data': {}}
        record = resource.collection_post()['data']
        timestamps['post'] = record['last_modified']

        # Wait for the fetch to finish
        thread.join()

        # Make sure fetch timestamp is below (for next fetch)
        self.assertGreater(timestamps['post'], timestamps['fetch'])
