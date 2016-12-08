import unittest

from .support import BaseWebTest


class SwaggerViewTest(BaseWebTest, unittest.TestCase):

    def test_get_spec(self):
        spec_dict = self.app.get('/swagger.json').json
        self.assertIsNotNone(spec_dict)
