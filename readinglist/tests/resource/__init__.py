from readinglist.storage.memory import Memory
from readinglist.tests.support import unittest, DummyRequest
from readinglist.resource import BaseResource


class BaseTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BaseTest, self).__init__(*args, **kwargs)
        self.db = Memory()

    def setUp(self):
        self.resource = BaseResource(self.get_request())

    def get_request(self):
        request = DummyRequest()
        request.db = self.db
        return request

    @property
    def last_response(self):
        return self.resource.request.response
