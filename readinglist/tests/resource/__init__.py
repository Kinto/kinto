import mock

from cornice import errors as cornice_errors

from readinglist.backend.memory import Memory
from readinglist.tests.support import unittest
from readinglist.resource import BaseResource


class BaseTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BaseTest, self).__init__(*args, **kwargs)
        self.db = Memory()

    def setUp(self):
        self.resource = BaseResource(self.get_request())

    def get_request(self):
        request = mock.MagicMock(headers={})
        request.db = self.db
        request.errors = cornice_errors.Errors()
        request.authenticated_userid = 'bob'
        request.validated = {}
        request.matchdict = {}
        request.response = mock.MagicMock(headers={})
        return request

    @property
    def last_response(self):
        return self.resource.request.response
