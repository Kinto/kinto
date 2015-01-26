from fxa import errors as fxa_errors
import mock

from readinglist.errors import ERRORS

from .support import BaseWebTest, unittest


class ErrorViewTest(BaseWebTest, unittest.TestCase):

    def test_backoff_header(self):
        with mock.patch.dict(
                self.app.app.registry.settings,
                [('readinglist.backoff', '10')]):
            response = self.app.get('/articles',
                                    headers=self.headers, status=200)
            self.assertIn('Backoff', response.headers)
            self.assertEquals(response.headers['Backoff'],
                              '10'.encode('utf-8'))

    def test_404_is_valid_formatted_error(self):
        response = self.app.get('/unknown', status=404)
        self.assertFormattedError(
            response, 404, ERRORS.MISSING_RESOURCE, "Not Found",
            "The resource your are looking for could not be found.")

    def test_401_is_valid_formatted_error(self):
        response = self.app.get('/articles', status=401)
        self.assertFormattedError(
            response, 401, ERRORS.MISSING_AUTH_TOKEN, "Unauthorized",
            "Please authenticate yourself to use this endpoint.")

    def test_403_is_valid_formatted_error(self):
        with mock.patch(
                'readinglist.authentication.AuthorizationPolicy.permits',
                return_value=False):
            response = self.app.get('/articles',
                                    headers=self.headers, status=403)
        self.assertFormattedError(
            response, 403, ERRORS.FORBIDDEN, "Forbidden",
            "This user cannot access this resource.")

    def test_500_is_valid_formatted_error(self):
        with mock.patch('traceback.format_exc', return_value="") as mock_err:
            with mock.patch('readinglist.views.article.Article.collection_get',
                            side_effect=ValueError):
                response = self.app.get('/articles',
                                        headers=self.headers, status=500)
        mock_err.assert_called_once_with()
        self.assertFormattedError(
            response, 500, ERRORS.UNDEFINED, "Internal Server Error",
            "A programmatic error occured, developers have been informed.",
            "https://github.com/mozilla-services/readinglist/issues/")

    def test_503_is_valid_formatted_error(self):
        self.fxa_verify.side_effect = fxa_errors.OutOfProtocolError
        response = self.app.get('/articles', headers=self.headers, status=503)
        self.assertFormattedError(
            response, 503, ERRORS.BACKEND, "Service unavailable",
            "Service unavailable due to high load, please retry later.")
        self.assertIn("Retry-After", response.headers)
