from pathlib import Path

from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid.static import static_view

from .views import admin_home_view


def includeme(config):
    admin_assets_path = config.registry.settings["admin_assets_path"]
    if not admin_assets_path:
        # Use bundled admin.
        admin_assets_path = "kinto.plugins.admin:build"
        version_file_parent = Path(__file__).parent
    else:
        version_file_parent = Path(admin_assets_path)

    admin_version = (version_file_parent / "VERSION").read_text().strip()

    # Expose capability.
    config.add_api_capability(
        "admin",
        version=admin_version,
        description="Serves the admin console.",
        url="https://github.com/Kinto/kinto-admin/",
    )

    config.add_route("admin_home", "/admin/")
    config.add_view(admin_home_view, route_name="admin_home")

    build_dir = static_view(admin_assets_path, use_subpath=True)
    config.add_route("catchall_static", "/admin/*subpath")
    config.add_view(build_dir, route_name="catchall_static")

    # Setup redirect without trailing slash.
    def admin_redirect_view(request):
        raise HTTPTemporaryRedirect(request.path + "/")

    config.add_route("admin_redirect", "/admin")
    config.add_view(admin_redirect_view, route_name="admin_redirect")
