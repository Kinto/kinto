import mock
import unittest

from kinto.core.utils import sqlalchemy
from kinto.core.permission import (memory as memory_backend,
                                   postgresql as postgresql_backend)
from kinto.core.permission.testing import BaseTestPermission
from kinto.core.testing import skip_if_no_postgresql


class MemoryPermissionTest(BaseTestPermission, unittest.TestCase):
    backend = memory_backend

    def test_backend_error_is_raised_anywhere(self):
        pass

    def test_ping_returns_false_if_unavailable(self):
        pass

    def test_ping_logs_error_if_unavailable(self):
        pass


@skip_if_no_postgresql
class PostgreSQLPermissionTest(BaseTestPermission, unittest.TestCase):
    backend = postgresql_backend
    settings = {
        'permission_backend': 'kinto.core.permission.postgresql',
        'permission_pool_size': 10,
        'permission_url': 'postgres://postgres:postgres@localhost:5432/testdb'
    }

    def setUp(self):
        super(PostgreSQLPermissionTest, self).setUp()
        self.client_error_patcher = [mock.patch.object(
            self.permission.client,
            'session_factory',
            side_effect=sqlalchemy.exc.SQLAlchemyError)]
