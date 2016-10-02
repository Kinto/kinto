import os

import webtest
from kinto.core import utils as core_utils
try:
    from kinto.core import testing as core_support
except ImportError:
    # Kinto < 4.0
    from kinto.tests.core import support as core_support


def get_user_headers(user):
    credentials = "%s:secret" % user
    authorization = 'Basic {0}'.format(core_utils.encode64(credentials))
    return {
        'Authorization': authorization
    }


class BaseWebTest(object):
    config = '../../config/kinto.ini'

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.app = self.make_app()

    def make_app(self):
        curdir = os.path.dirname(os.path.realpath(__file__))
        app = webtest.TestApp("config:%s" % self.config, relative_to=curdir)
        app.RequestClass = core_support.get_request_class(prefix="v1")
        return app
