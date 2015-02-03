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


class ReadArticleModificationTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(ReadArticleModificationTest, self).setUp()

        resp = self.app.post_json('/articles',
                                  MINIMALIST_ARTICLE,
                                  headers=self.headers)
        before = resp.json
        self.url = '/articles/{id}'.format(id=before['_id'])

        mark_read = {
            'read_position': 42,
            'unread': False,
            'marked_read_by': 'FxOS',
            'marked_read_on': 1234}
        resp = self.app.patch_json(self.url, mark_read, headers=self.headers)
        self.record = resp.json

    def refetch(self):
        resp = self.app.get(self.url, headers=self.headers)
        return resp.json

    def test_patch_changes_are_taken_into_account(self):
        record = self.refetch()
        self.assertEqual(record['marked_read_by'], 'FxOS')
        self.assertEqual(record['marked_read_on'], 1234)
        self.assertEqual(record['read_position'], 42)

    def test_mark_by_and_on_are_set_to_none_if_unread_is_true(self):
        self.app.patch_json(self.url,
                            {'unread': True},
                            headers=self.headers)
        record = self.refetch()
        self.assertIsNone(record['marked_read_by'])
        self.assertIsNone(record['marked_read_on'])

    def test_read_position_is_reset_when_unread_is_set_to_true(self):
        self.app.patch_json(self.url,
                            {'unread': True},
                            headers=self.headers)
        record = self.refetch()
        self.assertEqual(record['read_position'], 0)

    def test_read_position_is_ignored_if_set_to_lower_value(self):
        self.app.patch_json(self.url,
                            {'read_position': 41},
                            headers=self.headers)
        record = self.refetch()
        self.assertEqual(record['read_position'], 42)

    def test_read_position_is_saved_if_set_to_higher_value(self):
        self.app.patch_json(self.url,
                            {'read_position': 43},
                            headers=self.headers)
        record = self.refetch()
        self.assertEqual(record['read_position'], 43)
