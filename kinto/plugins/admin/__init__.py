from pyramid.static import static_view


def includeme(config):
    # Process settings to remove storage wording.

    # Expose capability.
    config.add_api_capability(
        "admin",
        version="1.4.0",
        description="Serves the admin console.",
        url="https://github.com/Kinto/kinto-admin/",
    )

    www = static_view('kinto.plugins.admin:www', use_subpath=True)
    config.add_route('catchall_static', '/admin/*subpath')
    config.add_view(www, route_name="catchall_static")
