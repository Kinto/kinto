import unittest

from .support import BaseResourceTest


class ResourceTest(BaseResourceTest, unittest.TestCase):
    resource = 'article'

    def record_factory(self):
        return dict(title="MoFo", url="http://mozilla.org")

    def modify_record(self, original):
        return dict(title="Mozilla Foundation")
