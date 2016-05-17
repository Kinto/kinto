"""Main entry point
"""
import pkg_resources

from cornice import Service as CorniceService
from pyramid.settings import aslist

from cliquet import authentication
from cliquet import errors
from cliquet import events
from cliquet.initialization import (  # NOQA
    initialize, initialize_cliquet, install_middlewares,
    load_default_settings)
from cliquet.utils import (
    follow_subrequest, current_service, current_resource_name)
from cliquet.logs import logger


# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version


# The protocol version, incremented when HTTP API has breaking change.
# - v1: initial version.
# - v2: with "data" attribute in payloads and ETags.
PROTOCOL_VERSION = '2'


DEFAULT_SETTINGS = {
    'backoff': None,
    'batch_max_requests': 25,
    'cache_backend': '',
    'cache_url': '',
    'cache_pool_size': 25,
    'cache_prefix': '',
    'cors_origins': '*',
    'cors_max_age_seconds': 3600,
    'eos': None,
    'eos_message': None,
    'eos_url': None,
    'error_info_link': 'https://github.com/mozilla-services/cliquet/issues/',
    'http_host': None,
    'http_scheme': None,
    'id_generator': 'cliquet.storage.generators.UUID4',
    'includes': '',
    'initialization_sequence': (
        'cliquet.initialization.setup_request_bound_data',
        'cliquet.initialization.setup_json_serializer',
        'cliquet.initialization.setup_logging',
        'cliquet.initialization.setup_storage',
        'cliquet.initialization.setup_permission',
        'cliquet.initialization.setup_cache',
        'cliquet.initialization.setup_requests_scheme',
        'cliquet.initialization.setup_vary_headers',
        'cliquet.initialization.setup_version_redirection',
        'cliquet.initialization.setup_deprecation',
        'cliquet.initialization.setup_authentication',
        'cliquet.initialization.setup_backoff',
        'cliquet.initialization.setup_statsd',
        'cliquet.initialization.setup_listeners',
        'cliquet.events.setup_transaction_hook',
    ),
    'event_listeners': '',
    'logging_renderer': 'cliquet.logs.ClassicLogRenderer',
    'newrelic_config': None,
    'newrelic_env': 'dev',
    'paginate_by': None,
    'permission_backend': '',
    'permission_url': '',
    'permission_pool_size': 25,
    'profiler_dir': '/tmp',
    'profiler_enabled': False,
    'project_docs': '',
    'project_name': '',
    'project_version': '',
    'readonly': False,
    'retry_after_seconds': 30,
    'statsd_prefix': 'cliquet',
    'statsd_url': None,
    'storage_backend': '',
    'storage_url': '',
    'storage_max_fetch_size': 10000,
    'storage_pool_size': 25,
    'tm.annotate_user': False,  # Do annotate transactions with the user-id.
    'transaction_per_request': True,
    'userid_hmac_secret': '',
    'version_prefix_redirect_enabled': True,
    'trailing_slash_redirect_enabled': True,
    'multiauth.groupfinder': 'cliquet.authorization.groupfinder',
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
    default_cors_headers = ('Backoff', 'Retry-After', 'Alert',
                            'Content-Length', 'Vary')

    def error_handler(self, error):
        return errors.json_error_handler(error)

    @classmethod
    def init_from_settings(cls, settings):
        cls.cors_origins = tuple(aslist(settings['cors_origins']))
        cors_max_age = settings['cors_max_age_seconds']
        cls.cors_max_age = int(cors_max_age) if cors_max_age else None


def includeme(config):
    settings = config.get_settings()

    # Heartbeat registry.
    config.registry.heartbeats = {}

    # Public settings registry.
    config.registry.public_settings = {'batch_max_requests', 'readonly'}

    # Directive to declare arbitrary API capabilities.
    def add_api_capability(config, identifier, description="", url="", **kw):
        existing = config.registry.api_capabilities.get(identifier)
        if existing:
            error_msg = "The '%s' API capability was already registered (%s)."
            raise ValueError(error_msg % (identifier, existing))

        capability = dict(description=description, url=url, **kw)
        config.registry.api_capabilities[identifier] = capability

    config.add_directive('add_api_capability', add_api_capability)
    config.registry.api_capabilities = {}

    # Resource events helpers.
    config.add_request_method(events.get_resource_events,
                              name='get_resource_events')
    config.add_request_method(events.notify_resource_event,
                              name='notify_resource_event')

    # Setup cornice.
    config.include("cornice")

    # Per-request transaction.
    config.include("pyramid_tm")

    # Add CORS settings to the base cliquet Service class.
    Service.init_from_settings(settings)

    # Setup components.
    for step in aslist(settings['initialization_sequence']):
        step_func = config.maybe_dotted(step)
        step_func(config)

    # Custom helpers.
    config.add_request_method(follow_subrequest)
    config.add_request_method(authentication.prefixed_userid, property=True)
    config.add_request_method(lambda r: {'id': r.prefixed_userid},
                              name='get_user_info')
    config.add_request_method(current_resource_name, reify=True)
    config.add_request_method(current_service, reify=True)
    config.commit()

    # Include cliquet plugins after init, unlike pyramid includes.
    includes = aslist(settings['includes'])
    for app in includes:
        config.include(app)

    # # Show settings to output.
    # for key, value in settings.items():
    #     logger.info('Using %s = %s' % (key, value))

    # Scan views.
    config.scan("cliquet.views")

    # Give sign of life.
    msg = "%(project_name)s %(project_version)s starting."
    logger.info(msg % settings)
