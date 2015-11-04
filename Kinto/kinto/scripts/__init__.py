import pkg_resources
import logging

import cliquet
from pyramid.config import Configurator
from pyramid.settings import asbool
from pyramid.security import Authenticated

from kinto.authorization import RouteFactory

# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# Main kinto logger
logger = logging.getLogger(__name__)


DEFAULT_SETTINGS = {
    'cache_backend': 'cliquet.cache.memory',
    'permission_backend': 'cliquet.permission.memory',
    'storage_backend': 'cliquet.storage.memory',
    'project_docs': 'https://kinto.readthedocs.org/',
    'bucket_create_principals': Authenticated,
    'multiauth.authorization_policy': (
        'kinto.authorization.AuthorizationPolicy'),
    'multiauth.groupfinder': (
        'kinto.authorization.groupfinder'),
    'experimental_collection_schema_validation': 'False',
}


def main(global_config, **settings):
    config = Configurator(settings=settings, root_factory=RouteFactory)

    # Force project name, since it determines settings prefix.
    config.add_settings({'cliquet.project_name': 'kinto'})

    cliquet.initialize(config,
                       version=__version__,
                       default_settings=DEFAULT_SETTINGS)

    # Redirect default to the right endpoint
    config.add_route('default_bucket_collection',
                     '/buckets/default/{subpath:.*}')
    config.add_route('default_bucket', '/buckets/default')

    # Retro-compatibility with first Kinto clients.
    config.registry.public_settings.add('cliquet.batch_max_requests')

    # Scan Kinto views.
    settings = config.get_settings()
    kwargs = {}
    flush_enabled = asbool(settings.get('flush_endpoint_enabled'))
    if not flush_enabled:
        kwargs['ignore'] = 'kinto.views.flush'
    config.scan("kinto.views", **kwargs)

    app = config.make_wsgi_app()

    # Install middleware (idempotent if disabled)
    return cliquet.install_middlewares(app, settings)
