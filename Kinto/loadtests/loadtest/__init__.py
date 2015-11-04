import json
import os
import uuid

from requests.auth import HTTPBasicAuth, AuthBase
from loads.case import TestCase
from konfig import Config


class RawAuth(AuthBase):
    def __init__(self, authorization):
        self.authorization = authorization

    def __call__(self, r):
        r.headers['Authorization'] = self.authorization
        return r


class BaseLoadTest(TestCase):
    def __init__(self, *args, **kwargs):
        """Initialization that happens once per user.

        :note:

            This method is called as many times as number of users.
        """
        super(BaseLoadTest, self).__init__(*args, **kwargs)

        self.conf = self._get_configuration()

        if self.conf.get('smoke', False):
            self.random_user = "test@restmail.net"
            self.auth = RawAuth("Bearer %s" % self.conf.get('token'))
        else:
            self.random_user = uuid.uuid4().hex
            self.auth = HTTPBasicAuth(self.random_user, 'secret')

        self.session.auth = self.auth
        self.session.headers.update({'Content-Type': 'application/json'})

        self.bucket = 'default'
        self.collection = 'default'

        # Keep track of created objects.
        self._collections_created = {}

    def _get_configuration(self):
        # Loads is removing the extra information contained in the ini files,
        # so we need to parse it again.
        config_file = self.config['config']
        # When copying the configuration files, we lose the config/ prefix so,
        # try to read from this folder in case the file doesn't exist.
        if not os.path.isfile(config_file):
            config_file = os.path.basename(config_file)
            if not os.path.isfile(config_file):
                msg = 'Unable to locate the configuration file, aborting.'
                raise LookupError(msg)
        return Config(config_file).get_map('loads')

    def api_url(self, path):
        url = "{0}/v1/{1}".format(self.server_url.rstrip('/'), path)
        return url

    def bucket_url(self, bucket=None, prefix=True):
        url = 'buckets/%s' % (bucket or self.bucket)
        return self.api_url(url) if prefix else '/' + url

    def group_url(self, bucket=None, group=None, prefix=True):
        bucket_url = self.bucket_url(bucket, prefix)
        group = group or self.group
        return '%s/groups/%s' % (bucket_url, group)

    def collection_url(self, bucket=None, collection=None, prefix=True):
        bucket_url = self.bucket_url(bucket, prefix)
        collection = collection or self.collection
        collection_url = bucket_url + '/collections/%s' % collection

        # Create collection objects.
        if collection not in self._collections_created:
            self.session.put(bucket_url,
                             data=json.dumps({'data': {}}),
                             headers={'If-None-Match': '*'})
            self.session.put(collection_url,
                             data=json.dumps({'data': {}}),
                             headers={'If-None-Match': '*'})
            self._collections_created[collection] = True

        return collection_url + '/records'

    def record_url(self, record_id, bucket=None, collection=None, prefix=True):
        collection_url = self.collection_url(bucket, collection, prefix)
        return collection_url + '/%s' % record_id
