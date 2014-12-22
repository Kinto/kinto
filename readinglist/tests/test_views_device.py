import unittest

from .support import BaseResourceTest


class DeviceResourceTest(BaseResourceTest, unittest.TestCase):
    resource = 'device'

    def record_factory(self):
        return dict(name="FxOS")

    def modify_record(self, original):
        return dict(name="Firefox OS")
