try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

import webtest
from kinto.core import utils
from kinto.tests.core import support as core_support
from kinto import main as testapp
from kinto import DEFAULT_SETTINGS


MINIMALIST_BUCKET = {}
MINIMALIST_COLLECTION = {}
MINIMALIST_GROUP = {'data': dict(members=['fxa:user'])}
MINIMALIST_RECORD = {'data': dict(name="Hulled Barley",
                                  type="Whole Grain")}
USER_PRINCIPAL = 'basicauth:3a0c56d278def4113f38d0cfff6db1b06b84fcc4384ee890' \
                 'cf7bbaa772317e10'


class BaseWebTest(object):

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.principal = USER_PRINCIPAL
        self.app = self._get_test_app()
        self.storage = self.app.app.registry.storage
        self.permission = self.app.app.registry.permission
        self.cache = self.app.app.registry.cache
        self.storage.initialize_schema()
        self.permission.initialize_schema()
        self.cache.initialize_schema()
        self.headers = {
            'Content-Type': 'application/json',
        }
        self.headers.update(get_user_headers('mat'))

    def _get_test_app(self, settings=None):
        app = webtest.TestApp(testapp({}, **self.get_app_settings(settings)))
        app.RequestClass = core_support.get_request_class(prefix="v1")
        return app

    def get_app_settings(self, additional_settings=None):
        settings = core_support.DEFAULT_SETTINGS.copy()
        settings.update(**DEFAULT_SETTINGS)
        settings['cache_backend'] = 'kinto.core.cache.memory'
        settings['storage_backend'] = 'kinto.core.storage.memory'
        settings['permission_backend'] = 'kinto.core.permission.memory'
        settings['userid_hmac_secret'] = "this is not a secret"
        settings['includes'] = "kinto.plugins.default_bucket"

        if additional_settings is not None:
            settings.update(additional_settings)
        return settings

    def tearDown(self):
        super(BaseWebTest, self).tearDown()
        self.storage.flush()
        self.cache.flush()
        self.permission.flush()

    def create_group(self, bucket_id, group_id, members=None):
        if members is None:
            group = MINIMALIST_GROUP
        else:
            group = {'data': {'members': members}}
        group_url = '/buckets/%s/groups/%s' % (bucket_id, group_id)
        self.app.put_json(group_url, group,
                          headers=self.headers, status=201)

    def create_bucket(self, bucket_id):
        self.app.put_json('/buckets/%s' % bucket_id, MINIMALIST_BUCKET,
                          headers=self.headers, status=201)


def get_user_headers(user):
    credentials = "%s:secret" % user
    authorization = 'Basic {0}'.format(utils.encode64(credentials))
    return {
        'Authorization': authorization
    }
