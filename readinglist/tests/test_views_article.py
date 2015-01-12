import unittest

from .support import BaseResourceTest, BaseWebTest


MINIMALIST_ARTICLE = dict(title="MoFo",
                          url="http://mozilla.org",
                          added_by="FxOS")


class ResourceTest(BaseResourceTest, unittest.TestCase):
    resource = 'article'

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

    def test_mark_by_are_set_to_none_if_unread_is_true(self):
        url = '/articles/{}'.format(self.before['_id'])

        mark_read = MINIMALIST_ARTICLE.copy()
        mark_read.update(unread=False, marked_read_by='FxOS')
        resp = self.app.patch_json(url, mark_read, headers=self.headers)
        self.assertEqual(resp.json['marked_read_by'], 'FxOS')

        resp = self.app.patch_json(url, {'unread': True}, headers=self.headers)
        self.assertEqual(resp.json['marked_read_by'], None)

    def test_resolved_url_and_titles_are_set(self):
        self.assertEqual(self.before['resolved_url'], "http://mozilla.org")
        self.assertEqual(self.before['resolved_title'], "MoFo")
