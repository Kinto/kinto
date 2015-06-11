try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

import webtest
from cliquet import utils
from cliquet.tests import support as cliquet_support


MINIMALIST_BUCKET = dict()
MINIMALIST_COLLECTION = dict()
MINIMALIST_GROUP = dict(members=['fxa:user'])
MINIMALIST_RECORD = dict(name="Hulled Barley",
                         type="Whole Grain")
USER_PRINCIPAL = 'basicauth_967e5a9f60cbe491bd8a695d8d0515caba27c' \
                 '5c4f404a11ff86e14d3256d88b7'


class BaseWebTest(object):

    app = webtest.TestApp("config:config/kinto.ini",
                          relative_to='.')

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.app.RequestClass = cliquet_support.get_request_class(prefix="v1")
        self.principal = USER_PRINCIPAL
        self.storage = self.app.app.registry.storage
        self.permission = self.app.app.registry.permission
        self.permission.flush()
        self.storage.initialize_schema()
        self.headers = {
            'Content-Type': 'application/json',
        }
        self.headers.update(get_user_headers('mat'))

    def tearDown(self):
        super(BaseWebTest, self).tearDown()
        self.storage.flush()
        self.permission.flush()

    def add_permission(self, object_id, permission):
        self.permission.add_principal_to_ace(
            object_id, permission, self.principal)


def get_user_headers(user):
    credentials = "%s:secret" % user
    authorization = 'Basic {0}'.format(utils.encode64(credentials))
    return {
        'Authorization': authorization
    }
