import webtest
from pyramid.config import Configurator

from cliquet.tests import support as cliquet_support
from kinto import main

from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_BUCKET, MINIMALIST_COLLECTION,
                      MINIMALIST_RECORD)


class DisableDefaultBucketViewTest(BaseWebTest, unittest.TestCase):

    test_url = '/buckets/default'

    def setUp(self):
        super(DisableDefaultBucketViewTest, self).setUp()
        self.events = []


    def tearDown(self):
        self.events = []
        super(DisableDefaultBucketViewTest, self).tearDown()

    def _get_test_app(self, settings=None):
        app_settings = self.get_app_settings(settings)
        self.config = Configurator(settings=app_settings)
        app = webtest.TestApp(main({}, config=self.config, **app_settings))
        app.RequestClass = cliquet_support.get_request_class(prefix="v1")

        return app

    def get_app_settings(self, extra=None):
        if extra is None:
            extra = {}
        settings = super(DisableDefaultBucketViewTest, self).get_app_settings(extra)
        return settings

    def test_returns_403_if_excluded_in_configuration(self):
        extra = {'includes': ''}
        app = self._get_test_app(settings=extra)
        app.get(self.test_url, headers=self.headers, status=403)

    def test_returns_200_if_included_in_configuration(self):
        extra = {'includes': 'kinto.plugins.default_bucket'}
        app = self._get_test_app(settings=extra)
        app.get(self.test_url, headers=self.headers, status=200)
