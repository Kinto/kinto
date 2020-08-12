import os

from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid.static import static_view

from kinto.core.utils import json

from .views import admin_home_view

HERE = os.path.dirname(__file__)


def includeme(config):
    # Process settings to remove storage wording.

    # Read version from package.json
    package_json = json.load(open(os.path.join(HERE, "package.json")))
    admin_version = package_json["dependencies"]["kinto-admin"]

    # Expose capability.
    config.add_api_capability(
        "admin",
        version=admin_version,
        description="Serves the admin console.",
        url="https://github.com/Kinto/kinto-admin/",
    )

    config.add_route("admin_home", "/admin/")
    config.add_view(admin_home_view, route_name="admin_home")

    build_dir = static_view("kinto.plugins.admin:build", use_subpath=True)
    config.add_route("catchall_static", "/admin/*subpath")
    config.add_view(build_dir, route_name="catchall_static")

    # Setup redirect without trailing slash.
    def admin_redirect_view(request):
        raise HTTPTemporaryRedirect(request.path + "/")

    config.add_route("admin_redirect", "/admin")
    config.add_view(admin_redirect_view, route_name="admin_redirect")
