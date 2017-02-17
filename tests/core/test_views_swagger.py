import unittest

from kinto.core.views.swagger import swagger_view
from .support import BaseWebTest


class SwaggerViewTest(BaseWebTest, unittest.TestCase):

    def setUp(self):
        try:
            delattr(swagger_view, '__json__')  # Clean-up memoization.
        except AttributeError:
            pass

    tearDown = setUp

    def test_get_spec_at_root(self):
        self.app.get('/__api__')
