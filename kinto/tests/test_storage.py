import mock

import requests
from cliquet.storage import exceptions
from cliquet.tests.test_storage import StorageTest

from kinto import storage
from kinto.tests.support import unittest


class CloudStorageTest(StorageTest, unittest.TestCase):
    backend = storage
    settings = {
        'cliquet.storage_url': 'http://localhost:8888'
    }

    def setUp(self):
        super(CloudStorageTest, self).setUp()
        self.client_error_patcher = mock.patch.object(
            self.storage._client,
            'request',
            side_effect=requests.ConnectionError)

    def test_raises_backenderror_when_remote_returns_500(self):
        with mock.patch.object(self.storage._client, 'request') as mocked:
            error_response = requests.models.Response()
            error_response.status_code = 500
            error_response._content_consumed = True
            error_response._content = u'Internal Error'.encode('utf8')
            mocked.return_value = error_response
            self.assertRaises(exceptions.BackendError,
                              self.storage.get_all,
                              **self.storage_kw)

    def test_returns_backend_error_when_batch_has_error_in_responses(self):
        batch_responses = {
            'responses': [
                {'status': 400}
            ]
        }
        rules = [[Filter('number', 1, utils.COMPARISON.GT)]]
        with mock.patch.object(self.storage._client, 'post') as mocked:
            response_body = mock.Mock(return_value=batch_responses)
            mocked.return_value = mock.MagicMock(json=response_body)
            self.assertRaises(exceptions.BackendError,
                              self.storage.get_all,
                              limit=5, pagination_rules=rules,
                              **self.storage_kw)
