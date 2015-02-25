from .support import BaseWebTest, unittest


def get_available_headers(headers):
    access_control_headers = headers['Access-Control-Expose-Headers']
    return [x.strip() for x in access_control_headers.split(',')]


class CORSTest(BaseWebTest, unittest.TestCase):
    def assert_headers_present(self, method, path, allowed_headers):
        if allowed_headers is None:
            return
        response = self.app.options(path, headers={
            'Origin': 'lolnet.org',
            'Access-Control-Request-Method': method})
        self.assertIn('Access-Control-Expose-Headers', response.headers)
        available_headers = get_available_headers(response.headers)
        for header in allowed_headers:
            self.assertIn(header, available_headers)

    def test_preflight_headers_are_set_for_default_endpoints(self):
        self.assert_headers_present('GET', '/',
                                    ['Alert', 'Backoff', 'Retry-After'])

    def test_preflight_headers_are_set_for_collection_get(self):
        self.assert_headers_present('GET', '/mushrooms', [
            'Alert', 'Backoff', 'Retry-After', 'Last-Modified',
            'Total-Records', 'Next-Page'])

    def test_preflight_headers_are_set_for_record_get(self):
        self.assert_headers_present('GET', '/mushrooms/id', [
            'Alert', 'Backoff', 'Retry-After', 'Last-Modified'])
