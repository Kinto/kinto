try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

import webtest

from cliquet.tests.support import FakeAuthentMixin
from kinto import API_VERSION


def get_request_class(prefix):

    class PrefixedRequestClass(webtest.app.TestRequest):

        @classmethod
        def blank(cls, path, *args, **kwargs):
            path = '/%s%s' % (prefix, path)
            return webtest.app.TestRequest.blank(path, *args, **kwargs)

    return PrefixedRequestClass


class BaseWebTest(FakeAuthentMixin):
    """Base Web Test to test your cornice service.

    It setups the database before each test and delete it after.
    """

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.app = webtest.TestApp("config:config/kinto.ini",
                                   relative_to='.')
        self.app.RequestClass = get_request_class(prefix=API_VERSION)
        self.db = self.app.app.registry.storage
        self.headers.update({
            'Content-Type': 'application/json',
        })

    def tearDown(self):
        super(BaseWebTest, self).tearDown()
        self.db.flush()
