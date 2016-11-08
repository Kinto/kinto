import functools
import warnings

import colander
from cornice.validators import colander_validator
from pyramid.settings import asbool

from kinto.core import authorization
from kinto.core.resource.schema import PermissionsSchema


CONTENT_TYPES = ["application/json"]

PATCH_CONTENT_TYPES = ["application/json-patch+json",
                       "application/merge-patch+json"]


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


class ViewSet(object):
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
    validate_schema_for = ('POST', 'PUT', 'PATCH')

    readonly_methods = ('GET', 'OPTIONS', 'HEAD')

    factory = authorization.RouteFactory

    service_arguments = {
        'description': 'Collection of {resource_name}',
    }

    default_arguments = {
        'permission': authorization.PRIVATE,
        'accept': CONTENT_TYPES,
    }

    default_post_arguments = {
        "content_type": CONTENT_TYPES,
    }

    default_put_arguments = {
        "content_type": CONTENT_TYPES,
    }

    default_patch_arguments = {
        "content_type": CONTENT_TYPES + PATCH_CONTENT_TYPES
    }

    default_collection_arguments = {}
    collection_get_arguments = {
        'cors_headers': ('Next-Page', 'Total-Records', 'Last-Modified', 'ETag',
                         'Cache-Control', 'Expires', 'Pragma')
    }

    default_record_arguments = {}
    record_get_arguments = {
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
        args = self.default_arguments.copy()
        default_arguments = getattr(self,
                                    'default_%s_arguments' % endpoint_type)
        args.update(**default_arguments)

        by_http_verb = 'default_%s_arguments' % method.lower()
        method_args = getattr(self, by_http_verb, {})
        args.update(**method_args)

        by_method = '%s_%s_arguments' % (endpoint_type, method.lower())
        endpoint_args = getattr(self, by_method, {})
        args.update(**endpoint_args)

        if method.lower() in map(str.lower, self.validate_schema_for):
            schema = PartialSchema()
            record_schema = self.get_record_schema(resource_cls, method)
            record_schema.name = 'body'
            schema.add(record_schema)
            args['schema'] = schema
        else:
            args['schema'] = SimpleSchema()

        validators = args.get('validators', [])
        validators.append(colander_validator)
        args['validators'] = validators

        return args

    def get_record_schema(self, resource_cls, method):
        """Return the Cornice schema for the given method.
        """
        if method.lower() == 'patch':
            resource_schema = SimpleSchema
        else:
            resource_schema = resource_cls.schema
            if hasattr(resource_cls, 'mapping'):
                message = "Resource `mapping` is deprecated, use `schema`"
                warnings.warn(message, DeprecationWarning)
                resource_schema = resource_cls.mapping.__class__

        payload_schema = StrictSchema()
        payload_schema.add(resource_schema(name='data'))
        return payload_schema

    def get_view(self, endpoint_type, method):
        """Return the view method name located on the resource object, for the
        given type and method.

        * For collections, this will be "collection_{method|lower}
        * For records, this will be "{method|lower}.
        """
        if endpoint_type == 'record':
            return method.lower()
        return '%s_%s' % (endpoint_type, method.lower())

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
        return self.service_arguments.copy()

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

        setting_enabled = '%s_%s_%s_enabled' % (
            endpoint_type, resource_name, method.lower())
        return asbool(settings.get(setting_enabled, True))


class ShareableViewSet(ViewSet):
    """A ShareableViewSet will register the given resource with a schema
    that supports permissions.

    The views will rely on dynamic permissions (e.g. create with PUT if
    record does not exist), and solicit the cliquet RouteFactory.
    """
    def get_record_schema(self, resource_cls, method):
        """Return the Cornice schema for the given method.
        """
        if method.lower() == 'patch':
            resource_schema = SimpleSchema
        else:
            resource_schema = resource_cls.schema
            if hasattr(resource_cls, 'mapping'):
                message = "Resource `mapping` is deprecated, use `schema`"
                warnings.warn(message, DeprecationWarning)
                resource_schema = resource_cls.mapping.__class__

        try:
            # Check if empty record is allowed.
            # (e.g every schema fields have defaults)
            resource_schema().deserialize({})
        except colander.Invalid:
            schema_kw = dict(missing=colander.required)
        else:
            schema_kw = dict(default={}, missing=colander.drop)

        allowed_permissions = resource_cls.permissions

        payload_schema = StrictSchema()
        payload_schema.add(resource_schema(name='data', **schema_kw))
        payload_schema.add(PermissionsSchema(name='permissions',
                                             missing=colander.drop,
                                             permissions=allowed_permissions))
        return payload_schema

    def get_view_arguments(self, endpoint_type, resource_cls, method):
        args = super(ShareableViewSet, self).get_view_arguments(endpoint_type,
                                                                resource_cls,
                                                                method)
        args['permission'] = authorization.DYNAMIC
        return args

    def get_service_arguments(self):
        args = super(ShareableViewSet, self).get_service_arguments()
        args['factory'] = self.factory
        return args
