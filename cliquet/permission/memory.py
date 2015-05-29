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

    def add_object_permission_principal(self, object_id, permission,
                                        principal):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        object_permission_principals = self._store.get(permission_key, set([]))
        object_permission_principals.add(principal)
        self._store[permission_key] = object_permission_principals

    def remove_object_permission_principal(self, object_id, permission,
                                           principal):
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

    def object_permission_authorized_principals(self, object_id, permission,
                                                _get_perm_keys=None):
        if _get_perm_keys is None:
            keys = [(object_id, permission)]
        else:
            keys = _get_perm_keys(object_id, permission)
        permissions = set([])
        for obj_id, perm in keys:
            permissions |= self.object_permission_principals(obj_id, perm)
        return permissions


def load_from_config(config):
    return Memory()
