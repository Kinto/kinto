import mock

import redis
from pyramid import testing

from kinto.core.utils import sqlalchemy
from kinto.core.storage import exceptions
from kinto.core.permission import (PermissionBase, redis as redis_backend,
                                   memory as memory_backend,
                                   postgresql as postgresql_backend, heartbeat)

from .support import unittest, skip_if_no_postgresql, DummyRequest


class PermissionBaseTest(unittest.TestCase):
    def setUp(self):
        self.permission = PermissionBase()

    def test_mandatory_overrides(self):
        calls = [
            (self.permission.initialize_schema,),
            (self.permission.flush,),
            (self.permission.add_user_principal, '', ''),
            (self.permission.remove_user_principal, '', ''),
            (self.permission.remove_principal, ''),
            (self.permission.user_principals, ''),
            (self.permission.add_principal_to_ace, '', '', ''),
            (self.permission.remove_principal_from_ace, '', '', ''),
            (self.permission.object_permission_principals, '', ''),
            (self.permission.object_permissions, ''),
            (self.permission.replace_object_permissions, '', {}),
            (self.permission.delete_object_permissions, ''),
            (self.permission.principals_accessible_objects, [], ''),
            (self.permission.object_permission_authorized_principals, '', ''),
        ]
        for call in calls:
            self.assertRaises(NotImplementedError, *call)


class BaseTestPermission(object):
    backend = None
    settings = {}

    def setUp(self):
        super(BaseTestPermission, self).setUp()
        self.permission = self.backend.load_from_config(self._get_config())
        self.permission.initialize_schema()
        self.request = DummyRequest()
        self.client_error_patcher = []

    def _get_config(self, settings=None):
        """Mock Pyramid config object.
        """
        if settings is None:
            settings = self.settings
        config = testing.setUp()
        config.add_settings(settings)
        return config

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
            (self.permission.user_principals, ''),
            (self.permission.add_principal_to_ace, '', '', ''),
            (self.permission.remove_principal_from_ace, '', '', ''),
            (self.permission.object_permission_principals, '', ''),
            (self.permission.object_permissions, ''),
            (self.permission.replace_object_permissions, '', {'write': []}),
            (self.permission.delete_object_permissions, ''),
            (self.permission.principals_accessible_objects, [], ''),
            (self.permission.object_permission_authorized_principals, '', ''),
        ]
        for call in calls:
            self.assertRaises(exceptions.BackendError, *call)

    def test_ping_returns_false_if_unavailable(self):
        ping = heartbeat(self.permission)
        for patch in self.client_error_patcher:
            patch.start()
        self.assertFalse(ping(self.request))

    def test_ping_returns_true_if_available(self):
        ping = heartbeat(self.permission)
        self.assertTrue(ping(self.request))

    def test_ping_returns_false_if_unavailable_in_readonly_mode(self):
        self.request.registry.settings['readonly'] = 'true'
        ping = heartbeat(self.permission)
        with mock.patch.object(self.permission, 'user_principals',
                               side_effect=exceptions.BackendError("Boom!")):
            self.assertFalse(ping(self.request))

    def test_ping_returns_true_if_available_in_readonly_mode(self):
        self.request.registry.settings['readonly'] = 'true'
        ping = heartbeat(self.permission)
        self.assertTrue(ping(self.request))

    def test_ping_logs_error_if_unavailable(self):
        for patch in self.client_error_patcher:
            patch.start()
        ping = heartbeat(self.permission)

        with mock.patch('kinto.core.permission.logger.exception') as \
                exc_handler:
            self.assertFalse(ping(self.request))

        self.assertTrue(exc_handler.called)

    def test_can_add_a_principal_to_a_user(self):
        user_id = 'foo'
        principal = 'bar'
        self.permission.add_user_principal(user_id, principal)
        retrieved = self.permission.user_principals(user_id)
        self.assertEquals(retrieved, {principal})

    def test_add_twice_a_principal_to_a_user_add_it_once(self):
        user_id = 'foo'
        principal = 'bar'
        self.permission.add_user_principal(user_id, principal)
        self.permission.add_user_principal(user_id, principal)
        retrieved = self.permission.user_principals(user_id)
        self.assertEquals(retrieved, {principal})

    def test_can_remove_a_principal_for_a_user(self):
        user_id = 'foo'
        principal = 'bar'
        principal2 = 'foobar'
        self.permission.add_user_principal(user_id, principal)
        self.permission.add_user_principal(user_id, principal2)
        self.permission.remove_user_principal(user_id, principal)
        retrieved = self.permission.user_principals(user_id)
        self.assertEquals(retrieved, {principal2})

    def test_can_remove_a_unexisting_principal_to_a_user(self):
        user_id = 'foo'
        principal = 'bar'
        principal2 = 'foobar'
        self.permission.add_user_principal(user_id, principal2)
        self.permission.remove_user_principal(user_id, principal)
        self.permission.remove_user_principal(user_id, principal2)
        retrieved = self.permission.user_principals(user_id)
        self.assertEquals(retrieved, set())

    def test_can_remove_principal_from_every_users(self):
        user_id1 = 'foo1'
        user_id2 = 'foo2'
        principal1 = 'bar'
        principal2 = 'foobar'
        self.permission.add_user_principal(user_id1, principal1)
        self.permission.add_user_principal(user_id2, principal1)
        self.permission.add_user_principal(user_id2, principal2)
        self.permission.remove_principal(principal1)
        self.permission.remove_principal('unknown')

        retrieved = self.permission.user_principals(user_id1)
        self.assertEquals(retrieved, set())
        retrieved = self.permission.user_principals(user_id2)
        self.assertEquals(retrieved, {principal2})

    def test_can_add_a_principal_to_an_object_permission(self):
        object_id = 'foo'
        permission = 'write'
        principal = 'bar'
        self.permission.add_principal_to_ace(object_id, permission, principal)
        retrieved = self.permission.object_permission_principals(
            object_id, permission)
        self.assertEquals(retrieved, {principal})

    def test_add_twice_a_principal_to_an_object_permission_add_it_once(self):
        object_id = 'foo'
        permission = 'write'
        principal = 'bar'
        self.permission.add_principal_to_ace(object_id, permission, principal)
        self.permission.add_principal_to_ace(object_id, permission, principal)
        retrieved = self.permission.object_permission_principals(
            object_id, permission)
        self.assertEquals(retrieved, {principal})

    def test_can_remove_a_principal_from_an_object_permission(self):
        object_id = 'foo'
        permission = 'write'
        principal = 'bar'
        principal2 = 'foobar'
        self.permission.add_principal_to_ace(object_id, permission, principal)
        self.permission.add_principal_to_ace(object_id, permission, principal2)
        self.permission.remove_principal_from_ace(object_id, permission,
                                                  principal)
        retrieved = self.permission.object_permission_principals(
            object_id, permission)
        self.assertEquals(retrieved, {principal2})

    def test_principals_is_empty_if_no_permission(self):
        object_id = 'foo'
        permission = 'write'
        principal = 'bar'
        self.permission.add_principal_to_ace(object_id, permission, principal)
        self.permission.remove_principal_from_ace(object_id, permission,
                                                  principal)
        retrieved = self.permission.object_permission_principals(
            object_id, permission)
        self.assertEquals(retrieved, set())

    def test_can_remove_an_unexisting_principal_to_an_object_permission(self):
        object_id = 'foo'
        permission = 'write'
        principal = 'bar'
        principal2 = 'foobar'
        self.permission.add_principal_to_ace(object_id, permission, principal2)
        self.permission.remove_principal_from_ace(object_id, permission,
                                                  principal)
        retrieved = self.permission.object_permission_principals(
            object_id, permission)
        self.assertEquals(retrieved, {principal2})

    def test_check_permission_returns_true_for_userid(self):
        object_id = 'foo'
        permission = 'write'
        principal = 'bar'
        self.permission.add_principal_to_ace(object_id, permission, principal)
        check_permission = self.permission.check_permission(
            object_id, permission, {principal})
        self.assertTrue(check_permission)

    def test_check_permission_returns_true_for_userid_group(self):
        object_id = 'foo'
        permission = 'write'
        group_id = 'bar'
        user_id = 'foobar'
        self.permission.add_user_principal(user_id, group_id)
        self.permission.add_principal_to_ace(object_id, permission, group_id)
        check_permission = self.permission.check_permission(
            object_id, permission, {user_id, group_id})
        self.assertTrue(check_permission)

    def test_check_permission_returns_true_for_object_inherited(self):
        object_id = 'foo'
        permissions = [(object_id, 'write'), (object_id, 'read')]
        user_id = 'bar'
        self.permission.add_principal_to_ace(object_id, 'write',
                                                        user_id)
        check_permission = self.permission.check_permission(
            object_id, 'read', {user_id},
            lambda object_id, permission: permissions)
        self.assertTrue(check_permission)

    def test_object_permission_authorized_principals_inherit_principals(self):
        object_id = 'foo'
        permissions = [(object_id, 'write'), (object_id, 'read')]
        user_id = 'bar'
        self.permission.add_principal_to_ace(object_id, 'write',
                                                        user_id)
        principals = self.permission.object_permission_authorized_principals(
            object_id, 'read', lambda object_id, permission: permissions)
        self.assertEquals(principals, {user_id})

    def test_object_permission_authorized_principals_handles_empty_set(self):
        object_id = 'foo'
        permissions = set()
        user_id = 'bar'
        self.permission.add_principal_to_ace(object_id, 'write', user_id)
        principals = self.permission.object_permission_authorized_principals(
            object_id, 'read', lambda object_id, permission: permissions)
        self.assertEquals(principals, set())

    def test_check_permissions_handles_empty_set(self):
        object_id = 'foo'
        permissions = set()
        principal = 'bar'
        self.permission.add_principal_to_ace(object_id, 'write', principal)
        permits = self.permission.check_permission(
            object_id, 'read', {principal},
            lambda object_id, permission: permissions)
        self.assertFalse(permits)

    def test_check_permission_return_false_for_unknown_principal(self):
        object_id = 'foo'
        permission = 'write'
        principal = 'bar'
        check_permission = self.permission.check_permission(
            object_id, permission, {principal})
        self.assertFalse(check_permission)

    def test_obtain_object_ids_from_principals_and_permission(self):
        self.permission.add_principal_to_ace('id1', 'write', 'user1')
        self.permission.add_principal_to_ace('id1', 'read', 'user1')
        self.permission.add_principal_to_ace('id1', 'read', 'group')
        self.permission.add_principal_to_ace('id2', 'write', 'user1')
        self.permission.add_principal_to_ace('id2', 'read', 'user2')
        self.permission.add_principal_to_ace('id2', 'read', 'group')
        self.permission.add_principal_to_ace('id3', 'read', 'user2')
        object_ids = self.permission.principals_accessible_objects(['user1',
                                                                    'group'],
                                                                   'read')
        self.assertEquals(object_ids, set(['id1', 'id2']))

    def test_obtain_object_ids_can_be_filtered_with_pattern(self):
        self.permission.add_principal_to_ace('/url1/id', 'write', 'user1')
        self.permission.add_principal_to_ace('/url2/id', 'write', 'user1')
        object_ids = self.permission.principals_accessible_objects(
            ['user1'],
            'write',
            object_id_match='*url1*')
        self.assertEquals(object_ids, set(['/url1/id']))

    def test_obtain_object_ids_with_get_bound_permissions(self):
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user1')
        self.permission.add_principal_to_ace('/url/a/id/2', 'read', 'user1')
        self.permission.add_principal_to_ace('/url/_/id/2', 'read', 'user1')
        object_ids = self.permission.principals_accessible_objects(
            ['user1'],
            'read',
            object_id_match='/url/a/id/*',
            get_bound_permissions=lambda o, p: [('/url/a/id/*', 'read'),
                                                ('/url/a/id/*', 'write')])
        self.assertEquals(object_ids, set(['/url/a/id/1', '/url/a/id/2']))

    def test_obtain_object_ids_with_get_bound_permissions_without_match(self):
        self.permission.add_principal_to_ace('/url/a', 'write', 'user1')
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user1')
        self.permission.add_principal_to_ace('/url/b/id/1', 'write', 'user1')
        self.permission.add_principal_to_ace('/url/a/id/2', 'read', 'user1')
        self.permission.add_principal_to_ace('/url/b/id/2', 'read', 'user1')
        object_ids = self.permission.principals_accessible_objects(
            ['user1'],
            'read',
            get_bound_permissions=lambda o, p: [('/url/a', 'write'),
                                                ('/url/a', 'read'),
                                                ('/url/a/id/*', 'write'),
                                                ('/url/a/id/*', 'read')])
        self.assertEquals(object_ids, set(['/url/a/id/1', '/url/a/id/2']))

    def test_object_permissions_return_all_object_acls(self):
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user1')
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user2')
        self.permission.add_principal_to_ace('/url/a/id/1', 'read', 'user3')
        self.permission.add_principal_to_ace('/url/a/id/1', 'obj:del', 'user1')
        object_permissions = self.permission.object_permissions('/url/a/id/1')
        self.assertDictEqual(object_permissions, {
            "write": {"user1", "user2"},
            "read": {"user3"},
            "obj:del": {"user1"}
        })

    def test_object_permissions_return_listed_object_acls(self):
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user1')
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user2')
        self.permission.add_principal_to_ace('/url/a/id/1', 'read', 'user3')
        self.permission.add_principal_to_ace('/url/a/id/1', 'create', 'user1')
        object_permissions = self.permission.object_permissions(
            '/url/a/id/1', ['write', 'read'])
        self.assertDictEqual(object_permissions, {
            "write": {"user1", "user2"},
            "read": {"user3"}
        })

    def test_object_permissions_return_empty_dict(self):
        self.assertDictEqual(self.permission.object_permissions('abc'), {})

    def test_replace_object_permission_replace_all_given_sets(self):
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user1')
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user2')
        self.permission.add_principal_to_ace('/url/a/id/1', 'read', 'user3')
        self.permission.add_principal_to_ace('/url/a/id/1', 'update', 'user1')
        self.permission.add_principal_to_ace('/url/a/id/1', 'obj:del', 'user1')

        self.permission.replace_object_permissions('/url/a/id/1', {
            "write": ["user1"],
            "read": ["user2"],
            "update": [],
            "obj:del": ["user1"],
            "new": ["user3"]
        })

        object_permissions = self.permission.object_permissions('/url/a/id/1')
        self.assertDictEqual(object_permissions, {
            "write": {"user1"},
            "read": {"user2"},
            "obj:del": {"user1"},
            "new": {"user3"}
        })

    def test_replace_object_permission_only_replace_given_sets(self):
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user1')
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user2')
        self.permission.add_principal_to_ace('/url/a/id/1', 'read', 'user3')
        self.permission.add_principal_to_ace('/url/a/id/1', 'obj:del', 'user1')

        self.permission.replace_object_permissions('/url/a/id/1', {
            "write": ["user1"],
            "new": set(["user2"])
        })

        object_permissions = self.permission.object_permissions('/url/a/id/1')
        self.assertDictEqual(object_permissions, {
            "write": {"user1"},
            "read": {"user3"},
            "new": {"user2"},
            "obj:del": {"user1"}
        })

    def test_replace_object_permission_supports_empty_input(self):
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user1')
        self.permission.replace_object_permissions('/url/a/id/1', {})
        object_permissions = self.permission.object_permissions('/url/a/id/1')
        self.assertDictEqual(object_permissions, {
            "write": {"user1"}
        })

    def test_replace_object_permission_supports_duplicated_entries(self):
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user1')
        self.permission.replace_object_permissions('/url/a/id/1', {
            "write": ["user1", "user1"]
        })
        object_permissions = self.permission.object_permissions('/url/a/id/1')
        self.assertDictEqual(object_permissions, {
            "write": {"user1"}
        })

    def test_replace_object_permission_supports_empty_list(self):
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user1')
        self.permission.replace_object_permissions('/url/a/id/1', {
            "write": set()
        })
        object_permissions = self.permission.object_permissions('/url/a/id/1')
        self.assertEqual(len(object_permissions), 0)

    def test_delete_object_permissions_remove_all_given_objects_acls(self):
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user1')
        self.permission.add_principal_to_ace('/url/a/id/1', 'write', 'user2')
        self.permission.add_principal_to_ace('/url/a/id/1', 'read', 'user3')
        self.permission.add_principal_to_ace('/url/a/id/1', 'create', 'user1')
        self.permission.add_principal_to_ace('/url/a/id/2', 'create', 'user3')
        self.permission.add_principal_to_ace('/url/a/id/3', 'create', 'user4')

        self.permission.delete_object_permissions('/url/a/id/1',
                                                  '/url/a/id/2')

        self.assertDictEqual(self.permission.object_permissions(
            '/url/a/id/1'), {})
        self.assertDictEqual(self.permission.object_permissions(
            '/url/a/id/2'), {})
        self.assertDictEqual(self.permission.object_permissions(
            '/url/a/id/3'), {"create": {"user4"}})

    def test_delete_object_permissions_supports_empty_list(self):
        self.permission.delete_object_permissions()  # Not failing


class MemoryPermissionTest(BaseTestPermission, unittest.TestCase):
    backend = memory_backend

    def test_backend_error_is_raised_anywhere(self):
        pass

    def test_ping_returns_false_if_unavailable(self):
        pass

    def test_ping_logs_error_if_unavailable(self):
        pass


class RedisPermissionTest(BaseTestPermission, unittest.TestCase):
    backend = redis_backend
    settings = {
        'permission_url': '',
        'permission_pool_size': 10
    }

    def setUp(self):
        super(RedisPermissionTest, self).setUp()
        self.client_error_patcher = [
            mock.patch.object(
                self.permission._client,
                'execute_command',
                side_effect=redis.RedisError),
            mock.patch.object(
                self.permission._client,
                'pipeline',
                side_effect=redis.RedisError)]

    def test_config_is_taken_in_account(self):
        config = testing.setUp(settings=self.settings)
        config.add_settings({'permission_url': 'redis://:pass@db.loc:1234/5'})
        backend = self.backend.load_from_config(config)
        self.assertDictEqual(
            backend.settings,
            {'host': 'db.loc', 'password': 'pass', 'db': 5, 'port': 1234})


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
