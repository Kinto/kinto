import mock

from pyramid.request import Request

from kinto.core import utils
from kinto.core.authorization import RouteFactory, AuthorizationPolicy, groupfinder
from kinto.core.storage import exceptions as storage_exceptions
from kinto.core.testing import DummyRequest, unittest


class RouteFactoryTest(unittest.TestCase):

    def setUp(self):
        self.record_uri = "/foo/bar"

    def assert_request_resolves_to(self, method, permission, uri=None,
                                   record_not_found=False):
        if uri is None:
            uri = self.record_uri

        with mock.patch('kinto.core.utils.current_service') as current_service:
            # Patch current service.
            resource = mock.MagicMock()
            resource.record_id = 1
            if record_not_found:
                resource.model.get_record.side_effect = \
                    storage_exceptions.RecordNotFoundError
            else:
                resource.model.get_record.return_value = 1
            current_service().resource.return_value = resource

            # Do the actual call.
            request = DummyRequest(method=method)
            request.upath_info = uri
            context = RouteFactory(request)

            self.assertEquals(context.required_permission, permission)

    def test_http_unknown_does_not_raise_a_500(self):
        self.assert_request_resolves_to("unknown", None)

    def test_http_get_resolves_in_a_read_permission(self):
        self.assert_request_resolves_to("get", "read")

    def test_http_post_resolves_in_a_create_permission(self):
        self.assert_request_resolves_to("post", "create")

    def test_http_delete_resolves_in_a_write_permission(self):
        self.assert_request_resolves_to("delete", "write")

    def test_http_put_unexisting_record_resolves_in_a_create_permission(self):
        with mock.patch('kinto.core.utils.current_service') as current_service:
            # Patch current service.
            resource = mock.MagicMock()
            resource.record_id = 1
            resource.model.get_record.side_effect = \
                storage_exceptions.RecordNotFoundError
            current_service().resource.return_value = resource
            current_service().collection_path = '/buckets/{bucket_id}'
            # Do the actual call.
            request = DummyRequest(method='put')
            request.upath_info = '/buckets/abc/collections/1'
            request.matchdict = {'bucket_id': 'abc'}
            context = RouteFactory(request)

            self.assertEquals(context.required_permission, 'create')

    def test_http_put_existing_record_resolves_in_a_write_permission(self):
        self.assert_request_resolves_to("put", "write")

    def test_http_put_sets_current_record_attribute(self):
        with mock.patch('kinto.core.utils.current_service') as current_service:
            # Patch current service.
            resource = mock.MagicMock()
            resource.record_id = 1
            resource.model.get_record.return_value = mock.sentinel.record
            current_service().resource.return_value = resource
            # Do the actual call.
            request = DummyRequest(method='put')
            context = RouteFactory(request)
            self.assertEquals(context.current_record, mock.sentinel.record)

    def test_http_patch_resolves_in_a_write_permission(self):
        self.assert_request_resolves_to("patch", "write")

    def test_attributes_are_none_with_blank_requests(self):
        request = Request.blank(path='/')
        request.registry = mock.Mock(settings={})
        request.authn_type = 'fxa'
        request.prefixed_userid = property(utils.prefixed_userid)
        context = RouteFactory(request)
        self.assertIsNone(context.required_permission)
        self.assertIsNone(context.current_record)
        self.assertIsNone(context.resource_name)

    def test_attributes_are_none_with_non_resource_requests(self):
        basic_service = object()
        request = Request.blank(path='/')
        request.prefixed_userid = property(utils.prefixed_userid)
        request.matched_route = mock.Mock(pattern='foo')
        request.registry = mock.Mock(cornice_services={'foo': basic_service})
        request.registry.settings = {}

        context = RouteFactory(request)
        self.assertIsNone(context.current_record)
        self.assertIsNone(context.required_permission)
        self.assertIsNone(context.resource_name)

    def test_fetch_shared_records_uses_pattern_if_on_collection(self):
        request = DummyRequest()
        request.route_path.return_value = '/v1/buckets/%2A'
        service = mock.MagicMock()
        service.type = 'collection'
        with mock.patch('kinto.core.authorization.utils.current_service') as m:
            m.return_value = service
            context = RouteFactory(request)
        self.assertTrue(context.on_collection)

        context.fetch_shared_records('read', ['userid'], None)

        request.registry.permission.get_accessible_objects.assert_called_with(
            ['userid'],
            [('/buckets/*', 'read')],
            with_children=False)

    def test_fetch_shared_records_uses_get_bound_permission_callback(self):
        request = DummyRequest()
        service = mock.MagicMock()
        request.route_path.return_value = '/v1/buckets/%2A'
        service.type = 'collection'
        with mock.patch('kinto.core.authorization.utils.current_service') as m:
            m.return_value = service
            context = RouteFactory(request)
        self.assertTrue(context.on_collection)

        # Define a callback where write means read:
        def get_bound_perms(obj_id, perm):
            return [(obj_id, 'write'), (obj_id, 'read')]

        context.fetch_shared_records('read', ['userid'], get_bound_perms)

        request.registry.permission.get_accessible_objects.assert_called_with(
            ['userid'],
            [('/buckets/*', 'write'), ('/buckets/*', 'read')],
            with_children=False)

    def test_fetch_shared_records_sets_shared_ids_from_results(self):
        request = DummyRequest()
        context = RouteFactory(request)
        request.registry.permission.get_accessible_objects.return_value = {
            '/obj/1': ['read', 'write'],
            '/obj/3': ['obj:create']
        }
        context.fetch_shared_records('read', ['userid'], None)
        self.assertEquals(sorted(context.shared_ids), ['1', '3'])

    def test_fetch_shared_records_sets_shared_ids_if_empty(self):
        request = DummyRequest()
        context = RouteFactory(request)
        request.registry.permission.get_accessible_objects.return_value = {}

        context.fetch_shared_records('read', ['userid'], None)

        self.assertEqual(context.shared_ids, [])


class AuthorizationPolicyTest(unittest.TestCase):
    def setUp(self):
        self.authz = AuthorizationPolicy()
        self.context = mock.MagicMock()
        self.context.permission_object_id = '/articles/43/comments/2'
        self.context.required_permission = 'read'
        self.principals = ["portier:yourself"]
        self.context.get_prefixed_principals.return_value = self.principals
        self.permission = 'dynamic'

    def test_permits_does_not_refer_to_context_if_permission_is_private(self):
        self.assertFalse(self.authz.permits(None, [], 'private'))

    def test_permits_return_if_authenticated_when_permission_is_private(self):
        self.assertTrue(self.authz.permits(None,
                                           ['system.Authenticated'],
                                           'private'))

    def test_permits_logs_authz_failures(self):
        self.context.on_collection = False
        self.context.check_permission.return_value = False
        with mock.patch('kinto.core.authorization.logger') as mocked:
            self.authz.permits(self.context, self.principals, 'dynamic')
        userid = 'portier:yourself'
        object_id = '/articles/43/comments/2'
        perm = 'read'
        mocked.warn.assert_called_with('Permission %r on %r not granted to %r.',
                                       perm, object_id, userid,
                                       extra=dict(perm=perm, uri=object_id, userid=userid))

    def test_permits_refers_to_context_to_check_permissions(self):
        self.context.check_permission.return_value = True
        allowed = self.authz.permits(self.context, self.principals, 'dynamic')
        self.assertTrue(allowed)

    def test_permits_refers_to_context_to_check_permission_principals(self):
        self.context.check_permission.return_value = False
        allowed = self.authz.permits(
            self.context, self.principals, 'dynamic')
        self.assertTrue(allowed)

    def test_permits_reads_the_context_when_permission_is_dynamic(self):
        self.authz.permits(self.context, self.principals, 'dynamic')
        self.context.check_permission.assert_called_with(
            self.principals,
            [(self.context.permission_object_id, 'read')])

    def test_permits_uses_get_bound_permissions_if_defined(self):
        self.authz.get_bound_permissions = lambda o, p: mock.sentinel.callback
        self.authz.permits(self.context, self.principals, 'dynamic')
        self.context.check_permission.assert_called_with(
            self.principals,
            mock.sentinel.callback)

    def test_permits_calls_get_bound_permissions_with_context_info(self):
        self.authz.get_bound_permissions = mock.Mock(return_value=[])
        self.authz.permits(self.context, self.principals, 'dynamic')
        self.authz.get_bound_permissions.assert_called_with(
            self.context.permission_object_id,
            'read')

    def test_permits_consider_permission_when_not_dynamic(self):
        self.authz.permits(self.context, self.principals, 'foobar')
        self.context.check_permission.assert_called_with(
            self.principals,
            [(self.context.permission_object_id, 'foobar')])

    def test_permits_prepend_obj_type_to_permission_on_create(self):
        self.context.required_permission = 'create'
        self.context.resource_name = 'record'
        self.authz.permits(self.context, self.principals, 'dynamic')
        self.context.check_permission.assert_called_with(
            self.principals,
            [(self.context.permission_object_id, 'record:create')])

    def test_permits_takes_route_factory_allowed_principals_into_account(self):
        self.context.resource_name = 'record'
        self.context.required_permission = 'create'
        self.context._settings = {'record_create_principals': 'fxa:user'}
        allowed = self.authz.permits(self.context, self.principals, 'dynamic')
        self.context._check_permission.assert_not_called()
        self.assertTrue(allowed)


class GuestAuthorizationPolicyTest(unittest.TestCase):
    def setUp(self):
        self.authz = AuthorizationPolicy()
        self.authz.get_bound_permissions = lambda o, p: []
        self.request = DummyRequest(method='GET')
        self.context = RouteFactory(self.request)
        self.context.on_collection = True
        self.context.check_permission = mock.Mock(return_value=False)

    def test_permits_returns_true_if_collection_and_shared_records(self):
        self.context.fetch_shared_records = mock.MagicMock(return_value=[
            'record1', 'record2'])
        allowed = self.authz.permits(self.context, ['userid'], 'dynamic')
        # Note: we use the list of principals from request.prefixed_principals
        self.context.fetch_shared_records.assert_called_with(
            'read',
            ['basicauth:bob', 'system.Everyone', 'system.Authenticated'],
            self.authz.get_bound_permissions)
        self.assertTrue(allowed)

    def test_permits_does_not_return_true_if_not_collection(self):
        self.context.on_collection = False
        allowed = self.authz.permits(self.context, ['userid'], 'dynamic')
        self.assertFalse(allowed)

    def test_permits_does_not_return_true_if_not_list_operation(self):
        self.context.required_permission = 'create'
        allowed = self.authz.permits(self.context, ['userid'], 'dynamic')
        self.assertFalse(allowed)
        allowed = self.authz.permits(self.context, ['userid'], 'create')
        self.assertFalse(allowed)

    def test_permits_returns_false_if_collection_is_unknown(self):
        self.context.fetch_shared_records = mock.MagicMock(return_value=None)
        allowed = self.authz.permits(self.context, ['userid'], 'dynamic')
        # Note: we use the list of principals from request.prefixed_principals
        self.context.fetch_shared_records.assert_called_with(
            'read',
            ['basicauth:bob', 'system.Everyone', 'system.Authenticated'],
            self.authz.get_bound_permissions)
        self.assertFalse(allowed)

    def test_perm_object_id_is_naive_if_no_record_path_exists(self):
        def route_path(service_name, **kwargs):
            # Simulate a resource that has no record_path (only list).
            if service_name == 'article-record':
                raise KeyError
            return '/comments/sub/{id}'.format_map(kwargs)

        self.request.route_path.side_effect = route_path

        self.request.path = '/comments'
        self.context.resource_name = 'comment'
        obj_id = self.context.get_permission_object_id(self.request, '*')
        self.assertEquals(obj_id, '/comments/sub/*')

        self.request.path = '/articles'
        self.context.resource_name = 'article'
        obj_id = self.context.get_permission_object_id(self.request, '*')
        self.assertEquals(obj_id, '/articles/*')


class GroupFinderTest(unittest.TestCase):
    def setUp(self):
        self.request = DummyRequest(method='GET')

    def test_uses_prefixed_as_userid(self):
        self.request.prefixed_userid = 'basic:bob'
        groupfinder('bob', self.request)
        self.request.registry.permission.get_user_principals.assert_called_with('basic:bob')

    def test_uses_provided_id_if_no_prefixed_userid(self):
        self.request.prefixed_userid = None
        groupfinder('bob', self.request)
        self.request.registry.permission.get_user_principals.assert_called_with('bob')
