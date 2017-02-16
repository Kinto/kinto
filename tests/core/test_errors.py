import json
import unittest

from kinto.core.errors import send_alert
from kinto.core.testing import DummyRequest


class SendAlertTest(unittest.TestCase):

    def verify_alert_header(self, request, expected):
        self.assertIn('Alert', request.response.headers)
        alert = request.response.headers['Alert']
        self.assertDictEqual(json.loads(alert),
                             expected)

    def test_send_alert_default_to_project_url(self):
        request = DummyRequest()
        request.registry.settings['project_docs'] = 'docs_url'
        send_alert(request, 'Message')
        self.verify_alert_header(request, {
            'code': 'soft-eol',
            'message': 'Message',
            'url': 'docs_url'
        })

    def test_send_alert_url_can_be_specified(self):
        request = DummyRequest()
        send_alert(request, 'Message', 'error_url')
        self.verify_alert_header(request, {
            'code': 'soft-eol',
            'message': 'Message',
            'url': 'error_url'
        })

    def test_send_alert_code_can_be_specified(self):
        request = DummyRequest()
        request.registry.settings['project_docs'] = 'docs_url'
        send_alert(request, 'Message', code='hard-eol')
        self.verify_alert_header(request, {
            'code': 'hard-eol',
            'message': 'Message',
            'url': 'docs_url'
        })
