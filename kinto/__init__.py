import pkg_resources
import logging

import cliquet
from pyramid.config import Configurator
from pyramid.settings import asbool
from pyramid.security import Authenticated

from kinto.authorization import RouteFactory

# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# Implemented HTTP API Version
HTTP_API_VERSION = '1.4'

# Main kinto logger
logger = logging.getLogger(__name__)


DEFAULT_SETTINGS = {
    'retry_after_seconds': 3,
    'cache_backend': 'cliquet.cache.memory',
    'permission_backend': 'cliquet.permission.memory',
    'storage_backend': 'cliquet.storage.memory',
    'project_docs': 'https://kinto.readthedocs.org/',
    'bucket_create_principals': Authenticated,
    'multiauth.authorization_policy': (
        'kinto.authorization.AuthorizationPolicy'),
    'experimental_collection_schema_validation': 'False',
    'http_api_version': HTTP_API_VERSION
}


def main(global_config, config=None, **settings):
    if not config:
        config = Configurator(settings=settings, root_factory=RouteFactory)

    # Force project name, since it determines settings prefix.
    config.add_settings({'cliquet.project_name': 'kinto'})

    cliquet.initialize(config,
                       version=__version__,
                       default_settings=DEFAULT_SETTINGS)

    settings = config.get_settings()

    # In Kinto API 1.x, a default bucket is available.
    default_bucket_plugin='kinto.plugins.default_bucket'
    if 'excludes' in settings and default_bucket_plugin in settings['excludes']:
        # do not include the default bucket plugin
        pass
    # Force its inclusion if not specified in settings and not explictly excluded
    elif default_bucket_plugin not in settings['includes']:
        config.include(default_bucket_plugin)

    # Retro-compatibility with first Kinto clients.
    config.registry.public_settings.add('cliquet.batch_max_requests')

    # Expose capability
    schema_enabled = asbool(
        settings['experimental_collection_schema_validation']
    )
    if schema_enabled:
        config.add_api_capability(
            "schema",
            description="Validates collection records with JSON schemas.",
            url="http://kinto.readthedocs.org/en/latest/api/1.x/"
                "collections.html#collection-json-schema")

    # Scan Kinto views.
    kwargs = {}
    flush_enabled = asbool(settings.get('flush_endpoint_enabled'))

    if flush_enabled:
        config.add_api_capability(
            "flush_endpoint",
            description="The __flush__ endpoint can be used to remove all "
                        "data from all backends.",
            url="http://kinto.readthedocs.org/en/latest/configuration/"
                "settings.html#activating-the-flush-endpoint"
        )
    else:
        kwargs['ignore'] = 'kinto.views.flush'
    config.scan("kinto.views", **kwargs)

    app = config.make_wsgi_app()

    # Install middleware (idempotent if disabled)
    return cliquet.install_middlewares(app, settings)
