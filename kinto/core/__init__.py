"""Main entry point
"""
import logging
import pkg_resources
import tempfile

from cornice import Service as CorniceService
from pyramid.settings import aslist

from kinto.core import errors
from kinto.core import events
from kinto.core.initialization import (  # NOQA
    initialize, install_middlewares,
    load_default_settings)
from kinto.core.utils import (
    follow_subrequest, current_service, current_resource_name,
    prefixed_userid, prefixed_principals, log_context)


logger = logging.getLogger(__name__)


# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution('kinto').version  # FIXME?

DEFAULT_SETTINGS = {
    'backoff': None,
    'batch_max_requests': 25,
    'cache_backend': '',
    'cache_url': '',
    'cache_pool_size': 25,
    'cache_prefix': '',
    'cache_max_size_bytes': 524288,
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
        'kinto.core.initialization.setup_version_redirection',
        'kinto.core.initialization.setup_deprecation',
        'kinto.core.initialization.setup_authentication',
        'kinto.core.initialization.setup_backoff',
        'kinto.core.initialization.setup_statsd',
        'kinto.core.initialization.setup_listeners',
        'kinto.core.events.setup_transaction_hook',
    ),
    'event_listeners': '',
    'heartbeat_timeout_seconds': 10,
    'newrelic_config': None,
    'newrelic_env': 'dev',
    'paginate_by': None,
    'pagination_token_validity_seconds': 10 * 60,
    'permission_backend': '',
    'permission_url': '',
    'permission_pool_size': 25,
    'profiler_dir': tempfile.gettempdir(),
    'profiler_enabled': False,
    'project_docs': '',
    'project_name': '',
    'project_version': '',
    'readonly': False,
    'retry_after_seconds': 30,
    'statsd_backend': 'kinto.core.statsd',
    'statsd_prefix': 'kinto.core',
    'statsd_url': None,
    'storage_backend': '',
    'storage_url': '',
    'storage_max_fetch_size': 10000,
    'storage_pool_size': 25,
    'tm.annotate_user': False,  # Do annotate transactions with the user-id.
    'transaction_per_request': True,
    'userid_hmac_secret': '',
    'version_json_path': 'version.json',
    'version_prefix_redirect_enabled': True,
    'trailing_slash_redirect_enabled': True,
    'multiauth.groupfinder': 'kinto.core.authorization.groupfinder',
    'multiauth.policies': 'basicauth',
    'multiauth.policy.basicauth.use': ('kinto.core.authentication.'
                                       'BasicAuthAuthenticationPolicy'),
    'multiauth.authorization_policy': ('kinto.core.authorization.'
                                       'AuthorizationPolicy'),
}


class Service(CorniceService):
    """Subclass of the default cornice service.

    This is useful in order to attach specific behaviours without monkey
    patching the default cornice service (which would impact other uses of it)
    """
    default_cors_headers = ('Backoff', 'Retry-After', 'Alert',
                            'Content-Length')

    def error_handler(self, request):
        return errors.json_error_handler(request)

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
            error_msg = "The '{}' API capability was already registered ({})."
            raise ValueError(error_msg.format(identifier, existing))

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

    # Setup cornice api documentation
    config.include("cornice_swagger")

    # Per-request transaction.
    config.include("pyramid_tm")

    # Add CORS settings to the base kinto.core Service class.
    Service.init_from_settings(settings)

    # Setup components.
    for step in aslist(settings['initialization_sequence']):
        step_func = config.maybe_dotted(step)
        step_func(config)

    # Custom helpers.
    config.add_request_method(log_context)
    config.add_request_method(follow_subrequest)
    config.add_request_method(prefixed_userid, property=True)
    config.add_request_method(prefixed_principals, reify=True)
    config.add_request_method(lambda r: {
        'id': r.prefixed_userid,
        'principals': r.prefixed_principals},
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
    #     logger.info('Using {} = {}'.format(key, value))

    # Scan views.
    config.scan("kinto.core.views")

    # Give sign of life.
    msg = "Running {project_name} {project_version}."
    logger.info(msg.format_map(settings))
