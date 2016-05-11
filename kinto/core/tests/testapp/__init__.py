from pyramid.config import Configurator
from pyramid.static import static_view
import cliquet


def includeme(config):
    config.scan("cliquet.tests.testapp.views")

    # Add an example route with trailing slash (here to serve static files).
    # This is only used to test 404 redirection in ``test_views_errors.py``
    static = static_view('cliquet:tests/testapp/static', use_subpath=True)
    config.add_route('catchall_static', '/static/*subpath')
    config.add_view(static, route_name="catchall_static")


def main(settings=None, config=None, *args, **additional_settings):
    if settings is None:
        settings = {}
    settings.update(additional_settings)
    if config is None:
        config = Configurator(settings=settings)
    cliquet.initialize(config, version='0.0.1')
    config.include(includeme)
    app = config.make_wsgi_app()
    # Install middleware (no-op if not enabled in setting)
    return cliquet.install_middlewares(app, settings)
