"""Main entry point
"""
import pkg_resources

import structlog
from cornice import Service as CorniceService
from pyramid.settings import aslist


# Main Cliquet logger.
logger = structlog.get_logger()

from cliquet import errors
from cliquet.initialization import (  # NOQA
    initialize, initialize_cliquet, install_middlewares,
    load_default_settings)


# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# The API version is derivated from the module version.
API_VERSION = 'v%s' % __version__.split('.')[0]


DEFAULT_SETTINGS = {
    'backoff': None,
    'batch_max_requests': 25,
    'cache_backend': '',
    'cache_pool_size': 10,
    'cache_url': '',
    'cors_origins': '*',
    'cors_max_age_seconds': 3600,
    'eos': None,
    'eos_message': None,
    'eos_url': None,
    'error_info_link': 'https://github.com/mozilla-services/cliquet/issues/',
    'http_host': None,
    'http_scheme': None,
    'id_generator': 'cliquet.storage.generators.UUID4',
    'initialization_sequence': (
        'cliquet.initialization.setup_request_bound_data',
        'cliquet.initialization.setup_json_serializer',
        'cliquet.initialization.setup_logging',
        'cliquet.initialization.setup_storage',
        'cliquet.initialization.setup_permission',
        'cliquet.initialization.setup_cache',
        'cliquet.initialization.setup_requests_scheme',
        'cliquet.initialization.setup_trailing_slash_redirection',
        'cliquet.initialization.setup_version_redirection',
        'cliquet.initialization.setup_deprecation',
        'cliquet.initialization.setup_authentication',
        'cliquet.initialization.setup_backoff',
        'cliquet.initialization.setup_statsd'
    ),
    'logging_renderer': 'cliquet.logs.ClassicLogRenderer',
    'newrelic_config': None,
    'newrelic_env': 'dev',
    'paginate_by': None,
    'permission_backend': '',
    'permission_url': '',
    'permission_pool_size': 10,
    'profiler_dir': '/tmp',
    'profiler_enabled': False,
    'project_docs': '',
    'project_name': '',
    'project_version': '',
    'retry_after_seconds': 30,
    'statsd_prefix': 'cliquet',
    'statsd_url': None,
    'storage_backend': '',
    'storage_max_fetch_size': 10000,
    'storage_pool_size': 10,
    'storage_url': '',
    'userid_hmac_secret': '',
    'version_prefix_redirect_enabled': True,
    'trailing_slash_redirect_enabled': True,
    'multiauth.policies': 'basicauth',
    'multiauth.policy.basicauth.use': ('cliquet.authentication.'
                                       'BasicAuthAuthenticationPolicy'),
    'multiauth.authorization_policy': ('cliquet.authorization.'
                                       'AuthorizationPolicy')
}


class Service(CorniceService):
    """Subclass of the default cornice service.

    This is useful in order to attach specific behaviours without monkey
    patching the default cornice service (which would impact other uses of it)
    """


def includeme(config):
    settings = config.get_settings()

    # Heartbeat registry.
    config.registry.heartbeats = {}

    # Public settings registry.
    config.registry.public_settings = {'batch_max_requests'}

    # Setup components.
    for step in aslist(settings['initialization_sequence']):
        step_func = config.maybe_dotted(step)
        step_func(config)

    # # Show settings to output.
    # for key, value in settings.items():
    #     logger.info('Using %s = %s' % (key, value))

    # Add CORS settings to the base cliquet Service class.
    cors_origins = settings['cors_origins']
    Service.cors_origins = tuple(aslist(cors_origins))
    Service.default_cors_headers = ('Backoff', 'Retry-After', 'Alert',
                                    'Content-Length')
    cors_max_age = settings['cors_max_age_seconds']
    Service.cors_max_age = int(cors_max_age) if cors_max_age else None

    Service.error_handler = lambda self, e: errors.json_error_handler(e)

    # Setup cornice.
    config.include("cornice")

    # Scan views.
    config.scan("cliquet.views")

    # Give sign of life.
    msg = "%(project_name)s %(project_version)s starting."
    logger.info(msg % settings)
