import json
import os
import pkg_resources

from pyramid.security import NO_PERMISSION_REQUIRED
from kinto.core import Service

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGIN = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

VERSION_PATH = 'version.json'  # Relative to where we start it.
VERSION_JSON = None

try:  # Pragma: no cover
    with open(VERSION_PATH, 'r') as f:
        VERSION_JSON = json.load(f)
except IOError:  # Pragma: no cover
    pass

version = Service(name="version", path='/__version__', description="Version")


def read_git_commit():
    head_path = os.path.join(ORIGIN, '.git', "HEAD")
    if not os.path.exists(head_path):
        return "NOT_AVAILABLE"

    with open(head_path) as fd:
        info = fd.readlines()[0].strip()
    if info.startswith('ref:'):
        ref_path = info.split()[1]
        with open(os.path.join(os.path.dirname(head_path), ref_path)) as fd:
            info = fd.readlines()[0].strip()
    return info


@version.get(permission=NO_PERMISSION_REQUIRED)
def version_view(request):
    body = VERSION_JSON

    if VERSION_JSON is None:
        settings = request.registry.settings
        project_name = settings['project_name']

        try:
            # Try to get the project_name distribution
            distribution = pkg_resources.get_distribution(project_name)
        except pkg_resources.DistributionNotFound:
            # If it doesn't work let's fallback to kinto
            project_name = 'kinto'
            distribution = pkg_resources.get_distribution(project_name)

        package_version = distribution.version
        package_metadata = distribution._get_metadata(distribution.PKG_INFO)

        home_page = [m for m in package_metadata if m.startswith('Home-page:')]

        source = None
        if home_page:
            source = home_page[0].split(':', 1)[1].strip()

        commit = read_git_commit()

        body = {
            "name": project_name,
            "commit": commit,
            "version": package_version,
            "source": source
        }
    return body
