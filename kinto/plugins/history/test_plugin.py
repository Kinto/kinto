from kinto.tests.support import (BaseWebTest, unittest)


class HelloViewTest(BaseWebTest, unittest.TestCase):

    def test_flush_capability_if_enabled(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('history', capabilities)

    def get_app_settings(self, extra=None):
        settings = super(HelloViewTest, self).get_app_settings(extra)
        settings['includes'] = 'kinto.plugins.history'
        return settings
