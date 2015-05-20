import mock

from .test_views import BaseWebTest


MINIMALIST_RECORD = {'name': 'Champignon'}


class CORSOriginHeadersTest(BaseWebTest):
    def setUp(self):
        super(CORSOriginHeadersTest, self).setUp()
        self.headers['Origin'] = 'notmyidea.org'

        body = {'data': MINIMALIST_RECORD}
        response = self.app.post_json(self.collection_url,
                                      body,
                                      headers=self.headers,
                                      status=201)
        self.record = response.json['data']

    def test_present_on_hello(self):
        response = self.app.get('/',
                                headers=self.headers,
                                status=200)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_single_record(self):
        response = self.app.get(self.get_item_url(),
                                headers=self.headers)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_deletion(self):
        response = self.app.delete(self.get_item_url(),
                                   headers=self.headers)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_unknown_record(self):
        url = self.get_item_url('1cea99eb-5e3d-44ad-a53a-2fb68473b538')
        response = self.app.get(url,
                                headers=self.headers,
                                status=404)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_invalid_record_update(self):
        body = {'data': {'name': 42}}
        response = self.app.patch_json(self.get_item_url(),
                                       body,
                                       headers=self.headers,
                                       status=400)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_successful_creation(self):
        body = {'data': MINIMALIST_RECORD}
        response = self.app.post_json(self.collection_url,
                                      body,
                                      headers=self.headers,
                                      status=201)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_invalid_record_creation(self):
        body = {'name': 42}
        response = self.app.post_json(self.collection_url,
                                      body,
                                      headers=self.headers,
                                      status=400)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_readonly_update(self):
        with mock.patch('cliquet.tests.testapp.views.'
                        'MushroomSchema.is_readonly',
                        return_value=True):
            body = {'data': {'name': 'Amanite'}}
            response = self.app.patch_json(self.get_item_url(),
                                           body,
                                           headers=self.headers,
                                           status=400)
        self.assertEqual(response.json['message'], 'Cannot modify name')
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_unauthorized(self):
        self.headers.pop('Authorization', None)
        body = {'data': MINIMALIST_RECORD}
        response = self.app.post_json(self.collection_url,
                                      body,
                                      headers=self.headers,
                                      status=401)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_internal_error(self):
        with mock.patch('cliquet.resource.BaseResource._extract_filters',
                        side_effect=ValueError):
            response = self.app.get('/mushrooms',
                                    headers=self.headers, status=500)
        self.assertIn('Access-Control-Allow-Origin', response.headers)


class CORSExposeHeadersTest(BaseWebTest):
    def assert_expose_headers(self, method, path, allowed_headers, body=None):
        self.headers.update({'Origin': 'lolnet.org'})
        http_method = getattr(self.app, method.lower())
        response = http_method(path, body, headers=self.headers)
        exposed_headers = response.headers['Access-Control-Expose-Headers']
        exposed_headers = [x.strip() for x in exposed_headers.split(',')]
        self.assertEqual(sorted(allowed_headers), sorted(exposed_headers))

    def test_collection_get_exposes_every_possible_header(self):
        self.assert_expose_headers('GET', self.collection_url, [
            'Alert', 'Backoff', 'ETag', 'Last-Modified', 'Next-Page',
            'Retry-After', 'Total-Records'])

    def test_hello_endpoint_exposes_only_minimal_set_of_headers(self):
        self.assert_expose_headers('GET', '/', [
            'Alert', 'Backoff', 'Retry-After'])

    def test_record_get_exposes_only_used_headers(self):
        body = {'data': MINIMALIST_RECORD}
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers,
                                  status=201)
        record_url = self.get_item_url(resp.json['data']['id'])
        self.assert_expose_headers('GET', record_url, [
            'Alert', 'Backoff', 'ETag', 'Retry-After', 'Last-Modified'])

    def test_record_post_exposes_only_minimal_set_of_headers(self):
        body = {'data': MINIMALIST_RECORD}
        self.assert_expose_headers('POST_JSON', '/mushrooms', [
            'Alert', 'Backoff', 'Retry-After'], body=body)
