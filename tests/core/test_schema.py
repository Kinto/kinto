import colander
import mock

from kinto.core.testing import unittest
from kinto.core import schema


class TimeStampTest(unittest.TestCase):
    def setUp(self):
        patch = mock.patch('kinto.core.schema.msec_time')
        self.time_mocked = patch.start()
        self.time_mocked.return_value = 666
        self.addCleanup(patch.stop)

    def test_default_value_comes_from_timestamper(self):
        default = schema.TimeStamp().deserialize(colander.null)
        self.assertEqual(default, 666)

    def test_default_value_is_none_if_not_autonow(self):
        ts = schema.TimeStamp()
        ts.auto_now = False
        default = ts.deserialize(colander.null)
        self.assertEqual(default, None)


class URLTest(unittest.TestCase):
    def test_supports_full_url(self):
        url = 'https://user:pass@myserver:9999/feeling.html#anchor'
        deserialized = schema.URL().deserialize(url)
        self.assertEqual(deserialized, url)

    def test_raises_invalid_if_no_scheme(self):
        url = 'myserver/feeling.html#anchor'
        self.assertRaises(colander.Invalid,
                          schema.URL().deserialize,
                          url)
