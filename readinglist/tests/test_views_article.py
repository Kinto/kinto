from .support import BaseWebTest, unittest


MINIMALIST_ARTICLE = dict(title="MoFo",
                          url="http://mozilla.org",
                          added_by="FxOS")


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

    def test_patch_marked_read_are_taken_into_account(self):
        mark_read = {
            'unread': False,
            'marked_read_by': 'FxOS',
            'marked_read_on': 1234}
        resp = self.app.patch_json(self.url, mark_read, headers=self.headers)
        body = resp.json
        self.assertEqual(body['marked_read_by'], mark_read['marked_read_by'])
        self.assertEqual(body['marked_read_on'], mark_read['marked_read_on'])

        resp = self.app.get(self.url, headers=self.headers)
        body = resp.json
        self.assertEqual(body['marked_read_by'], mark_read['marked_read_by'])
        self.assertEqual(body['marked_read_on'], mark_read['marked_read_on'])

    def test_cannot_modify_last_modified(self):
        body = {'last_modified': 123}
        self.app.patch_json(self.url,
                            body,
                            headers=self.headers,
                            status=400)

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
