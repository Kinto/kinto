import re

from kinto.core.permission import PermissionBase


class Permission(PermissionBase):
    """Permission backend implementation in local thread memory.

    Enable in configuration::

        kinto.permission_backend = kinto.core.permission.memory

    :noindex:
    """

    def __init__(self, *args, **kwargs):
        super(Permission, self).__init__(*args, **kwargs)
        self.flush()

    def initialize_schema(self):
        # Nothing to do.
        pass

    def flush(self):
        self._store = {}

    def add_user_principal(self, user_id, principal):
        user_key = 'user:%s' % user_id
        user_principals = self._store.get(user_key, set())
        user_principals.add(principal)
        self._store[user_key] = user_principals

    def remove_user_principal(self, user_id, principal):
        user_key = 'user:%s' % user_id
        user_principals = self._store.get(user_key, set())
        try:
            user_principals.remove(principal)
        except KeyError:
            pass
        if len(user_principals) == 0:
            if user_key in self._store:
                del self._store[user_key]
        else:
            self._store[user_key] = user_principals

    def remove_principal(self, principal):
        for user_principals in self._store.values():
            try:
                user_principals.remove(principal)
            except KeyError:
                pass

    def user_principals(self, user_id):
        user_key = 'user:%s' % user_id
        members = self._store.get(user_key, set())
        return members

    def add_principal_to_ace(self, object_id, permission, principal):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        object_permission_principals = self._store.get(permission_key, set())
        object_permission_principals.add(principal)
        self._store[permission_key] = object_permission_principals

    def remove_principal_from_ace(self, object_id, permission, principal):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        object_permission_principals = self._store.get(permission_key, set())
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
        members = self._store.get(permission_key, set())
        return members

    def principals_accessible_objects(self, principals, permission,
                                      object_id_match=None,
                                      get_bound_permissions=None):
        principals = set(principals)
        if object_id_match is None:
            object_id_match = '*'

        if get_bound_permissions is None:
            object_id_match = object_id_match.replace('*', '.*')
            keys = [(re.compile(object_id_match), permission)]
        else:
            keys = get_bound_permissions(object_id_match, permission)
            keys = [(re.compile(obj_id.replace('*', '.*')), p) for (obj_id, p)
                    in keys if obj_id.endswith(object_id_match)]

        objects = set()
        for obj_id, perm in keys:
            for key, value in self._store.items():
                if key.endswith(perm):
                    if len(principals & value) > 0:
                        object_id = key.split(':')[1]
                        if obj_id.match(object_id):
                            objects.add(object_id)
        return objects

    def object_permission_authorized_principals(self, object_id, permission,
                                                get_bound_permissions=None):
        if get_bound_permissions is None:
            keys = [(object_id, permission)]
        else:
            keys = get_bound_permissions(object_id, permission)
        principals = set()
        for obj_id, perm in keys:
            principals |= self.object_permission_principals(obj_id, perm)
        return principals

    def object_permissions(self, object_id, permissions=None):
        if permissions is None:
            aces = [k for k in self._store.keys()
                    if k.startswith('permission:%s' % object_id)]
        else:
            aces = ['permission:%s:%s' % (object_id, permission)
                    for permission in permissions]
        permissions = {}
        for ace in aces:
            # Should work with stuff like 'permission:/url/id:record:create'.
            permission = ace.split(':', 2)[2]
            permissions[permission] = set(self._store[ace])
        return permissions

    def replace_object_permissions(self, object_id, permissions):
        for permission, principals in permissions.items():
            permission_key = 'permission:%s:%s' % (object_id, permission)
            if permission_key in self._store and len(principals) == 0:
                del self._store[permission_key]
            else:
                self._store[permission_key] = set(principals)
        return permissions

    def delete_object_permissions(self, *object_id_list):
        to_delete = []
        for key in self._store.keys():
            object_id = key.split(':')[1]
            if object_id in object_id_list:
                to_delete.append(key)
        for k in to_delete:
            del self._store[k]


def load_from_config(config):
    return Permission()
