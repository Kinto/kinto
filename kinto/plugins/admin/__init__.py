from pathlib import Path

from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid.static import static_view

from .views import admin_home_view

VERSION_FILE_PATH = Path(__file__).parent / "VERSION"


def includeme(config):
    admin_version = VERSION_FILE_PATH.read_text().strip()

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
