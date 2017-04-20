import json
import os

from pyramid import httpexceptions
from pyramid.security import NO_PERMISSION_REQUIRED
from kinto.core import Service

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGIN = os.path.dirname(os.path.dirname(HERE))

VERSION_PATH = 'version.json'
VERSION_JSON = None

version = Service(name="version", path='/__version__', description="Version")

VERSIONS_FILES = [
    VERSION_PATH,  # Relative to the CURRENT_WORKING_DIR.
    os.path.join(ORIGIN, VERSION_PATH),  # Relative to the package.
    os.path.join(HERE, VERSION_PATH)]  # Relative to this file.

for version_file in VERSIONS_FILES:
    file_path = os.path.abspath(version_file)
    if os.path.exists(file_path):
        with open(file_path) as f:
            VERSION_JSON = json.load(f)
            break  # The first one wins


@version.get(permission=NO_PERMISSION_REQUIRED)
def version_view(request):
    if VERSION_JSON is not None:
        return VERSION_JSON

    raise httpexceptions.HTTPNotFound()
