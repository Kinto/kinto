import functools

import colander

from cliquet import authorization
from cliquet.schema import PermissionsSchema


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

    readonly_methods = ('GET',)

    service_arguments = {
        'description': 'Collection of {resource_name}',
    }

    default_arguments = {
        'permission': authorization.PRIVATE
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

    def get_view_arguments(self, endpoint_type, resource, method):
        """Return the Pyramid/Cornice view arguments for the given endpoint
        type and method.

        :param str endpoint_type: either "collection" or "record".
        :param resource: the resource object.
        :param str method: the HTTP method.
        """
        args = self.default_arguments.copy()
        default_arguments = getattr(self,
                                    'default_%s_arguments' % endpoint_type)
        args.update(**default_arguments)

        by_method = '%s_%s_arguments' % (endpoint_type, method.lower())
        method_args = getattr(self, by_method, {})
        args.update(**method_args)

        args['schema'] = self.get_record_schema(resource, method)

        return args

    def get_record_schema(self, resource, method):
        """Return the Cornice schema for the given method.
        """
        simple_mapping = colander.MappingSchema(unknown='preserve')

        if method.lower() not in map(str.lower, self.validate_schema_for):
            # Simply validate that posted body is a mapping.
            return simple_mapping

        if method.lower() == 'patch':
            record_mapping = simple_mapping
        else:
            record_mapping = resource.mapping

            try:
                record_mapping.deserialize({})
                # Empty data accepted.
                record_mapping.missing = colander.drop
                record_mapping.default = {}
            except colander.Invalid:
                pass

        class PayloadSchema(colander.MappingSchema):
            data = record_mapping

            def schema_type(self, **kw):
                return colander.Mapping(unknown='raise')

        return PayloadSchema()

    def get_view(self, endpoint_type, method):
        """Return the view method name located on the resource object, for the
        given type and method.

        * For collections, this will be "collection_{method|lower}
        * For records, this will be "{method|lower}.
        """
        if endpoint_type == 'record':
            return method.lower()
        return '%s_%s' % (endpoint_type, method.lower())

    def get_name(self, resource):
        """Returns the name of the resource.
        """
        if 'name' in self.__dict__:
            name = self.__dict__['name']
        elif hasattr(resource, 'name') and not callable(resource.name):
            name = resource.name
        else:
            name = resource.__name__.lower()

        return name

    def get_service_name(self, endpoint_type, resource):
        """Returns the name of the service, depending a given type and
        resource.
        """
        return self.service_name.format(
            resource_name=self.get_name(resource),
            endpoint_type=endpoint_type)

    def get_service_arguments(self):
        return self.service_arguments.copy()

    def is_endpoint_enabled(self, endpoint_type, resource_name, method,
                            settings):
        """Returns if the given endpoint is enabled or not.

        Uses the settings to tell so.
        """
        setting_enabled = '%s_%s_%s_enabled' % (
            endpoint_type, resource_name, method.lower())
        return settings.get(setting_enabled, True)


class ProtectedViewSet(ViewSet):
    def get_record_schema(self, resource, method):
        schema = super(ProtectedViewSet, self).get_record_schema(resource,
                                                                 method)

        if method.lower() not in map(str.lower, self.validate_schema_for):
            return schema

        if method.lower() == 'patch':
            # Data is optional when patching permissions.
            schema.children[-1].missing = colander.drop

        permissions_node = PermissionsSchema(missing=colander.drop,
                                             permissions=resource.permissions,
                                             name='permissions')
        schema.add(permissions_node)
        return schema

    def get_view_arguments(self, endpoint_type, resource, method):
        args = super(ProtectedViewSet, self).get_view_arguments(endpoint_type,
                                                                resource,
                                                                method)
        args['permission'] = authorization.DYNAMIC
        return args

    def get_service_arguments(self):
        args = super(ProtectedViewSet, self).get_service_arguments()
        args['factory'] = authorization.RouteFactory
        return args
