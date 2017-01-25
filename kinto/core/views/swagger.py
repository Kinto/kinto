from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.settings import aslist
from cornice.service import get_services
from cornice_swagger import CorniceSwagger
from cornice_swagger.converters.schema import TypeConversionDispatcher, TypeConverter

from kinto.core import Service
from kinto.core.schema import Any


swagger = Service(name="swagger", path='/__api__', description="OpenAPI description")


class AnyTypeConverter(TypeConverter):
    """Convert type agnostic parameter to swagger."""

    def __call__(self, schema_node):
        return {}


# XXX: Add type converter to the dispatcher
# https://github.com/Cornices/cornice.ext.swagger/pull/48
TypeConversionDispatcher.converters[Any] = AnyTypeConverter


def tag_generator(service, method):
    """Povides default swagger tags to views."""

    base_tag = service.name.capitalize()
    base_tag = base_tag.replace('-collection', '')
    base_tag = base_tag.replace('-record', '')
    return [base_tag]


def operation_id_generator(service, method):
    """Povides default operation ids to methods if not defined on view."""

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

    resource = resource.replace('-collection', 's')
    resource = resource.replace('-record', '')
    op_id = "%s_%s" % (method, resource)

    return op_id


def security_policies_generator(service, method, security_roles=[]):
    """Provides OpenAPI security properties based on kinto policies."""

    definitions = service.definitions

    # Get method view arguments
    for definition in definitions:
        met, view, args = definition
        if met == method:
            break
    print(args.keys())
    if args.get('permission') == '__no_permission_required__':
        return []
    else:
        return security_roles


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

    security_defs = {}
    security_roles = []

    # BasicAuth is a non extension capability, so we should check it from config
    if 'basicauth' in aslist(settings.get('multiauth.policies', '')):
        basicauth = {'type': 'basic',
                     'description': 'HTTP Basic Authentication.'}
        security_defs['basicAuth'] = basicauth
        security_roles.append({'basicAuth': []})

    def security_generator(service, method):
        return security_policies_generator(service, method, security_roles)

    base_spec = {
        'host': request.host,
        'schemes': [settings.get('http_scheme') or 'http'],
        'basePath': request.path.replace(swagger.path, ''),
        'securityDefinitions': security_defs,
    }

    spec = generator(
        title=settings['project_name'],
        version=settings['http_api_version'],
        base_path=request.path.replace(swagger.path, ''),
        ignore_ctypes=["application/json-patch+json"],
        default_tags=tag_generator,
        default_op_ids=operation_id_generator,
        default_security=security_generator,
        swagger=base_spec
    )

    swagger_view.__json__ = spec

    return swagger_view.__json__
