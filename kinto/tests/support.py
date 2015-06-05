try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

import webtest
from cliquet import utils
from cliquet.tests import support as cliquet_support


class BaseWebTest(object):

    app = webtest.TestApp("config:config/kinto.ini",
                          relative_to='.')

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.app.RequestClass = cliquet_support.get_request_class(prefix="v1")
        self.storage = self.app.app.registry.storage
        self.storage.initialize_schema()
        self.headers = {
            'Content-Type': 'application/json',
        }
        self.headers.update(get_user_headers('mat'))

    def tearDown(self):
        super(BaseWebTest, self).tearDown()
        self.storage.flush()


def get_user_headers(user):
    credentials = "%s:secret" % user
    authorization = 'Basic {0}'.format(utils.encode64(credentials))
    return {
        'Authorization': authorization
    }
