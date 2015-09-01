import re

from cliquet.permission import PermissionBase


class Memory(PermissionBase):
    """Permission backend implementation in local thread memory.

    Enable in configuration::

        cliquet.permission_backend = cliquet.permission.memory

    :noindex:
    """

    def __init__(self, *args, **kwargs):
        super(Memory, self).__init__(*args, **kwargs)
        self.flush()

    def initialize_schema(self):
        # Nothing to do.
        pass

    def flush(self):
        self._store = {}

    def add_user_principal(self, user_id, principal):
        user_key = 'user:%s' % user_id
        user_principals = self._store.get(user_key, set([]))
        user_principals.add(principal)
        self._store[user_key] = user_principals

    def remove_user_principal(self, user_id, principal):
        user_key = 'user:%s' % user_id
        user_principals = self._store.get(user_key, set([]))
        try:
            user_principals.remove(principal)
        except KeyError:
            pass
        if len(user_principals) == 0:
            if user_key in self._store:
                del self._store[user_key]
        else:
            self._store[user_key] = user_principals

    def user_principals(self, user_id):
        user_key = 'user:%s' % user_id
        members = self._store.get(user_key, set([]))
        return members

    def add_principal_to_ace(self, object_id, permission, principal):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        object_permission_principals = self._store.get(permission_key, set([]))
        object_permission_principals.add(principal)
        self._store[permission_key] = object_permission_principals

    def remove_principal_from_ace(self, object_id, permission, principal):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        object_permission_principals = self._store.get(permission_key, set([]))
        try:
            object_permission_principals.remove(principal)
        except KeyError:
            pass
        if len(object_permission_principals) == 0:
            if permission_key in self._store:
                del self._store[permission_key]
        else:
            self._store[permission_key] = object_permission_principals

    def object_permission_principals(self, object_id, permission):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        members = self._store.get(permission_key, set([]))
        return members

    def principals_accessible_objects(self, principals, permission,
                                      object_id_match=None):
        if object_id_match is None:
            object_id_match = re.compile('.*')
        else:
            object_id_match = re.compile(object_id_match.replace('*', '.*'))
        objects = set([])
        for key, value in self._store.items():
            if key.endswith(permission):
                if len(set(principals) & value) > 0:
                    object_id = key.split(':')[1]
                    if object_id_match.match(object_id):
                        objects.add(object_id)
        return objects

    def object_permission_authorized_principals(self, object_id, permission,
                                                get_bound_permissions=None):
        if get_bound_permissions is None:
            keys = [(object_id, permission)]
        else:
            keys = get_bound_permissions(object_id, permission)
        principals = set([])
        for obj_id, perm in keys:
            principals |= self.object_permission_principals(obj_id, perm)
        return principals


def load_from_config(config):
    return Memory()
