import mock
from .support import BaseWebTest, unittest

MINIMALIST_ARTICLE = dict(title="MoFo",
                          url="http://mozilla.org",
                          added_by="FxOS")


class CORSHeadersTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(CORSHeadersTest, self).setUp()
        self.headers['Origin'] = 'notmyidea.org'

    def test_support_on_hello(self):
        response = self.app.get('/',
                                headers=self.headers,
                                status=200)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_support_on_get_unknown_id(self):
        response = self.app.get('/articles/unknown',
                                headers=self.headers,
                                status=404)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_support_on_valid_definition(self):
        response = self.app.post_json('/articles',
                                      MINIMALIST_ARTICLE,
                                      headers=self.headers,
                                      status=201)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_support_on_invalid_article(self):
        article = MINIMALIST_ARTICLE.copy()
        article.pop('url')
        response = self.app.post_json('/articles',
                                      article,
                                      headers=self.headers,
                                      status=400)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_support_on_unauthorized(self):
        response = self.app.post_json('/articles',
                                      MINIMALIST_ARTICLE,
                                      headers={'Origin': 'notmyidea.org'},
                                      status=401)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_500_is_valid_formatted_error(self):
        with mock.patch('readinglist.views.article.Article.collection_get',
                        side_effect=ValueError):
            response = self.app.get('/articles',
                                    headers=self.headers, status=500)
        self.assertIn('Access-Control-Allow-Origin', response.headers)
