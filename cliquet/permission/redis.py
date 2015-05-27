from __future__ import absolute_import

import redis
from six.moves.urllib import parse as urlparse

from cliquet.permission import PermissionBase
from cliquet.storage.redis import wrap_redis_error


class Redis(PermissionBase):
    """Permission backend implementation using Redis.

    Enable in configuration::

        cliquet.permission_backend = cliquet.permission.redis

    *(Optional)* Instance location URI can be customized::

        cliquet.permission_url = redis://localhost:6379/2

    A threaded connection pool is enabled by default::

        cliquet.permission_pool_size = 50

    :noindex:
    """

    def __init__(self, *args, **kwargs):
        super(Redis, self).__init__(*args, **kwargs)
        maxconn = kwargs.pop('max_connections')
        connection_pool = redis.BlockingConnectionPool(max_connections=maxconn)
        self._client = redis.StrictRedis(connection_pool=connection_pool,
                                         **kwargs)

    def initialize_schema(self):
        # Nothing to do.
        pass

    @wrap_redis_error
    def flush(self):
        self._client.flushdb()

    @wrap_redis_error
    def add_user_principal(self, user_id, principal):
        user_key = 'user:%s' % user_id
        with self._client.pipeline() as multi:
            multi.sadd(user_key, principal)
            multi.sadd(user_key, user_id)
            multi.execute()

    @wrap_redis_error
    def remove_user_principal(self, user_id, principal):
        user_key = 'user:%s' % user_id
        self._client.srem(user_key, principal)
        if self._client.scard(user_key) <= 1:
            self._client.delete(user_key)

    @wrap_redis_error
    def get_user_principals(self, user_id):
        user_key = 'user:%s' % user_id
        members = self._client.smembers(user_key)
        return members

    @wrap_redis_error
    def add_object_permission_principal(self, object_id, permission,
                                        principal):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        self._client.sadd(permission_key, principal)

    @wrap_redis_error
    def remove_object_permission_principal(self, object_id, permission,
                                           principal):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        self._client.srem(permission_key, principal)
        if self._client.scard(permission_key) == 0:
            self._client.delete(permission_key)

    @wrap_redis_error
    def get_object_permission_principals(self, object_id, permission):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        members = self._client.smembers(permission_key)
        return members

    def _get_user_permission(self, object_id, permission, user_id,
                             _get_perm_keys=None):
        if _get_perm_keys is None:
            def _get_perm_keys(object_id, permission):
                return [(object_id, permission)]

        user_key = 'user:%s' % user_id
        temp_key = 'temp_permission:%s:%s' % (object_id, permission)

        keys = _get_perm_keys(object_id, permission)
        keys = ['permission:%s:%s' % key for key in keys]
        with self._client.pipeline() as multi:
            multi.sadd(user_key, user_id)  # results[0]
            if len(keys) == 1:
                multi.sinter(keys[0], user_key)  # results[1]
                results = multi.execute()
                return results[1]
            else:
                multi.sunionstore(temp_key, *list(keys))  # results[1]
                multi.sinter(temp_key, user_key)  # results[2]
                multi.delete(temp_key)  # results[3]
                results = multi.execute()
                return results[2]

    @wrap_redis_error
    def has_permission(self, object_id, permission, user_id,
                       _get_perm_keys=None):
        members = self._get_user_permission(object_id, permission, user_id,
                                            _get_perm_keys)
        return len(members) > 0


def load_from_config(config):
    settings = config.get_settings()
    uri = settings['cliquet.permission_url']
    uri = urlparse.urlparse(uri)
    pool_size = int(settings['cliquet.permission_pool_size'])

    return Redis(max_connections=pool_size,
                 host=uri.hostname or 'localhost',
                 port=uri.port or 6739,
                 password=uri.password or None,
                 db=int(uri.path[1:]) if uri.path else 0)
