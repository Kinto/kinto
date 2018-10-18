import unittest

from kinto.core.views.openapi import openapi_view
from .support import BaseWebTest


class OpenAPIViewTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        try:
            delattr(openapi_view, "__json__")  # Clean-up memoization.
        except AttributeError:
            pass

    tearDown = setUp

    def test_get_spec_at_root(self):
        self.app.get("/__api__")
