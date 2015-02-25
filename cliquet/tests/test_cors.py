from .support import BaseWebTest, unittest


def get_available_headers(headers):
    access_control_headers = headers['Access-Control-Expose-Headers']
    return [x.strip() for x in access_control_headers.split(',')]


class CORSTest(BaseWebTest, unittest.TestCase):
    def test_preflight_headers_for_default(self):
        response = self.app.options('/', headers={
            'Origin': 'lolnet.org',
            'Access-Control-Request-Method': 'GET'})
        self.assertIn('Access-Control-Expose-Headers', response.headers)
        available_headers = get_available_headers(response.headers)
        for header in ['Alert', 'Backoff', 'Retry-After']:
            self.assertIn(header, available_headers)

    def test_preflight_headers_for_collection_get(self):
        response = self.app.options('/mushrooms', headers={
            'Origin': 'lolnet.org',
            'Access-Control-Request-Method': 'GET'})
        self.assertIn('Access-Control-Expose-Headers', response.headers)
        available_headers = get_available_headers(response.headers)
        for header in ['Alert', 'Backoff', 'Retry-After', 'Last-Modified',
                       'Total-Records', 'Next-Page']:
            self.assertIn(header, available_headers)

    def test_preflight_headers_for_record_get(self):
        response = self.app.options('/mushrooms/id', headers={
            'Origin': 'lolnet.org',
            'Access-Control-Request-Method': 'GET'})
        self.assertIn('Access-Control-Expose-Headers', response.headers)
        available_headers = get_available_headers(response.headers)
        for header in ['Alert', 'Backoff', 'Retry-After', 'Last-Modified']:
            self.assertIn(header, available_headers)
