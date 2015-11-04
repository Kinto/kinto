from pyramid.config import Configurator
import cliquet


def includeme(config):
    config.scan("cliquet.tests.testapp.views")


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
