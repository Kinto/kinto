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
        self.url = '/articles/{}'.format(self.before['_id'])

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
