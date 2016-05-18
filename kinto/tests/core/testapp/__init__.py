from pyramid.config import Configurator
from pyramid.static import static_view
import kinto.core


def includeme(config):
    config.scan("kinto.tests.core.testapp.views")

    # Add an example route with trailing slash (here to serve static files).
    # This is only used to test 404 redirection in ``test_views_errors.py``
    static = static_view('kinto:tests/core/testapp/static', use_subpath=True)
    config.add_route('catchall_static', '/static/*subpath')
    config.add_view(static, route_name="catchall_static")


def main(settings=None, config=None, *args, **additional_settings):
    if settings is None:
        settings = {}
    settings.update(additional_settings)
    if config is None:
        config = Configurator(settings=settings)
    kinto.core.initialize(config, version='0.0.1')
    config.include(includeme)
    app = config.make_wsgi_app()
    # Install middleware (no-op if not enabled in setting)
    return kinto.core.install_middlewares(app, settings)
