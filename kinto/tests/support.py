try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

import webtest
from cliquet import utils
from cliquet.tests import support as cliquet_support


class BaseWebTest(cliquet_support.FakeAuthentMixin):

    app = webtest.TestApp("config:config/kinto.ini",
                          relative_to='.')

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.app.RequestClass = cliquet_support.get_request_class(prefix="v0")
        self.db = self.app.app.registry.storage
        self.db.initialize_schema()
        self.headers.update({
            'Content-Type': 'application/json',
        })

    def tearDown(self):
        super(BaseWebTest, self).tearDown()
        self.db.flush()


def get_user_headers(user):
    credentials = "%s:secret" % user
    authorization = 'Basic {0}'.format(utils.encode64(credentials))
    return {
        'Authorization': authorization
    }
