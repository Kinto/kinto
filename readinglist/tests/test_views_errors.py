try:
    import unittest2 as unittest
except ImportError:
    import unittest

import mock
from .support import BaseWebTest


class ErrorViewTest(BaseWebTest, unittest.TestCase):

    def test_backoff_header(self):
        with mock.patch.dict(
                self.app.app.registry.settings,
                [('readinglist.backoff', '10')]):
            response = self.app.get('/articles',
                                    headers=self.headers, status=200)
            self.assertIn('Backoff', response.headers)
            self.assertEquals(response.headers['Backoff'],
                              '10'.encode('utf-8'))
