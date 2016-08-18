from kinto.core.testing import unittest

from .support import BaseWebTest


class DisableDefaultBucketViewTest(BaseWebTest, unittest.TestCase):

    test_url = '/buckets/default'

    def test_returns_403_if_excluded_in_configuration(self):
        extra = {'includes': ''}
        app = self.make_app(settings=extra)
        app.get(self.test_url, headers=self.headers, status=403)

    def test_returns_200_if_included_in_configuration(self):
        extra = {'includes': 'kinto.plugins.default_bucket'}
        app = self.make_app(settings=extra)
        app.get(self.test_url, headers=self.headers, status=200)
