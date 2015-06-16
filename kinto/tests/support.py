try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

import webtest
from cliquet import utils
from pyramid.security import IAuthorizationPolicy
from zope.interface import implementer
from cliquet.tests import support as cliquet_support
from kinto import main as testapp
from kinto import DEFAULT_SETTINGS


MINIMALIST_BUCKET = {'data': dict()}
MINIMALIST_COLLECTION = {'data': dict()}
MINIMALIST_GROUP = {'data': dict(members=['fxa:user'])}
MINIMALIST_RECORD = {'data': dict(name="Hulled Barley",
                                  type="Whole Grain")}
USER_PRINCIPAL = 'basicauth_8a931a10fc88ab2f6d1cc02a07d3a81b5d4768f' \
                 '6f13e85c5d8d4180419acb1b4'


class BaseWebTest(object):

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.principal = USER_PRINCIPAL
        self.app = self._get_test_app()
        self.storage = self.app.app.registry.storage
        self.permission = self.app.app.registry.permission
        self.permission.initialize_schema()
        self.storage.initialize_schema()
        self.headers = {
            'Content-Type': 'application/json',
        }
        self.headers.update(get_user_headers('mat'))

    def _get_test_app(self, settings=None):
        app = webtest.TestApp(testapp({}, **self.get_app_settings(settings)))
        app.RequestClass = cliquet_support.get_request_class(prefix="v1")
        return app

    def get_app_settings(self, additional_settings=None):
        settings = cliquet_support.DEFAULT_SETTINGS.copy()
        settings.update(**DEFAULT_SETTINGS)
        settings['cliquet.cache_backend'] = 'cliquet.cache.memory'
        settings['cliquet.storage_backend'] = 'cliquet.storage.memory'
        settings['cliquet.permission_backend'] = 'cliquet.permission.memory'
        settings['cliquet.project_name'] = 'cloud storage'
        settings['cliquet.project_docs'] = 'https://kinto.rtfd.org/'
        settings['multiauth.authorization_policy'] = (
            'kinto.tests.support.AllowAuthorizationPolicy')

        if additional_settings is not None:
            settings.update(additional_settings)
        return settings

    def tearDown(self):
        super(BaseWebTest, self).tearDown()
        self.storage.flush()
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


@implementer(IAuthorizationPolicy)
class AllowAuthorizationPolicy(object):
    def permits(self, context, principals, permission):
        if USER_PRINCIPAL in principals:
            return True
        return False

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError()  # PRAGMA NOCOVER


def get_user_headers(user):
    credentials = "%s:secret" % user
    authorization = 'Basic {0}'.format(utils.encode64(credentials))
    return {
        'Authorization': authorization
    }
