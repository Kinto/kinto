import mock
from pyramid import httpexceptions

from kinto.core.errors import ERRORS, http_error

from .support import BaseWebTest, unittest, authorize, FormattedErrorMixin


class ErrorViewTest(FormattedErrorMixin, BaseWebTest, unittest.TestCase):

    sample_url = "/mushrooms"

    def test_backoff_headers_is_not_present_by_default(self):
        response = self.app.get(self.sample_url,
                                headers=self.headers, status=200)
        self.assertNotIn('Backoff', response.headers)

    def test_backoff_headers_is_present_if_configured(self):
        with mock.patch.dict(self.app.app.registry.settings,
                             [('backoff', 10)]):
            response = self.app.get(self.sample_url,
                                    headers=self.headers, status=200)
        self.assertIn('Backoff', response.headers)

    def test_backoff_headers_is_present_on_304(self):
        first = self.app.get(self.sample_url, headers=self.headers)
        etag = first.headers['ETag']
        headers = self.headers.copy()
        headers['If-None-Match'] = etag
        with mock.patch.dict(self.app.app.registry.settings,
                             [('backoff', 10)]):
            response = self.app.get(self.sample_url, headers=headers,
                                    status=304)
        self.assertIn('Backoff', response.headers)

    def test_backoff_header_is_present_on_error_responses(self):
        with mock.patch.dict(
                self.app.app.registry.settings,
                [('backoff', 10)]):
            response = self.app.get(self.sample_url,
                                    headers=self.headers, status=200)
            self.assertIn('Backoff', response.headers)
            self.assertEquals(response.headers['Backoff'], '10')

    def test_404_is_valid_formatted_error(self):
        response = self.app.get('/unknown', status=404)
        self.assertFormattedError(
            response, 404, ERRORS.MISSING_RESOURCE, "Not Found",
            "The resource you are looking for could not be found.")

    def test_401_is_valid_formatted_error(self):
        response = self.app.get(self.sample_url, status=401)
        self.assertFormattedError(
            response, 401, ERRORS.MISSING_AUTH_TOKEN, "Unauthorized",
            "Please authenticate yourself to use this endpoint.")

    @authorize(False)
    def test_403_is_valid_formatted_error(self):
        response = self.app.get(self.sample_url,
                                headers=self.headers, status=403)
        self.assertFormattedError(
            response, 403, ERRORS.FORBIDDEN, "Forbidden",
            "This user cannot access this resource.")

    def test_405_is_valid_formatted_error(self):
        response = self.app.patch(self.sample_url,
                                  headers=self.headers, status=405)
        self.assertFormattedError(
            response, 405, ERRORS.METHOD_NOT_ALLOWED, "Method Not Allowed",
            "Method not allowed on this endpoint.")

    def test_405_can_have_custom_message(self):
        custom_405 = http_error(httpexceptions.HTTPMethodNotAllowed(),
                                errno=ERRORS.METHOD_NOT_ALLOWED,
                                message="Disabled from conf.")
        with mock.patch(
                'kinto.tests.core.testapp.views.Mushroom._extract_filters',
                side_effect=custom_405):
            response = self.app.get(self.sample_url,
                                    headers=self.headers, status=405)
        self.assertFormattedError(
            response, 405, ERRORS.METHOD_NOT_ALLOWED, "Method Not Allowed",
            "Disabled from conf.")

    def test_500_is_valid_formatted_error(self):
        with mock.patch(
                'kinto.tests.core.testapp.views.Mushroom._extract_filters',
                side_effect=ValueError):
            response = self.app.get(self.sample_url,
                                    headers=self.headers, status=500)
        self.assertFormattedError(
            response, 500, ERRORS.UNDEFINED, "Internal Server Error",
            "A programmatic error occured, developers have been informed.",
            "https://github.com/Kinto/kinto/issues/")

    def test_info_link_in_error_responses_can_be_configured(self):
        with mock.patch(
                'kinto.tests.core.testapp.views.Mushroom._extract_filters',
                side_effect=ValueError):
            link = "https://github.com/mozilla-services/kinto/issues/"
            app = self.make_app({'error_info_link': link,
                                 'readonly': False})
            response = app.get(self.sample_url,
                               headers=self.headers, status=500)
        self.assertFormattedError(
            response, 500, ERRORS.UNDEFINED, "Internal Server Error",
            "A programmatic error occured, developers have been informed.",
            link)

    def test_503_is_valid_formatted_error(self):
        with mock.patch(
                'kinto.tests.core.testapp.views.Mushroom._extract_filters',
                side_effect=httpexceptions.HTTPServiceUnavailable):
            response = self.app.get(self.sample_url,
                                    headers=self.headers, status=503)
        self.assertFormattedError(
            response, 503, ERRORS.BACKEND, "Service Unavailable",
            ("Service temporary unavailable "
             "due to overloading or maintenance, please retry later."))
        self.assertIn("Retry-After", response.headers)

    def test_503_can_have_custom_message(self):
        custom_503 = http_error(httpexceptions.HTTPServiceUnavailable(),
                                errno=ERRORS.BACKEND,
                                message="Unable to connect the server.")
        with mock.patch(
                'kinto.tests.core.testapp.views.Mushroom._extract_filters',
                side_effect=custom_503):
            response = self.app.get(self.sample_url,
                                    headers=self.headers, status=503)
        self.assertFormattedError(
            response, 503, ERRORS.BACKEND, "Service Unavailable",
            "Unable to connect the server.")

    def test_500_provides_traceback_on_server(self):
        mock_traceback = mock.patch('logging.traceback.print_exception')
        with mock.patch(
                'kinto.tests.core.testapp.views.Mushroom._extract_filters',
                side_effect=ValueError):
            with mock_traceback as mocked_traceback:
                self.app.get(self.sample_url, headers=self.headers, status=500)
                self.assertTrue(mocked_traceback.called)
                self.assertEqual(ValueError,
                                 mocked_traceback.call_args[0][0])


class RedirectViewTest(FormattedErrorMixin, BaseWebTest, unittest.TestCase):
    api_prefix = ''

    def test_do_not_redirect_to_version_if_not_supported_version(self):
        resp = self.app.get('/v1/', status=404)
        self.assertFormattedError(
            resp, 404, ERRORS.VERSION_NOT_AVAILABLE, "Not Found",
            "The requested protocol version is not available "
            "on this server.")

    def test_redirect_to_version(self):
        # GET on the hello view.
        response = self.app.get('/')
        self.assertEqual(response.status_int, 307)
        self.assertEqual(response.location,
                         'http://localhost/v0/')

        # GET on the fields view.
        response = self.app.get('/mushrooms')
        self.assertEqual(response.status_int, 307)
        self.assertEqual(response.location,
                         'http://localhost/v0/mushrooms')

    def test_do_not_redirect_to_version_if_disabled_in_settings(self):
        # GET on the hello view.
        app = self.make_app({'version_prefix_redirect_enabled': False})
        app.get('/', status=404)

    def test_querystring_is_preserved_during_redirection(self):
        response = self.app.get('/home/articles?_since=42')
        self.assertEqual(response.location,
                         'http://localhost/v0/home/articles?_since=42')


class TrailingSlashRedirectViewTest(FormattedErrorMixin, BaseWebTest,
                                    unittest.TestCase):
    def test_doesnt_redirect_the_home_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_int, 200)

    def test_does_redirect_the_version_prefix(self):
        response = self.app.get('')
        self.assertEqual(response.status_int, 307)
        self.assertEqual(response.location,
                         'http://localhost/v0/')

    def test_it_redirects_if_it_ends_with_a__slash_(self):
        response = self.app.get('/mushrooms/')
        self.assertEqual(response.status_int, 307)
        self.assertEqual(response.location,
                         'http://localhost/v0/mushrooms')

    def test_do_not_redirect_if_disabled_in_settings(self):
        app = self.make_app({'trailing_slash_redirect_enabled': False})
        app.get('/', status=200)
        app.get('/mushrooms/', status=404)

    def test_querystring_is_preserved_during_redirection(self):
        response = self.app.get('/home/articles/?_since=42')
        self.assertEqual(response.location,
                         'http://localhost/v0/home/articles?_since=42')

    def test_it_does_not_redirect_if_the_url_exists(self):
        self.app.get('/static/', status=200)

    def test_display_an_error_message_if_disabled_in_settings(self):
        app = self.make_app({'trailing_slash_redirect_enabled': False})
        response = app.get('', status=404)
        self.assertFormattedError(
            response, 404, ERRORS.MISSING_RESOURCE, "Not Found",
            "The resource you are looking for could not be found.")
