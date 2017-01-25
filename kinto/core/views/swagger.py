import os
import pkg_resources

from pyramid.security import NO_PERMISSION_REQUIRED
from cornice.service import get_services
from cornice_swagger import CorniceSwagger
from cornice_swagger.converters.schema import TypeConversionDispatcher, TypeConverter
from kinto.core import Service
from kinto.core.schema import Any


class AnyTypeConverter(TypeConverter):

    def __call__(self, schema_node):
        return {}


TypeConversionDispatcher.converters[Any] = AnyTypeConverter


swagger = Service(name="swagger", path='/__api__', description="OpenAPI description")


def tag_generator(service, method):
    base_tag = service.name.capitalize()
    base_tag = base_tag.replace('-collection', '')
    base_tag = base_tag.replace('-record', '')
    return [base_tag, "Kinto"]


def operation_id_generator(service, method):
    method = method.lower()
    method_mapping = {
        'post': 'create',
        'put': 'update'
    }
    if method in method_mapping:
        method = method_mapping[method]

    resource = service.name
    if method == 'create':
        resource = resource.replace('-collection', '')
    else:
        resource = resource.replace('-collection', 's')
    resource = resource.replace('-record', '')
    op_id = "%s_%s" % (method, resource)
    return op_id


@swagger.get(permission=NO_PERMISSION_REQUIRED)
def swagger_view(request):

    # Only build json once
    try:
        return swagger_view.__json__
    except AttributeError:
        pass

    services = get_services()
    settings = request.registry.settings
    generator = CorniceSwagger(services)

    base_spec = {
        'host': request.host,
        'schemes': [settings.get('http_scheme') or 'http'],
        'basePath': request.path.replace(swagger.path, ''),
    }

    spec = generator(settings['project_name'], settings['http_api_version'],
                     ignore_ctypes=["application/json-patch+json"],
                     default_tags=tag_generator, default_op_ids=operation_id_generator,
                     swagger=base_spec)

    swagger_view.__json__  = spec

    return swagger_view.__json__
