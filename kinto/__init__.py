import pkg_resources
import logging

from pyramid.config import Configurator

# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# The API version is derivated from the module version.
API_VERSION = 'v%s' % __version__.split('.')[0]

# Main kinto logger
logger = logging.getLogger(__name__)


def main(global_config, **settings):
    config = Configurator(settings=settings)

    # Include cornice and discover views.
    config.include("cliquet", route_prefix=API_VERSION)
    config.route_prefix = API_VERSION

    config.scan("kinto.views")
    return config.make_wsgi_app()
