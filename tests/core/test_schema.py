import colander
import mock

from kinto.core.testing import unittest
from kinto.core import schema


class TimeStampTest(unittest.TestCase):
    @mock.patch('kinto.core.schema.msec_time')
    def test_default_value_comes_from_timestamper(self, time_mocked):
        time_mocked.return_value = 666
        default = schema.TimeStamp().deserialize(colander.null)
        self.assertEqual(default, 666)


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
