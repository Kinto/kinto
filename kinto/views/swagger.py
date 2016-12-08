import json
import os

from pyramid.security import NO_PERMISSION_REQUIRED
from kinto.core import Service
from kinto.core.utils import recursive_update_dict

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGIN = os.path.dirname(os.path.dirname(HERE))

swagger = Service(name="swagger", path='/swagger.json', description="OpenAPI description")


@swagger.get(permission=NO_PERMISSION_REQUIRED)
def swagger_view(request):
    try:
        return swagger_view.__json__
    except AttributeError:
        pass

    settings = request.registry.settings

    # Swagger basic info
    info = dict(
        title=settings['project_name'],
        version=settings['http_api_version'],
    )

    schemes = [settings.get('http_scheme') or 'http']

    data = dict(
        info=info,
        host=request.host,
        basePath=request.path.replace(swagger.path, ''),
        schemes=schemes,
    )

    files = [
        os.path.join(ORIGIN, 'swagger.json'),  # Relative to the package root.
        os.path.join(HERE, 'swagger.json')  # Relative to this file.
    ]
    for version_file in files:
        file_path = os.path.abspath(version_file)
        if os.path.exists(file_path):
            with open(file_path) as f:
                swagger_view.__json__ = json.load(f)
                recursive_update_dict(swagger_view.__json__, data)
                return swagger_view.__json__
