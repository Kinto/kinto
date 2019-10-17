import unittest
from unittest import mock

from kinto.core.permission import PermissionBase
from kinto.core.permission import memory as memory_backend
from kinto.core.permission import postgresql as postgresql_backend
from kinto.core.permission.testing import PermissionTest
from kinto.core.testing import skip_if_no_postgresql
from kinto.core.utils import sqlalchemy


class PermissionBaseTest(unittest.TestCase):
    def setUp(self):
        self.permission = PermissionBase()

    def test_mandatory_overrides(self):
        calls = [
            (self.permission.initialize_schema,),
            (self.permission.flush,),
            (self.permission.add_user_principal, "", ""),
            (self.permission.remove_user_principal, "", ""),
            (self.permission.remove_principal, ""),
            (self.permission.get_user_principals, ""),
            (self.permission.add_principal_to_ace, "", "", ""),
            (self.permission.remove_principal_from_ace, "", "", ""),
            (self.permission.get_object_permission_principals, "", ""),
            (self.permission.get_objects_permissions, ""),
            (self.permission.replace_object_permissions, "", {}),
            (self.permission.delete_object_permissions, ""),
            (self.permission.get_accessible_objects, [], ""),
            (self.permission.get_authorized_principals, []),
        ]
        for call in calls:
            self.assertRaises(NotImplementedError, *call)


class MemoryPermissionTest(PermissionTest, unittest.TestCase):
    backend = memory_backend

    def test_backend_error_is_raised_anywhere(self):
        pass

    def test_ping_returns_false_if_unavailable(self):
        pass

    def test_ping_logs_error_if_unavailable(self):
        pass


@skip_if_no_postgresql
class PostgreSQLPermissionTest(PermissionTest, unittest.TestCase):
    backend = postgresql_backend
    settings = {
        "permission_backend": "kinto.core.permission.postgresql",
        "permission_pool_size": 10,
        "permission_url": "postgresql://postgres:postgres@localhost:5432/testdb",
    }

    def setUp(self):
        super().setUp()
        self.client_error_patcher = [
            mock.patch.object(
                self.permission.client,
                "session_factory",
                side_effect=sqlalchemy.exc.SQLAlchemyError,
            )
        ]
