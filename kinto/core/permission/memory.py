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

    def get_user_principals(self, user_id):
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

    def get_object_permission_principals(self, object_id, permission):
        permission_key = 'permission:%s:%s' % (object_id, permission)
        members = self._store.get(permission_key, set())
        return members

    def get_accessible_objects(self, principals, bound_permissions=None):
        principals = set(principals)
        if bound_permissions is not None:
            bound_permissions = [(re.compile(obj_id.replace('*', '.*')), perm)
                                 for (obj_id, perm) in bound_permissions]

        if bound_permissions is None:
            candidates = self._store.items()
        else:
            candidates = []
            for obj_id, perm in bound_permissions:
                for key, value in self._store.items():
                    if key.endswith(perm):
                        object_id = key.split(':')[1]
                        if obj_id.match(object_id):
                            candidates.append((obj_id, perm, value))

        perms_by_object_id = {}
        for object_id, perm, value in candidates:
            if len(principals & value) > 0:
                perms_by_object_id.setdefault(object_id, set()).add(perm)
        return perms_by_object_id

    def get_authorized_principals(self, bound_permissions):
        principals = set()
        for obj_id, perm in bound_permissions:
            principals |= self.get_object_permission_principals(obj_id, perm)
        return principals

    def get_object_permissions(self, object_id, permissions=None):
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
