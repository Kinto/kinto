from cliquet.tests.support import unittest

from cliquet.resource import TimeStamp

import colander
import mock


class TimeStampTest(unittest.TestCase):
    @mock.patch('cliquet.resource.msec_time')
    def test_default_value_comes_from_timestamper(self, time_mocked):
        time_mocked.return_value = 666
        default = TimeStamp().deserialize(colander.null)
        self.assertEqual(default, 666)
