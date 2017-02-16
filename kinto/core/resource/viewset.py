import functools
import warnings

import colander
from cornice.validators import colander_validator
from pyramid.settings import asbool

from kinto.core import authorization

from .schema import (PermissionsSchema, RequestSchema, PayloadRequestSchema,
                     PatchHeaderSchema, CollectionQuerySchema, CollectionGetQuerySchema,
                     RecordGetQuerySchema, RecordSchema, ResourceReponses,
                     ShareableResourseResponses)


CONTENT_TYPES = ["application/json"]

PATCH_CONTENT_TYPES = ["application/merge-patch+json"]


class StrictSchema(colander.MappingSchema):
    @staticmethod
    def schema_type():
        return colander.Mapping(unknown='raise')


class PartialSchema(colander.MappingSchema):
    @staticmethod
    def schema_type():
        return colander.Mapping(unknown='ignore')


class SimpleSchema(colander.MappingSchema):
    @staticmethod
    def schema_type():
        return colander.Mapping(unknown='preserve')


class ViewSet:
    """The default ViewSet object.

    A viewset contains all the information needed to register
    any resource in the Cornice registry.

    It provides the same features as ``cornice.resource()``, except
    that it is much more flexible and extensible.
    """
    service_name = "{resource_name}-{endpoint_type}"
    collection_path = "/{resource_name}s"
    record_path = "/{resource_name}s/{{id}}"

    collection_methods = ('GET', 'POST', 'DELETE')
    record_methods = ('GET', 'PUT', 'PATCH', 'DELETE')

    readonly_methods = ('GET', 'OPTIONS', 'HEAD')

    factory = authorization.RouteFactory

    responses = ResourceReponses()

    service_arguments = {
        'description': 'Collection of {resource_name}',
    }

    default_arguments = {
        'permission': authorization.PRIVATE,
        'accept': CONTENT_TYPES,
        'schema': RequestSchema(),
    }

    default_post_arguments = {
        "content_type": CONTENT_TYPES,
        'schema': PayloadRequestSchema(),
    }

    default_put_arguments = {
        "content_type": CONTENT_TYPES,
        'schema': PayloadRequestSchema(),
    }

    default_patch_arguments = {
        "content_type": CONTENT_TYPES + PATCH_CONTENT_TYPES,
        'schema': PayloadRequestSchema().bind(header=PatchHeaderSchema()),
    }

    default_collection_arguments = {
        'schema': RequestSchema().bind(querystring=CollectionQuerySchema()),
    }
    collection_get_arguments = {
        'schema': RequestSchema().bind(querystring=CollectionGetQuerySchema()),
        'cors_headers': ('Next-Page', 'Total-Records', 'Last-Modified', 'ETag',
                         'Cache-Control', 'Expires', 'Pragma')
    }
    collection_post_arguments = {
        'schema': PayloadRequestSchema(),
    }
    default_record_arguments = {}
    record_get_arguments = {
        'schema': RequestSchema().bind(querystring=RecordGetQuerySchema()),
        'cors_headers': ('Last-Modified', 'ETag',
                         'Cache-Control', 'Expires', 'Pragma')
    }

    def __init__(self, **kwargs):
        self.update(**kwargs)
        self.record_arguments = functools.partial(self.get_view_arguments,
                                                  'record')
        self.collection_arguments = functools.partial(self.get_view_arguments,
                                                      'collection')

    def update(self, **kwargs):
        """Update viewset attributes with provided values."""
        self.__dict__.update(**kwargs)

    def get_view_arguments(self, endpoint_type, resource_cls, method):
        """Return the Pyramid/Cornice view arguments for the given endpoint
        type and method.

        :param str endpoint_type: either "collection" or "record".
        :param resource_cls: the resource class.
        :param str method: the HTTP method.
        """
        args = {**self.default_arguments}
        default_arguments = getattr(self,
                                    'default_{}_arguments'.format(endpoint_type))
        args.update(**default_arguments)

        by_http_verb = 'default_{}_arguments'.format(method.lower())
        method_args = getattr(self, by_http_verb, {})
        args.update(**method_args)

        by_method = '{}_{}_arguments'.format(endpoint_type, method.lower())
        endpoint_args = getattr(self, by_method, {})
        args.update(**endpoint_args)

        request_schema = args.get('schema', RequestSchema())
        record_schema = self.get_record_schema(resource_cls, method)
        request_schema = request_schema.bind(body=record_schema)
        response_schemas = self.responses.get_and_bind(endpoint_type, method,
                                                       record=record_schema)

        args['schema'] = request_schema
        args['response_schemas'] = response_schemas

        validators = args.get('validators', [])
        validators.append(colander_validator)
        args['validators'] = validators

        return args

    def get_record_schema(self, resource_cls, method):
        """Return the Cornice schema for the given method.
        """
        if method.lower() in ('patch', 'delete'):
            resource_schema = SimpleSchema
        else:
            resource_schema = resource_cls.schema
            if hasattr(resource_cls, 'mapping'):
                message = "Resource `mapping` is deprecated, use `schema`"
                warnings.warn(message, DeprecationWarning)
                resource_schema = resource_cls.mapping.__class__

        record_schema = RecordSchema().bind(data=resource_schema())

        return record_schema

    def get_view(self, endpoint_type, method):
        """Return the view method name located on the resource object, for the
        given type and method.

        * For collections, this will be "collection_{method|lower}
        * For records, this will be "{method|lower}.
        """
        if endpoint_type == 'record':
            return method.lower()
        return '{}_{}'.format(endpoint_type, method.lower())

    def get_name(self, resource_cls):
        """Returns the name of the resource.
        """
        # Provided on viewset during registration.
        if 'name' in self.__dict__:
            return self.__dict__['name']

        # Attribute on resource class (but not @property)
        has_class_attr = (hasattr(resource_cls, 'name') and
                          not callable(resource_cls.name))
        if has_class_attr:
            return resource_cls.name

        # Use classname
        return resource_cls.__name__.lower()

    def get_service_name(self, endpoint_type, resource_cls):
        """Returns the name of the service, depending a given type and
        resource.
        """
        return self.service_name.format(
            resource_name=self.get_name(resource_cls),
            endpoint_type=endpoint_type)

    def get_service_arguments(self):
        return {**self.service_arguments}

    def is_endpoint_enabled(self, endpoint_type, resource_name, method,
                            settings):
        """Returns if the given endpoint is enabled or not.

        Uses the settings to tell so.
        """
        readonly_enabled = asbool(settings.get('readonly'))
        readonly_method = method.lower() in [m.lower() for m in
                                             self.readonly_methods]
        if readonly_enabled and not readonly_method:
            return False

        setting_enabled = '{}_{}_{}_enabled'.format(
            endpoint_type, resource_name, method.lower())
        return asbool(settings.get(setting_enabled, True))


class ShareableViewSet(ViewSet):
    """A ShareableViewSet will register the given resource with a schema
    that supports permissions.

    The views will rely on dynamic permissions (e.g. create with PUT if
    record does not exist), and solicit the cliquet RouteFactory.
    """

    responses = ShareableResourseResponses()

    def get_record_schema(self, resource_cls, method):
        """Return the Cornice schema for the given method.
        """
        record_schema = super(ShareableViewSet, self).get_record_schema(resource_cls, method)
        allowed_permissions = resource_cls.permissions
        permissions = PermissionsSchema(name='permissions', missing=colander.drop,
                                        permissions=allowed_permissions)
        record_schema = record_schema.bind(permissions=permissions)
        return record_schema

    def get_view_arguments(self, endpoint_type, resource_cls, method):
        args = super().get_view_arguments(endpoint_type, resource_cls, method)
        args['permission'] = authorization.DYNAMIC
        return args

    def get_service_arguments(self):
        args = super().get_service_arguments()
        args['factory'] = self.factory
        return args
