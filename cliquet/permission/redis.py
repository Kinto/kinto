from __future__ import absolute_import

from collections import defaultdict

from cliquet.permission import PermissionBase
from cliquet.storage.redis import create_from_config, wrap_redis_error


class Permission(PermissionBase):
    """Permission backend implementation using Redis.

    Enable in configuration::

        cliquet.permission_backend = cliquet.permission.redis

    *(Optional)* Instance location URI can be customized::

        cliquet.permission_url = redis://localhost:6379/2

    A threaded connection pool is enabled by default::

        cliquet.permission_pool_size = 50

    :noindex:
    """

    def __init__(self, client, *args, **kwargs):
        super(Permission, self).__init__(*args, **kwargs)
        self._client = client

    @property
    def settings(self):
        return dict(self._client.connection_pool.connection_kwargs)

    def initialize_schema(self):
        # Nothing to do.
        pass

    def _decode_set(self, results):
        return set([r.decode('utf-8') for r in results])

    @wrap_redis_error
    def flush(self):
        self._client.flushdb()

    @wrap_redis_error
    def add_user_principal(self, user_id, principal):
        user_key = 'user:%s' % user_id
        self._client.sadd(user_key, principal)

    @wrap_redis_error
    def remove_user_principal(self, user_id, principal):
        user_key = 'user:%s' % user_id
        self._client.srem(user_key, principal)
        if self._client.scard(user_key) == 0:
            self._client.delete(user_key)

    def remove_principal(self, principal):
        with self._client.pipeline() as pipe:
            user_keys = self._client.scan_iter(match='user:*')
            for user_key in user_keys:
                pipe.srem(user_key, principal)
            pipe.execute()

    @wrap_redis_error
    def user_principals(self, user_id):
        user_key = 'user:%s' % user_id
        return self._decode_set(self._client.smembers(user_key))

    @wrap_redis_error
    def add_principal_to_ace(self, object_id, permission, principal):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        self._client.sadd(permission_key, principal)

    @wrap_redis_error
    def remove_principal_from_ace(self, object_id, permission, principal):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        self._client.srem(permission_key, principal)
        if self._client.scard(permission_key) == 0:
            self._client.delete(permission_key)

    @wrap_redis_error
    def object_permission_principals(self, object_id, permission):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        members = self._client.smembers(permission_key)
        return self._decode_set(members)

    @wrap_redis_error
    def principals_accessible_objects(self, principals, permission,
                                      object_id_match=None,
                                      get_bound_permissions=None):
        if object_id_match is None:
            object_id_match = '*'

        if get_bound_permissions is None:
            def get_bound_permissions(object_id, permission):
                return [(object_id, permission)]

        keys = get_bound_permissions(object_id_match, permission)
        keys = ['permission:%s:%s' % key for key in keys
                if key[0].endswith(object_id_match)]
        principals = set(principals)
        objects = set()
        for key_pattern in keys:
            matched = self._client.scan_iter(match=key_pattern)
            for key in matched:
                authorized = self._decode_set(self._client.smembers(key))
                if len(authorized & principals) > 0:
                    object_id = key.decode('utf-8').split(':')[1]
                    objects.add(object_id)

        return objects

    @wrap_redis_error
    def object_permission_authorized_principals(self, object_id, permission,
                                                get_bound_permissions=None):
        if get_bound_permissions is None:
            def get_bound_permissions(object_id, permission):
                return [(object_id, permission)]

        keys = get_bound_permissions(object_id, permission)
        keys = ['permission:%s:%s' % key for key in keys]
        if keys:
            return self._decode_set(self._client.sunion(*list(keys)))
        return set()

    @wrap_redis_error
    def object_permissions(self, object_id, permissions=None):
        if permissions is not None:
            keys = ['permission:%s:%s' % (object_id, permission)
                    for permission in permissions]
        else:
            keys = [key.decode('utf-8') for key in self._client.scan_iter(
                match='permission:%s:*' % object_id)]

        with self._client.pipeline() as pipe:
            for permission_key in keys:
                pipe.smembers(permission_key)

            results = pipe.execute()

        permissions = defaultdict(set)
        for i, result in enumerate(results):
            permission = keys[i].split(':', 2)[-1]
            permissions[permission] = self._decode_set(result)

        return permissions

    @wrap_redis_error
    def replace_object_permissions(self, object_id, permissions):
        keys = ['permission:%s:%s' % (object_id, permission)
                for permission in permissions]
        with self._client.pipeline() as pipe:
            for key in keys:
                pipe.delete(key)
                permission = key.split(':', 2)[-1]
                principals = permissions[permission]
                if len(principals) > 0:
                    pipe.sadd(key, *principals)
            pipe.execute()

    @wrap_redis_error
    def delete_object_permissions(self, *object_id_list):
        with self._client.pipeline() as pipe:
            for object_id in object_id_list:
                keys = list(self._client.scan_iter(
                    match='permission:%s:*' % object_id))
                if len(keys) > 0:
                    pipe.delete(*keys)
            pipe.execute()


def load_from_config(config):
    client = create_from_config(config, prefix='permission_')
    return Permission(client)
