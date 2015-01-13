try:
    import unittest2 as unittest
except ImportError:
    import unittest

from readinglist.views.article import Article
from .support import BaseResourceTest, BaseWebTest


MINIMALIST_ARTICLE = dict(title="MoFo",
                          url="http://mozilla.org",
                          added_by="FxOS")


class ResourceTest(BaseResourceTest, unittest.TestCase):
    resource_class = Article

    def record_factory(self):
        return MINIMALIST_ARTICLE

    def modify_record(self, original):
        return dict(title="Mozilla Foundation")


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


class ArticleFilteringTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(ArticleFilteringTest, self).setUp()
        for i in range(6):
            article = MINIMALIST_ARTICLE.copy()
            article['status'] = i % 3
            article['favorite'] = (i % 4 == 0)
            self.app.post_json('/articles', article, headers=self.headers)

    def test_single_basic_filter_by_attribute(self):
        resp = self.app.get('/articles?status=1', headers=self.headers)
        self.assertEqual(len(resp.json['items']), 2)

    def test_filter_on_unknown_attribute_is_ignored(self):
        resp = self.app.get('/articles?foo=1', headers=self.headers)
        self.assertEqual(len(resp.json['items']), 6)

    def test_double_basic_filter_by_attribute(self):
        resp = self.app.get('/articles?status=1&favorite=true',
                            headers=self.headers)
        self.assertEqual(len(resp.json['items']), 1)

    def test_string_filters_naively_by_value(self):
        resp = self.app.get('/articles?title=MoF', headers=self.headers)
        self.assertEqual(len(resp.json['items']), 0)
        resp = self.app.get('/articles?title=MoFo', headers=self.headers)
        self.assertEqual(len(resp.json['items']), 6)


class ArticleSortingTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(ArticleSortingTest, self).setUp()
        for i in range(6):
            article = MINIMALIST_ARTICLE.copy()
            article['title'] = '{title} #{number}'.format(
                title=article['title'], number=i)
            article['status'] = i % 3
            self.app.post_json('/articles', article, headers=self.headers)

    def test_single_basic_sort_by_attribute(self):
        resp = self.app.get('/articles?sort=title', headers=self.headers)
        records = resp.json['items']
        self.assertEqual(records[0]['title'], 'MoFo #0')
        self.assertEqual(records[-1]['title'], 'MoFo #5')

    def test_single_basic_sort_by_attribute_reversed(self):
        resp = self.app.get('/articles?sort=-title', headers=self.headers)
        records = resp.json['items']
        self.assertEqual(records[0]['title'], 'MoFo #5')
        self.assertEqual(records[-1]['title'], 'MoFo #0')

    def test_multiple_sort(self):
        resp = self.app.get('/articles?sort=status,title',
                            headers=self.headers)
        records = resp.json['items']
        self.assertEqual(records[0]['status'], 0)
        self.assertEqual(records[0]['title'], 'MoFo #0')
        self.assertEqual(records[1]['status'], 0)
        self.assertEqual(records[1]['title'], 'MoFo #3')
