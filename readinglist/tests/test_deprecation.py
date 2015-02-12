import datetime
import json

import mock

from .support import BaseWebTest, unittest
from readinglist.errors import ERRORS


class DeprecationTest(BaseWebTest, unittest.TestCase):

    def test_do_not_return_alert_if_no_eos(self):
        response = self.app.get('/')
        self.assertNotIn('Alert', response.headers)

    def test_returns_alert_if_eos_in_the_future(self):
        # Set an end of service date in the future.
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        with mock.patch.dict(
                self.app.app.registry.settings,
                [('readinglist.eos', tomorrow.isoformat()),
                 ('readinglist.eos_url', 'http://eos-url')]):
            response = self.app.get('/')

            # Requests should work as usual and contain an
            # Alert header, with the service end of life information.
            self.assertIn('Alert', response.headers)
            self.assertEquals(json.loads(response.headers['Alert']), {
                'code': 'soft-eol',
                'url': 'http://eos-url'
            })

    def test_returns_410_if_eos_in_the_past(self):
        # Set an end of service date in the past.
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        with mock.patch.dict(
                self.app.app.registry.settings,
                [('readinglist.eos', yesterday.isoformat()),
                 ('readinglist.eos_url', 'http://eos-url')]):
            response = self.app.get('/', status=410)
            self.assertIn('Alert', response.headers)
            self.assertEquals(json.loads(response.headers['Alert']), {
                'code': 'hard-eol',
                'url': 'http://eos-url'
            })
            self.assertEqual(response.body, json.dumps({
                "errno": ERRORS.SERVICE_DEPRECATED,
                "message": "The service you are trying to connect no longer "
                           "exists at this location.",
                "code": 410,
                "error": "Gone"
            }))
