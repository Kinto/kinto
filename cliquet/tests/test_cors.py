import json
from .support import BaseWebTest, unittest


def get_exposed_headers(headers):
    access_control_headers = headers['Access-Control-Expose-Headers']
    return [x.strip() for x in access_control_headers.split(',')]


class CORSTest(BaseWebTest, unittest.TestCase):
    def assert_headers_present(self, method, path, allowed_headers):
        if allowed_headers is None:
            return
        self.headers.update({'Origin': 'lolnet.org'})
        http_method = getattr(self.app, method.lower())
        response = http_method(path, headers=self.headers)
        self.assertIn('Access-Control-Expose-Headers', response.headers)
        exposed_headers = get_exposed_headers(response.headers).sort()
        self.assertEqual(allowed_headers.sort(), exposed_headers)

    def test_preflight_headers_are_set_for_default_endpoints(self):
        self.assert_headers_present('GET', '/',
                                    ['Alert', 'Backoff', 'Retry-After'])

    def test_preflight_headers_are_set_for_collection_get(self):
        self.assert_headers_present('GET', '/mushrooms', [
            'Alert', 'Backoff', 'Retry-After', 'Last-Modified',
            'Total-Records', 'Next-Page'])

    def test_preflight_headers_are_set_for_record_get(self):
        resp = self.app.post('/mushrooms', json.dumps({'name': 'Bolet'}),
                             headers=self.headers, status=201)
        self.assert_headers_present('GET', '/mushrooms/%s' % resp.json['id'], [
            'Alert', 'Backoff', 'Retry-After', 'Last-Modified'])
