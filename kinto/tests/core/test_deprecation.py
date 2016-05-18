import datetime

import mock

from .support import BaseWebTest, unittest
from kinto.core.errors import ERRORS
from kinto.core.utils import json


class DeprecationTest(BaseWebTest, unittest.TestCase):

    def test_do_not_return_alert_if_no_eos(self):
        response = self.app.get('/')
        self.assertNotIn('Alert', response.headers)

    def test_returns_alert_if_eos_in_the_future(self):
        # Set an end of service date in the future.
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        with mock.patch.dict(self.app.app.registry.settings, [
                             ('eos', tomorrow.isoformat()),
                             ('eos_url', 'http://eos-url'),
                             ('eos_message',
                              'This service will soon be decommissioned')]):
            response = self.app.get('/')

            # Requests should work as usual and contain an
            # Alert header, with the service end of life information.
            self.assertIn('Alert', response.headers)
            self.assertDictEqual(json.loads(response.headers['Alert']), {
                'code': 'soft-eol',
                'url': 'http://eos-url',
                'message': 'This service will soon be decommissioned'
            })

    def test_returns_410_if_eos_in_the_past(self):
        # Set an end of service date in the past.
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        with mock.patch.dict(self.app.app.registry.settings, [
                             ('eos', yesterday.isoformat()),
                             ('eos_url', 'http://eos-url'),
                             ('eos_message',
                              'This service had been decommissioned')]):
            response = self.app.get('/', status=410)
            self.assertIn('Alert', response.headers)
            self.assertDictEqual(json.loads(response.headers['Alert']), {
                'code': 'hard-eol',
                'url': 'http://eos-url',
                'message': 'This service had been decommissioned'
            })
            self.assertDictEqual(response.json, {
                "errno": ERRORS.SERVICE_DEPRECATED.value,
                "message": "The service you are trying to connect no longer "
                           "exists at this location.",
                "code": 410,
                "error": "Gone"
            })
