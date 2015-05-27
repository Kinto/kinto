import mock

# import psycopg2
import redis

from cliquet.storage import exceptions
from cliquet.permission import (PermissionBase, redis as redis_backend,
                                memory as memory_backend)

from .support import unittest


class PermissionBaseTest(unittest.TestCase):
    def setUp(self):
        self.permission = PermissionBase()

    def test_mandatory_overrides(self):
        calls = [
            (self.permission.initialize_schema,),
            (self.permission.flush,),
            (self.permission.add_user_principal, '', ''),
            (self.permission.remove_user_principal, '', ''),
            (self.permission.get_user_principals, ''),
            (self.permission.add_object_permission_principal, '', '', ''),
            (self.permission.remove_object_permission_principal, '', '', ''),
            (self.permission.get_object_permission_principals, '', ''),
            (self.permission.has_permission, '', '', '')
        ]
        for call in calls:
            self.assertRaises(NotImplementedError, *call)


class BaseTestPermission(object):
    backend = None
    settings = {}

    def __init__(self, *args, **kwargs):
        super(BaseTestPermission, self).__init__(*args, **kwargs)
        self.permission = self.backend.load_from_config(self._get_config())
        self.permission.initialize_schema()
        self.request = None
        self.client_error_patcher = []

    def _get_config(self, settings=None):
        """Mock Pyramid config object.
        """
        if settings is None:
            settings = self.settings
        return mock.Mock(get_settings=mock.Mock(return_value=settings))

    def tearDown(self):
        mock.patch.stopall()
        super(BaseTestPermission, self).tearDown()
        self.permission.flush()

    def test_backend_error_is_raised_anywhere(self):
        for patch in self.client_error_patcher:
            patch.start()
        calls = [
            (self.permission.flush,),
            (self.permission.add_user_principal, '', ''),
            (self.permission.remove_user_principal, '', ''),
            (self.permission.get_user_principals, ''),
            (self.permission.add_object_permission_principal, '', '', ''),
            (self.permission.remove_object_permission_principal, '', '', ''),
            (self.permission.get_object_permission_principals, '', ''),
            (self.permission.has_permission, '', '', ''),
        ]
        for call in calls:
            try:
                self.assertRaises(exceptions.BackendError, *call)
            except:
                print call[0]
                raise

    def test_ping_returns_false_if_unavailable(self):
        for patch in self.client_error_patcher:
            patch.start()
        self.assertFalse(self.permission.ping(self.request))

    def test_ping_returns_true_if_available(self):
        self.assertTrue(self.permission.ping(self.request))

    def test_add_a_principal_to_a_user(self):
        user_id = 'foo'
        principal = 'bar'
        self.permission.add_user_principal(user_id, principal)
        retrieved = self.permission.get_user_principals(user_id)
        self.assertEquals(retrieved, set([user_id, principal]))

    def test_remove_a_principal_for_a_user(self):
        user_id = 'foo'
        principal = 'bar'
        principal2 = 'foobar'
        self.permission.add_user_principal(user_id, principal)
        self.permission.add_user_principal(user_id, principal2)
        self.permission.remove_user_principal(user_id, principal)
        retrieved = self.permission.get_user_principals(user_id)
        self.assertEquals(retrieved, set([user_id, principal2]))

    def test_add_a_principal_to_an_object_permission(self):
        object_id = 'foo'
        permission = 'write'
        principal = 'bar'
        self.permission.add_object_permission_principal(object_id, permission,
                                                        principal)
        retrieved = self.permission.get_object_permission_principals(
            object_id, permission)
        self.assertEquals(retrieved, set([principal]))

    def test_remove_a_principal_from_an_object_permission(self):
        object_id = 'foo'
        permission = 'write'
        principal = 'bar'
        principal2 = 'foobar'
        self.permission.add_object_permission_principal(object_id, permission,
                                                        principal)
        self.permission.add_object_permission_principal(object_id, permission,
                                                        principal2)
        self.permission.remove_object_permission_principal(object_id,
                                                           permission,
                                                           principal)
        retrieved = self.permission.get_object_permission_principals(
            object_id, permission)
        self.assertEquals(retrieved, set([principal2]))

    def test_userid_has_permission(self):
        object_id = 'foo'
        permission = 'write'
        principal = 'bar'
        self.permission.add_object_permission_principal(object_id, permission,
                                                        principal)
        has_permission = self.permission.has_permission(object_id, permission,
                                                        principal)
        self.assertTrue(has_permission)

    def test_userid_group_has_permission(self):
        object_id = 'foo'
        permission = 'write'
        group_id = 'bar'
        user_id = 'foobar'
        self.permission.add_user_principal(user_id, group_id)
        self.permission.add_object_permission_principal(object_id, permission,
                                                        group_id)
        has_permission = self.permission.has_permission(object_id, permission,
                                                        user_id)
        self.assertTrue(has_permission)

    def test_object_inherit_userid_permissions(self):
        object_id = 'foo'
        permissions = [(object_id, 'write'), (object_id, 'read')]
        user_id = 'bar'
        self.permission.add_object_permission_principal(object_id, 'write',
                                                        user_id)
        self.permission.has_permission(
            object_id, 'read', user_id,
            lambda object_id, permission: permissions)


class MemoryPermissionTest(BaseTestPermission, unittest.TestCase):
    backend = memory_backend

    def test_backend_error_is_raised_anywhere(self):
        pass

    def test_ping_returns_false_if_unavailable(self):
        pass


class RedisPermissionTest(BaseTestPermission, unittest.TestCase):
    backend = redis_backend
    settings = {
        'cliquet.permission_url': '',
        'cliquet.permission_pool_size': 10
    }

    def __init__(self, *args, **kwargs):
        super(RedisPermissionTest, self).__init__(*args, **kwargs)
        self.client_error_patcher = [
            mock.patch.object(
                self.permission._client,
                'execute_command',
                side_effect=redis.RedisError),
            mock.patch.object(
                self.permission._client,
                'pipeline',
                side_effect=redis.RedisError)]


# class PostgreSQLPermissionTest(BaseTestPermission, unittest.TestCase):
#     backend = postgresql_backend
#     settings = {
#         'cliquet.permission_pool_size': 10,
#         'cliquet.permission_url':
#             'postgres://postgres:postgres@localhost:5432/testdb'
#     }
#
#     def __init__(self, *args, **kwargs):
#         super(PostgreSQLPermissionTest, self).__init__(*args, **kwargs)
#         self.client_error_patcher = [mock.patch.object(
#             self.permission.pool,
#             'getconn',
#             side_effect=psycopg2.DatabaseError)]
