import pkg_resources
import logging

import cliquet
from pyramid.config import Configurator
from pyramid.settings import asbool
from pyramid.security import Authenticated
from cliquet.authorization import RouteFactory

# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# Main kinto logger
logger = logging.getLogger(__name__)


DEFAULT_SETTINGS = {
    'cliquet.cache_backend': 'cliquet.cache.memory',
    'cliquet.permission_backend': 'cliquet.permission.memory',
    'cliquet.storage_backend': 'cliquet.storage.memory',
    'cliquet.project_name': 'Cloud Storage',
    'cliquet.project_docs': 'https://kinto.readthedocs.org/',
    'cliquet.bucket_create_principals': Authenticated,
    'multiauth.authorization_policy': (
        'kinto.authorization.AuthorizationPolicy'),
    'multiauth.groupfinder': (
        'kinto.authorization.groupfinder')
}


def main(global_config, **settings):
    config = Configurator(settings=settings, root_factory=RouteFactory)
    cliquet.initialize(config,
                       version=__version__,
                       default_settings=DEFAULT_SETTINGS)

    settings = config.get_settings()
    kwargs = {}
    flush_enabled = asbool(settings.get('kinto.flush_endpoint_enabled'))
    if not flush_enabled:
        kwargs['ignore'] = 'kinto.views.flush'

    # Redirect default to the right endpoint
    config.add_route('default_bucket', '/buckets/default{subpath:.*}')

    config.scan("kinto.views", **kwargs)
    return config.make_wsgi_app()
