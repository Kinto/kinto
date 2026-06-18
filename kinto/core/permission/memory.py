import re
from collections.abc import Iterable
from typing import Any

from pyramid.config import Configurator

from kinto.core.decorators import synchronized
from kinto.core.permission import PermissionBase


class Permission(PermissionBase):
    """Permission backend implementation in local process memory.

    Enable in configuration::

        kinto.permission_backend = kinto.core.permission.memory

    :noindex:
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flush()

    def initialize_schema(self, dry_run: bool = False) -> None:
        # Nothing to do.
        pass

    def flush(self) -> None:
        self._store: dict[str, set[str]] = {}

    @synchronized
    def add_user_principal(self, user_id: str, principal: str) -> None:
        user_key = f"user:{user_id}"
        user_principals = self._store.get(user_key, set())
        user_principals.add(principal)
        self._store[user_key] = user_principals

    @synchronized
    def remove_user_principal(self, user_id: str, principal: str) -> None:
        user_key = f"user:{user_id}"
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

    @synchronized
    def remove_principal(self, principal: str) -> None:
        for key, user_principals in self._store.items():
            if not key.startswith("user:"):
                continue
            try:
                user_principals.remove(principal)
            except KeyError:
                pass

    @synchronized
    def get_user_principals(self, user_id: str) -> set[str]:
        # Fetch the groups the user is in.
        user_key = f"user:{user_id}"
        members = self._store.get(user_key, set())
        # Fetch the groups system.Authenticated is in.
        group_authenticated = self._store.get("user:system.Authenticated", set())
        return members | group_authenticated

    @synchronized
    def add_principal_to_ace(self, object_id: str, permission: str, principal: str) -> None:
        permission_key = f"permission:{object_id}:{permission}"
        object_permission_principals = self._store.get(permission_key, set())
        object_permission_principals.add(principal)
        self._store[permission_key] = object_permission_principals

    @synchronized
    def remove_principal_from_ace(self, object_id: str, permission: str, principal: str) -> None:
        permission_key = f"permission:{object_id}:{permission}"
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

    @synchronized
    def get_object_permission_principals(self, object_id: str, permission: str) -> set[str]:
        permission_key = f"permission:{object_id}:{permission}"
        members = self._store.get(permission_key, set())
        return members

    @synchronized
    def get_accessible_objects(
        self,
        principals: Iterable[str],
        bound_permissions: list[tuple[str, str]] | None = None,
        with_children: bool = True,
    ) -> dict[str, set[str]]:
        principals = set(principals)
        candidates = []
        if bound_permissions is None:
            for key, value in self._store.items():
                if key.startswith("permission:"):
                    _, object_id, permission = key.split(":", 2)
                    candidates.append((object_id, permission, value))
        else:
            for pattern, perm in bound_permissions:
                id_match = ".*" if with_children else "[^/]+"
                regexp = re.compile(f"^{pattern.replace('*', id_match)}$")
                for key, value in self._store.items():
                    if key.endswith(perm):
                        object_id = key.split(":")[1]
                        if regexp.match(object_id):
                            candidates.append((object_id, perm, value))

        perms_by_object_id = {}
        for object_id, perm, value in candidates:
            if len(principals & value) > 0:
                perms_by_object_id.setdefault(object_id, set()).add(perm)
        return perms_by_object_id

    @synchronized
    def get_authorized_principals(self, bound_permissions: list[tuple[str, str]]) -> set[str]:
        principals = set()
        for obj_id, perm in bound_permissions:
            principals |= self.get_object_permission_principals(obj_id, perm)
        return principals

    @synchronized
    def get_objects_permissions(
        self, objects_ids: list[str], permissions: list[str] | None = None
    ) -> list[dict[str, set[str]]]:
        result = []
        for object_id in objects_ids:
            if permissions is None:
                aces = [k for k in self._store.keys() if k.startswith(f"permission:{object_id}:")]
            else:
                aces = [f"permission:{object_id}:{permission}" for permission in permissions]
            perms = {}
            for ace in aces:
                # Should work with 'permission:/url/id:object:create'.
                permission = ace.split(":", 2)[2]
                perms[permission] = set(self._store[ace])
            result.append(perms)
        return result

    @synchronized
    def replace_object_permissions(
        self, object_id: str, permissions: dict[str, Any]
    ) -> dict[str, Any]:
        for permission, principals in permissions.items():
            permission_key = f"permission:{object_id}:{permission}"
            if permission_key in self._store and len(principals) == 0:
                del self._store[permission_key]
            elif principals:
                self._store[permission_key] = set(principals)
        return permissions

    @synchronized
    def delete_object_permissions(self, *object_id_list: str) -> None:
        to_delete = []
        for key in self._store.keys():
            object_id = key.split(":")[1]
            for pattern in object_id_list:
                regexp = re.compile(f"^{pattern.replace('*', '.*')}$")
                if regexp.match(object_id):
                    to_delete.append(key)
        for k in to_delete:
            del self._store[k]


def load_from_config(config: Configurator) -> Permission:
    return Permission()
