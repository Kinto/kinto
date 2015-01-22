import mock
from random import shuffle

from readinglist.errors import ERRORS
from readinglist.views.article import Article
from readinglist.utils import timestamper

from .support import BaseResourceTest, BaseWebTest, unittest


MINIMALIST_ARTICLE = dict(title="MoFo",
                          url="http://mozilla.org",
                          added_by="FxOS")


class ResourceTest(BaseResourceTest, unittest.TestCase):
    resource_class = Article

    def record_factory(self):
        return MINIMALIST_ARTICLE

    def modify_record(self, original):
        return dict(title="Mozilla Foundation")

    def _get_modified_keys(self):
        keys = set(self.modify_record(self.record).keys())
        keys |= set(['_id', 'last_modified', 'stored_on', 'url'])
        return keys


class ArticleModificationTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(ArticleModificationTest, self).setUp()
        resp = self.app.post_json('/articles',
                                  MINIMALIST_ARTICLE,
                                  headers=self.headers)
        self.before = resp.json
        self.url = '/articles/{id}'.format(id=self.before['_id'])

    def test_resolved_url_and_titles_are_set(self):
        self.assertEqual(self.before['resolved_url'], "http://mozilla.org")
        self.assertEqual(self.before['resolved_title'], "MoFo")

    def test_mark_by_and_on_are_set_to_none_if_unread_is_true(self):
        mark_read = {
            'unread': False,
            'marked_read_by': 'FxOS',
            'marked_read_on': 1234}
        resp = self.app.patch_json(self.url, mark_read, headers=self.headers)
        self.assertIsNotNone(resp.json['marked_read_by'])
        self.assertIsNotNone(resp.json['marked_read_on'])

        resp = self.app.patch_json(self.url,
                                   {'unread': True},
                                   headers=self.headers)
        self.assertIsNone(resp.json['marked_read_by'])
        self.assertIsNone(resp.json['marked_read_on'])

    def test_cannot_modify_url(self):
        body = {'url': 'http://immutable.org'}
        self.app.patch_json(self.url,
                            body,
                            headers=self.headers,
                            status=400)

    def test_cannot_modify_stored_on(self):
        body = {'stored_on': 1234}
        self.app.patch_json(self.url,
                            body,
                            headers=self.headers,
                            status=400)


class ArticleFilteringTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(ArticleFilteringTest, self).setUp()
        for i in range(6):
            article = MINIMALIST_ARTICLE.copy()
            article['status'] = i % 3
            article['favorite'] = (i % 4 == 0)
            self.app.post_json('/articles', article, headers=self.headers)

    def test_number_of_records_matches_filter(self):
        resp = self.app.head('/articles?status=1', headers=self.headers)
        count = resp.headers['Total-Records']
        self.assertEquals(int(count), 2)

    def test_single_basic_filter_by_attribute(self):
        resp = self.app.get('/articles?status=1', headers=self.headers)
        self.assertEqual(len(resp.json['items']), 2)

    def test_filter_on_unknown_attribute_raises_error(self):
        url = '/articles?foo=1'
        resp = self.app.get(url, headers=self.headers, status=400)
        self.assertFormattedError(
            resp, 400, ERRORS.INVALID_PARAMETERS,
            "Invalid parameters", "querystring: Unknown filter field 'foo'")

    def test_double_basic_filter_by_attribute(self):
        resp = self.app.get('/articles?status=1&favorite=true',
                            headers=self.headers)
        self.assertEqual(len(resp.json['items']), 1)

    def test_string_filters_naively_by_value(self):
        resp = self.app.get('/articles?title=MoF', headers=self.headers)
        self.assertEqual(len(resp.json['items']), 0)
        resp = self.app.get('/articles?title=MoFo', headers=self.headers)
        self.assertEqual(len(resp.json['items']), 6)

    def test_filter_considers_string_if_syntaxically_invalid(self):
        url = '/articles?status=1.2.3'
        resp = self.app.get(url, headers=self.headers)
        self.assertEqual(len(resp.json['items']), 0)

    def test_different_value(self):
        resp = self.app.get('/articles?not_status=2', headers=self.headers)
        values = [item['status'] for item in resp.json['items']]
        self.assertTrue(all([value != 2 for value in values]))

    def test_minimal_value(self):
        resp = self.app.get('/articles?min_status=2', headers=self.headers)
        values = [item['status'] for item in resp.json['items']]
        self.assertTrue(all([value >= 2 for value in values]))

    def test_maximal_value(self):
        resp = self.app.get('/articles?max_status=1', headers=self.headers)
        values = [item['status'] for item in resp.json['items']]
        self.assertTrue(all([value <= 1 for value in values]))

    def test_regexp_false_positive(self):
        """Make sure madmax is not understood as max."""
        self.app.get('/articles?madmax_status=1',
                     headers=self.headers,
                     status=400)


class ArticleFilterModifiedTest(BaseWebTest, unittest.TestCase):

    @mock.patch('readinglist.utils.TimeStamper.now')
    def setUp(self, now_mocked):
        super(ArticleFilterModifiedTest, self).setUp()
        for i in range(6):
            now_mocked.return_value = i
            article = MINIMALIST_ARTICLE.copy()
            self.app.post_json('/articles', article, headers=self.headers)

    def test_filter_with_since_is_exclusive(self):
        resp = self.app.get('/articles?_since=3', headers=self.headers)
        self.assertEqual(len(resp.json['items']), 2)

    def test_the_timestamp_header_is_equal_to_last_modification(self):
        article = MINIMALIST_ARTICLE.copy()
        resp = self.app.post_json('/articles', article, headers=self.headers)
        modification = resp.json['last_modified']
        header = float(resp.headers['Timestamp'])
        self.assertEqual(header, modification)

    def test_filter_with_since_accepts_decimal_value(self):
        before = timestamper.now()
        article = MINIMALIST_ARTICLE.copy()
        self.app.post_json('/articles', article, headers=self.headers)
        url = '/articles?_since={0}'.format(before)
        resp = self.app.get(url, headers=self.headers)
        self.assertEqual(len(resp.json['items']), 1)

    def test_filter_from_last_modified_is_exclusive(self):
        article = MINIMALIST_ARTICLE.copy()
        resp = self.app.post_json('/articles', article, headers=self.headers)

        current = resp.json['last_modified']
        url = '/articles?_since={0}'.format(current)

        resp = self.app.get(url, headers=self.headers)
        self.assertEqual(len(resp.json['items']), 0)

    def test_filter_from_last_header_value_is_exclusive(self):
        article = MINIMALIST_ARTICLE.copy()
        resp = self.app.post_json('/articles', article, headers=self.headers)

        current = float(resp.headers['Timestamp'])
        url = '/articles?_since={0:.3f}'.format(current)

        resp = self.app.get(url, headers=self.headers)
        self.assertEqual(len(resp.json['items']), 0)

    def test_filter_works_with_empty_list(self):
        self.fxa_verify.return_value = {
            'user': 'jean-louis'
        }
        self.app.get('/articles?unread=true', headers=self.headers)

    def test_filter_with_since_rejects_non_numeric_value(self):
        url = '/articles?_since=abc'
        self.app.get(url, headers=self.headers, status=400)

    def test_filter_with_since_rejects_decimal_value(self):
        url = '/articles?_since=1.2'
        self.app.get(url, headers=self.headers, status=400)


class ArticleSortingTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(ArticleSortingTest, self).setUp()
        articles = list(range(20))
        shuffle(articles)
        for i in articles:
            article = MINIMALIST_ARTICLE.copy()
            article['title'] = '{title} #{number:02}'.format(
                title=article['title'], number=i)
            article['status'] = i % 4
            article['unread'] = (i % 2 == 0)
            self.app.post_json('/articles', article, headers=self.headers)

    def test_sort_works_with_empty_list(self):
        self.fxa_verify.return_value = {
            'user': 'jean-louis'
        }
        self.app.get('/articles?_sort=unread', headers=self.headers)

    def test_sort_on_unknown_attribute_raises_error(self):
        url = '/articles?_sort=foo'
        resp = self.app.get(url, headers=self.headers, status=400)
        self.assertFormattedError(
            resp, 400, ERRORS.INVALID_PARAMETERS,
            "Invalid parameters", "querystring: Unknown sort field 'foo'")

    def test_single_basic_sort_by_attribute(self):
        resp = self.app.get('/articles?_sort=title', headers=self.headers)
        records = resp.json['items']
        self.assertEqual(records[0]['title'], 'MoFo #00')
        self.assertEqual(records[-1]['title'], 'MoFo #19')

    def test_single_basic_sort_by_attribute_reversed(self):
        resp = self.app.get('/articles?_sort=-title', headers=self.headers)
        records = resp.json['items']
        self.assertEqual(records[0]['title'], 'MoFo #19')
        self.assertEqual(records[-1]['title'], 'MoFo #00')

    def test_boolean_sort_brings_true_first(self):
        resp = self.app.get('/articles?_sort=unread', headers=self.headers)
        records = resp.json['items']
        self.assertEqual(records[0]['unread'], True)
        self.assertEqual(records[-1]['unread'], False)

    def test_multiple_sort(self):
        resp = self.app.get('/articles?_sort=status,title',
                            headers=self.headers)
        records = resp.json['items']
        self.assertEqual(records[0]['status'], 0)
        self.assertEqual(records[0]['title'], 'MoFo #00')
        self.assertEqual(records[1]['status'], 0)
        self.assertEqual(records[1]['title'], 'MoFo #04')
        self.assertEqual(records[-2]['status'], 3)
        self.assertEqual(records[-2]['title'], 'MoFo #15')
        self.assertEqual(records[-1]['status'], 3)
        self.assertEqual(records[-1]['title'], 'MoFo #19')

    def test_multiple_sort_with_order(self):
        resp = self.app.get('/articles?_sort=status,-title',
                            headers=self.headers)
        records = resp.json['items']
        self.assertEqual(records[0]['status'], 0)
        self.assertEqual(records[0]['title'], 'MoFo #16')
        self.assertEqual(records[1]['status'], 0)
        self.assertEqual(records[1]['title'], 'MoFo #12')
        self.assertEqual(records[-2]['status'], 3)
        self.assertEqual(records[-2]['title'], 'MoFo #07')
        self.assertEqual(records[-1]['status'], 3)
        self.assertEqual(records[-1]['title'], 'MoFo #03')
