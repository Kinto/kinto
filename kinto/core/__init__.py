"""Main entry point
"""
import pkg_resources

from cornice import Service as CorniceService
from pyramid.settings import aslist

from kinto.core import authentication
from kinto.core import errors
from kinto.core import events
from kinto.core.initialization import (  # NOQA
    initialize, install_middlewares,
    load_default_settings)
from kinto.core.utils import (
    follow_subrequest, current_service, current_resource_name)
from kinto.core.logs import logger


# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution('kinto').version  # FIXME?


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
    'error_info_link': 'https://github.com/Kinto/kinto/issues/',
    'http_host': None,
    'http_scheme': None,
    'id_generator': 'kinto.core.storage.generators.UUID4',
    'includes': '',
    'initialization_sequence': (
        'kinto.core.initialization.setup_request_bound_data',
        'kinto.core.initialization.setup_json_serializer',
        'kinto.core.initialization.setup_logging',
        'kinto.core.initialization.setup_storage',
        'kinto.core.initialization.setup_permission',
        'kinto.core.initialization.setup_cache',
        'kinto.core.initialization.setup_requests_scheme',
        'kinto.core.initialization.setup_vary_headers',
        'kinto.core.initialization.setup_version_redirection',
        'kinto.core.initialization.setup_deprecation',
        'kinto.core.initialization.setup_authentication',
        'kinto.core.initialization.setup_backoff',
        'kinto.core.initialization.setup_statsd',
        'kinto.core.initialization.setup_listeners',
        'kinto.core.events.setup_transaction_hook',
    ),
    'event_listeners': '',
    'logging_renderer': 'kinto.core.logs.ClassicLogRenderer',
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
    'statsd_prefix': 'kinto.core',
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
    'multiauth.groupfinder': 'kinto.core.authorization.groupfinder',
    'multiauth.policies': 'basicauth',
    'multiauth.policy.basicauth.use': ('kinto.core.authentication.'
                                       'BasicAuthAuthenticationPolicy'),
    'multiauth.authorization_policy': ('kinto.core.authorization.'
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

    # Add CORS settings to the base kinto.core Service class.
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

    # Include plugins after init, unlike pyramid includes.
    includes = aslist(settings['includes'])
    for app in includes:
        config.include(app)

    # # Show settings to output.
    # for key, value in settings.items():
    #     logger.info('Using %s = %s' % (key, value))

    # Scan views.
    config.scan("kinto.core.views")

    # Give sign of life.
    msg = "%(project_name)s %(project_version)s starting."
    logger.info(msg % settings)
