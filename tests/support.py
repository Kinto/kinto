from kinto.core import testing
from kinto import main as kinto_main
from kinto import DEFAULT_SETTINGS


MINIMALIST_BUCKET = {}
MINIMALIST_COLLECTION = {}
MINIMALIST_GROUP = {'data': dict(members=['fxa:user'])}
MINIMALIST_RECORD = {'data': dict(name="Hulled Barley",
                                  type="Whole Grain")}
USER_PRINCIPAL = 'basicauth:8a931a10fc88ab2f6d1cc02a07d3a81b5d4768f6f13e85c5' \
                 'd8d4180419acb1b4'


class BaseWebTest(testing.BaseWebTest):

    api_prefix = "v1"
    entry_point = kinto_main
    principal = USER_PRINCIPAL

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.headers.update(testing.get_user_headers('mat'))

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = {**DEFAULT_SETTINGS}
        if extras is not None:
            settings.update(extras)
        settings = super().get_app_settings(extras=settings)
        return settings

    def create_group(self, bucket_id, group_id, members=None):
        if members is None:
            group = MINIMALIST_GROUP
        else:
            group = {'data': {'members': members}}
        group_url = '/buckets/{}/groups/{}'.format(bucket_id, group_id)
        self.app.put_json(group_url, group,
                          headers=self.headers, status=201)

    def create_bucket(self, bucket_id):
        self.app.put_json('/buckets/{}'.format(bucket_id), MINIMALIST_BUCKET,
                          headers=self.headers, status=201)
