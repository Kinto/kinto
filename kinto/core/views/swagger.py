import os
import yaml
import pkg_resources

from pyramid import httpexceptions
from pyramid.settings import aslist
from pyramid.security import NO_PERMISSION_REQUIRED
from kinto.core import Service
from kinto.core.utils import recursive_update_dict

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGIN = os.path.dirname(os.path.dirname(HERE))

swagger = Service(name="swagger", path='/swagger.json', description="OpenAPI description")


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
    if settings.get('swagger_extensions'):
        includes = aslist(settings['includes'])
        for app in includes:
            f = pkg_resources.resource_filename(app, 'swagger.yaml')
            if os.path.exists(f):
                files.append(f)

    swagger_view.__json__ = {}

    # Read and merge files
    for path in files:
        abs_path = os.path.abspath(path)
        with open(abs_path) as f:
            spec = yaml.load(f)
            recursive_update_dict(swagger_view.__json__, spec)

    # Update instance fields
    info = dict(
        title=settings['project_name'],
        version=settings['http_api_version'])

    schemes = [settings.get('http_scheme') or 'http']

    data = dict(
        info=info,
        host=request.host,
        basePath=request.path.replace(swagger.path, ''),
        schemes=schemes)

    recursive_update_dict(swagger_view.__json__, data)

    return swagger_view.__json__
