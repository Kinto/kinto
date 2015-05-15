"""Main entry point
"""
import warnings
import pkg_resources

import structlog
from cornice import Service
from pyramid.settings import asbool, aslist

# Main Cliquet logger.
logger = structlog.get_logger()

from cliquet import utils
from cliquet.initialization import (  # NOQA
    initialize, initialize_cliquet, install_middlewares)


# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# The API version is derivated from the module version.
API_VERSION = 'v%s' % __version__.split('.')[0]


DEFAULT_SETTINGS = {
    'cliquet.backoff': None,
    'cliquet.basic_auth_enabled': False,
    'cliquet.batch_max_requests': 25,
    'cliquet.cache_backend': 'cliquet.cache.redis',
    'cliquet.cache_pool_size': 10,
    'cliquet.cache_url': '',
    'cliquet.cors_origins': '*',
    'cliquet.delete_collection_enabled': True,
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
    'fxa-oauth.cache_ttl_seconds': 5 * 60,
    'fxa-oauth.client_id': None,
    'fxa-oauth.client_secret': None,
    'fxa-oauth.heartbeat_timeout_seconds': 3,
    'fxa-oauth.oauth_uri': None,
    'fxa-oauth.relier.enabled': True,
    'fxa-oauth.scope': 'profile',
    'fxa-oauth.state.ttl_seconds': 3600,  # 1 hour
    'fxa-oauth.webapp.authorized_domains': '',
}


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
    ]
    for old, new in deprecated_settings:
        if old in settings:
            msg = "'%s' setting is deprecated. Use '%s' instead." % (old, new)
            warnings.warn(msg, DeprecationWarning)
            settings[new] = settings.pop(old)

    config.add_settings(settings)


def includeme(config):
    load_default_settings(config, DEFAULT_SETTINGS)
    settings = config.get_settings()

    # Monkey Patch Cornice Service to setup the global CORS configuration.
    # XXX: Refactor @crud decorator and inherit Service instead.
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
    # Ignore FxA OAuth in case it's not activated (ignored by default).
    kwargs = {}
    if not asbool(settings['fxa-oauth.relier.enabled']):
        kwargs['ignore'] = 'cliquet.views.oauth.relier'
    config.scan("cliquet.views", **kwargs)

    # Give sign of life.
    msg = "%(cliquet.project_name)s %(cliquet.project_version)s starting."
    logger.info(msg % settings)
