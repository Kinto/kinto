import os
import pkg_resources

from ruamel import yaml
from pyramid import httpexceptions
from pyramid.settings import aslist
from pyramid.security import NO_PERMISSION_REQUIRED
from kinto.core import Service
from kinto.core.utils import recursive_update_dict

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGIN = os.path.dirname(os.path.dirname(HERE))

swagger = Service(name="swagger", path='/__api__', description="OpenAPI description")


@swagger.get(permission=NO_PERMISSION_REQUIRED)
def swagger_view(request):

    # Only build json once
    try:
        return swagger_view.__json__
    except AttributeError:
        pass

    settings = request.registry.settings

    # Base swagger spec
    files = [
        settings.get('swagger_file', ''),  # From config
        os.path.join(ORIGIN, 'swagger.yaml'),  # Relative to the package root
        os.path.join(HERE, 'swagger.yaml')  # Relative to this file.
    ]

    files = [f for f in files if os.path.exists(f)]

    # Get first file that exists
    if files:
        files = files[:1]
    else:
        raise httpexceptions.HTTPNotFound()

    # Plugin swagger extensions
    includes = aslist(settings.get('includes', ''))
    for app in includes:
        f = pkg_resources.resource_filename(app, 'swagger.yaml')
        if os.path.exists(f):
            files.append(f)

    swagger_view.__json__ = {}

    # Read and merge files
    for path in files:
        abs_path = os.path.abspath(path)
        with open(abs_path) as f:
            spec = yaml.safe_load(f)
            recursive_update_dict(swagger_view.__json__, spec)

    # Update instance fields
    info = dict(
        title=settings['project_name'],
        version=settings['http_api_version'])

    schemes = [settings.get('http_scheme') or 'http']

    security_defs = swagger_view.__json__.get('securityDefinitions', {})

    # BasicAuth is a non extension capability, so we should check it from config
    if 'basicauth' in aslist(settings.get('multiauth.policies', '')):
        basicauth = {'type': 'basic',
                     'description': 'HTTP Basic Authentication.'}
        security_defs['basicAuth'] = basicauth

    # Security options are JSON objects with a single key
    security = swagger_view.__json__.get('security', [])
    security_names = [next(iter(security_def)) for security_def in security]

    # include securityDefinitions that are not on default security options
    for name, prop in security_defs.items():
        security_def = {name: prop.get('scopes', {}).keys()}
        if name not in security_names:
            security.append(security_def)

    data = dict(
        info=info,
        host=request.host,
        basePath=request.path.replace(swagger.path, ''),
        schemes=schemes,
        securityDefinitions=security_defs,
        security=security)

    recursive_update_dict(swagger_view.__json__, data)

    return swagger_view.__json__
