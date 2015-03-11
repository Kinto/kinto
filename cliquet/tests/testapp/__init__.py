from pyramid.config import Configurator
from cliquet import initialize_cliquet


def includeme(config):
    config.scan("cliquet.tests.testapp.views")


def main(settings=None):
    config = Configurator(settings=settings)
    initialize_cliquet(config, version='0.0.1')
    config.include(includeme)
    return config.make_wsgi_app()
