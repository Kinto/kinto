import json
import os

from pyramid import httpexceptions
from pyramid.security import NO_PERMISSION_REQUIRED
from kinto.core import Service

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGIN = os.path.dirname(os.path.dirname(HERE))

version = Service(name="version", path='/__version__', description="Version")


@version.get(permission=NO_PERMISSION_REQUIRED)
def version_view(request):
    try:
        return version_view.__json__
    except AttributeError:
        pass

    location = request.registry.settings['version_json_path']
    files = [
        location,  # Default is current working dir.
        os.path.join(ORIGIN, 'version.json'),  # Relative to the package root.
        os.path.join(HERE, 'version.json')  # Relative to this file.
    ]
    for version_file in files:
        file_path = os.path.abspath(version_file)
        if os.path.exists(file_path):
            with open(file_path) as f:
                version_view.__json__ = json.load(f)
                return version_view.__json__  # First one wins.

    raise httpexceptions.HTTPNotFound()
