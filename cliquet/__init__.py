"""Main entry point
"""
import warnings
import pkg_resources

import structlog
from cornice import Service as CorniceService
from pyramid.settings import asbool, aslist

from cliquet import utils

# Main Cliquet logger.
logger = structlog.get_logger()

from cliquet.initialization import (  # NOQA
    initialize, initialize_cliquet, install_middlewares)


# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# The API version is derivated from the module version.
API_VERSION = 'v%s' % __version__.split('.')[0]


DEFAULT_SETTINGS = {
    'cliquet.backoff': None,
    'cliquet.batch_max_requests': 25,
    'cliquet.cache_backend': 'cliquet.cache.redis',
    'cliquet.cache_pool_size': 10,
    'cliquet.cache_url': '',
    'cliquet.cors_origins': '*',
    'cliquet.eos': None,
    'cliquet.eos_message': None,
    'cliquet.eos_url': None,
    'cliquet.http_host': None,
    'cliquet.http_scheme': None,
    'cliquet.id_generator': 'cliquet.storage.generators.UUID4',
    'cliquet.initialization_sequence': (
        'cliquet.initialization.setup_json_serializer',
        'cliquet.initialization.setup_logging',
        'cliquet.initialization.setup_storage',
        'cliquet.initialization.setup_permission',
        'cliquet.initialization.setup_cache',
        'cliquet.initialization.setup_requests_scheme',
        'cliquet.initialization.setup_version_redirection',
        'cliquet.initialization.setup_deprecation',
        'cliquet.initialization.setup_authentication',
        'cliquet.initialization.setup_backoff',
        'cliquet.initialization.setup_statsd'
    ),
    'cliquet.logging_renderer': 'cliquet.logs.ClassicLogRenderer',
    'cliquet.newrelic_config': None,
    'cliquet.newrelic_env': 'dev',
    'cliquet.paginate_by': None,
    'cliquet.permission_backend': 'cliquet.permission.redis',
    'cliquet.permission_url': '',
    'cliquet.permission_pool_size': 10,
    'cliquet.profiler_dir': '/tmp',
    'cliquet.profiler_enabled': False,
    'cliquet.project_docs': '',
    'cliquet.project_name': '',
    'cliquet.project_version': '',
    'cliquet.retry_after_seconds': 30,
    'cliquet.statsd_prefix': 'cliquet',
    'cliquet.statsd_url': None,
    'cliquet.storage_backend': 'cliquet.storage.redis',
    'cliquet.storage_max_fetch_size': 10000,
    'cliquet.storage_pool_size': 10,
    'cliquet.storage_url': '',
    'cliquet.userid_hmac_secret': '',
    'cliquet.version_prefix_redirect_enabled': True,
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


def load_default_settings(config, default_settings):
    """Read settings provided in Paste ini file, set default values and
    replace if defined as environment variable.
    """
    settings = config.get_settings()
    for key, value in default_settings.items():
        configured = settings.get(key, value)
        settings[key] = utils.read_env(key, configured)

    deprecated_settings = [
        ('cliquet.cache_pool_maxconn', 'cliquet.cache_pool_size'),
        ('cliquet.storage_pool_maxconn', 'cliquet.storage_pool_size'),
        ('cliquet.basic_auth_enabled', 'multiauth.policies')
    ]
    for old, new in deprecated_settings:
        if old in settings:
            msg = "'%s' setting is deprecated. Use '%s' instead." % (old, new)
            warnings.warn(msg, DeprecationWarning)

            if old == 'cliquet.basic_auth_enabled':
                # Transform former setting into pyramid_multiauth config:
                is_already_set = 'basicauth' in settings['multiauth.policies']
                if asbool(settings.pop(old)) and not is_already_set:
                    settings['multiauth.policies'] += ' basicauth'
            else:
                settings[new] = settings.pop(old)

    config.add_settings(settings)


def includeme(config):
    load_default_settings(config, DEFAULT_SETTINGS)
    settings = config.get_settings()

    # Add CORS settings to the base cliquet Service class.
    cors_origins = settings['cliquet.cors_origins']
    Service.cors_origins = tuple(aslist(cors_origins))
    Service.default_cors_headers = ('Backoff', 'Retry-After', 'Alert')

    # Heartbeat registry.
    config.registry.heartbeats = {}

    # Setup components.
    for step in aslist(settings['cliquet.initialization_sequence']):
        step_func = config.maybe_dotted(step)
        step_func(config)

    # Setup cornice.
    config.include("cornice")

    # Scan views.
    config.scan("cliquet.views")

    # Give sign of life.
    msg = "%(cliquet.project_name)s %(cliquet.project_version)s starting."
    logger.info(msg % settings)
