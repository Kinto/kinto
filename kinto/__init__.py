import pkg_resources
import logging

import kinto.core
from pyramid.config import Configurator
from pyramid.settings import asbool
from pyramid.security import Authenticated

from kinto.authorization import RouteFactory

# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# Implemented HTTP API Version
HTTP_API_VERSION = '1.5'

# Main kinto logger
logger = logging.getLogger(__name__)


DEFAULT_SETTINGS = {
    'retry_after_seconds': 3,
    'cache_backend': 'kinto.core.cache.memory',
    'permission_backend': 'kinto.core.permission.memory',
    'storage_backend': 'kinto.core.storage.memory',
    'project_docs': 'https://kinto.readthedocs.io/',
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
    config.add_settings({'kinto.project_name': 'kinto'})

    kinto.core.initialize(config,
                          version=__version__,
                          default_settings=DEFAULT_SETTINGS)

    settings = config.get_settings()

    # Expose capability
    schema_enabled = asbool(
        settings['experimental_collection_schema_validation']
    )
    if schema_enabled:
        config.add_api_capability(
            "schema",
            description="Validates collection records with JSON schemas.",
            url="http://kinto.readthedocs.io/en/latest/api/1.x/"
                "collections.html#collection-json-schema")

    # Scan Kinto views.
    kwargs = {}
    flush_enabled = asbool(settings.get('flush_endpoint_enabled'))

    if flush_enabled:
        config.add_api_capability(
            "flush_endpoint",
            description="The __flush__ endpoint can be used to remove all "
                        "data from all backends.",
            url="http://kinto.readthedocs.io/en/latest/configuration/"
                "settings.html#activating-the-flush-endpoint"
        )
    else:
        kwargs['ignore'] = 'kinto.views.flush'
    config.scan("kinto.views", **kwargs)

    app = config.make_wsgi_app()

    # Install middleware (idempotent if disabled)
    return kinto.core.install_middlewares(app, settings)
