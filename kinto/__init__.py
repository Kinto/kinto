import pkg_resources
import logging

from pyramid.config import Configurator
from pyramid.settings import asbool
from cliquet import initialize_cliquet
from cliquet.authorization import RouteFactory

# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# Main kinto logger
logger = logging.getLogger(__name__)


DEFAULT_SETTINGS = {
    'cliquet.bucket_create_principals': 'system.Authenticated',
    'multiauth.authorization_policy': (
        'kinto.authorization.AuthorizationPolicy'),
    'kinto.flush_endpoint_enabled': False
}


def main(global_config, **settings):
    config = Configurator(settings=settings, root_factory=RouteFactory)
    initialize_cliquet(config,
                       version=__version__,
                       default_settings=DEFAULT_SETTINGS)

    kwargs = {}
    flush_enabled = asbool(settings['kinto.flush_endpoint_enabled'])
    if not flush_enabled:
        kwargs['ignore'] = 'kinto.views.flush'

    config.scan("kinto.views", **kwargs)
    return config.make_wsgi_app()
