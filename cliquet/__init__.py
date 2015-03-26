"""Main entry point
"""
import datetime
import warnings

from dateutil import parser as dateparser
import pkg_resources
import requests
import structlog
import webob
try:
    import raven
except ImportError:
    pass  # NOQA

from cornice import Service
from pyramid.events import NewRequest, NewResponse
from pyramid.httpexceptions import HTTPTemporaryRedirect, HTTPGone
from pyramid.renderers import JSON as JSONRenderer
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.interfaces import IAuthenticationPolicy
from pyramid_multiauth import MultiAuthenticationPolicy
from pyramid.settings import asbool, aslist

# Main Cliquet logger.
logger = structlog.get_logger()

from cliquet import authentication
from cliquet import errors
from cliquet import logs as cliquet_logs
from cliquet import statsd
from cliquet import utils


# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# The API version is derivated from the module version.
API_VERSION = 'v%s' % __version__.split('.')[0]


DEFAULT_SETTINGS = {
    'fxa-oauth.cache_ttl_seconds': 5 * 60,
    'fxa-oauth.client_id': None,
    'fxa-oauth.client_secret': None,
    'fxa-oauth.oauth_uri': None,
    'fxa-oauth.scope': 'profile',
    'fxa-oauth.state.ttl_seconds': 3600,  # 1 hour
    'fxa-oauth.webapp.authorized_domains': '',
    'fxa-oauth.relier.enabled': True,
    'cliquet.backoff': None,
    'cliquet.basic_auth_enabled': False,
    'cliquet.batch_max_requests': 25,
    'cliquet.delete_collection_enabled': True,
    'cliquet.eos': None,
    'cliquet.eos_message': None,
    'cliquet.eos_url': None,
    'cliquet.http_scheme': None,
    'cliquet.http_host': None,
    'cliquet.logging_renderer': 'cliquet.logs.ClassicLogRenderer',
    'cliquet.paginate_by': None,
    'cliquet.project_docs': '',
    'cliquet.project_name': '',
    'cliquet.project_version': '',
    'cliquet.retry_after_seconds': 30,
    'cliquet.cache_backend': 'cliquet.cache.redis',
    'cliquet.cache_url': '',
    'cliquet.cache_pool_maxconn': 50,
    'cliquet.storage_backend': 'cliquet.storage.redis',
    'cliquet.storage_url': '',
    'cliquet.storage_pool_maxconn': 50,
    'cliquet.storage_max_fetch_size': 10000,
    'cliquet.userid_hmac_secret': '',
    'cliquet.sentry_url': None,
    'cliquet.sentry_projects': '',
    'cliquet.statsd_url': None,
    'cliquet.statsd_prefix': 'cliquet'
}


def monkey_patch_json(config):
    # Monkey patch to use ujson
    webob.request.json = utils.json
    requests.models.json = utils.json

    # Override json renderer using ujson
    renderer = JSONRenderer(serializer=lambda v, **kw: utils.json.dumps(v))
    config.add_renderer('json', renderer)


def load_default_settings(config):
    """Read settings provided in Paste ini file, set default values and
    replace if defined as environment variable.
    """
    settings = config.get_settings()
    for key, value in DEFAULT_SETTINGS.items():
        configured = settings.get(key, value)
        settings[key] = utils.read_env(key, configured)
    config.add_settings(settings)


def handle_api_redirection(config):
    """Add a view which redirects to the current version of the API.
    """
    # Disable the route prefix passed by the app.
    route_prefix = config.route_prefix
    config.route_prefix = None

    def _redirect_to_version_view(request):
        raise HTTPTemporaryRedirect(
            '/%s/%s' % (route_prefix, request.matchdict['path']))

    # Redirect to the current version of the API if the prefix isn't used.
    config.add_route(name='redirect_to_version',
                     pattern='/{path:(?!%s).*}' % route_prefix)

    config.add_view(view=_redirect_to_version_view,
                    route_name='redirect_to_version',
                    permission=NO_PERMISSION_REQUIRED)

    config.route_prefix = route_prefix


def set_auth(config):
    """Define the authentication and authorization policies.
    """
    policies = [
        authentication.Oauth2AuthenticationPolicy(config),
        authentication.BasicAuthAuthenticationPolicy(),
    ]
    authn_policy = MultiAuthenticationPolicy(policies)
    authz_policy = authentication.AuthorizationPolicy()

    config.set_authorization_policy(authz_policy)
    config.set_authentication_policy(authn_policy)
    config.set_default_permission('readwrite')
    config.commit()


def attach_http_objects(config):
    """Attach HTTP requests/responses objects.

    This is useful to attach objects to the request object for easier
    access, and to pre-process responses.
    """

    def on_new_request(event):
        # Attach objects on requests for easier access.
        event.request.db = config.registry.storage
        event.request.cache = config.registry.cache

    config.add_subscriber(on_new_request, NewRequest)

    def on_new_response(event):
        # Add backoff in response headers.
        backoff = '%s' % config.registry.settings['cliquet.backoff']
        if backoff is not None:
            event.request.response.headers['Backoff'] = backoff.encode('utf-8')

    config.add_subscriber(on_new_response, NewResponse)


def force_requests_url(config):
    """Force server scheme, host and port at the application level."""
    settings = config.get_settings()

    http_scheme = settings['cliquet.http_scheme']
    http_host = settings['cliquet.http_host']

    def on_new_request(event):
        if http_scheme:
            event.request.scheme = http_scheme
        if http_host:
            event.request.host = http_host

    if http_scheme or http_host:
        config.add_subscriber(on_new_request, NewRequest)


def end_of_life_tween_factory(handler, registry):
    """Pyramid tween to handle service end of life."""

    deprecated_response = errors.http_error(
        HTTPGone(),
        errno=errors.ERRORS.SERVICE_DEPRECATED,
        message="The service you are trying to connect no longer exists "
                "at this location.")

    def eos_tween(request):
        eos_date = registry.settings['cliquet.eos']
        eos_url = registry.settings['cliquet.eos_url']
        eos_message = registry.settings['cliquet.eos_message']
        if eos_date:
            eos_date = dateparser.parse(eos_date)
            alert = {}
            if eos_url is not None:
                alert['url'] = eos_url

            if eos_message is not None:
                alert['message'] = eos_message

            if eos_date > datetime.datetime.now():
                alert['code'] = "soft-eol"
                response = handler(request)
            else:
                response = deprecated_response
                alert['code'] = "hard-eol"
            response.headers['Alert'] = utils.json.dumps(alert)
            return response
        return handler(request)
    return eos_tween


def handle_sentry(config):
    settings = config.get_settings()

    if settings['cliquet.sentry_url']:
        extra_projects = aslist(settings['cliquet.sentry_projects'])
        raven_client = raven.Client(
            settings['cliquet.sentry_url'],
            include_paths=['cornice', 'cliquet'] + extra_projects,
            release=settings['cliquet.project_version'])

        msg = "%(cliquet.project_name)s %(cliquet.project_version)s starting."
        raven_client.captureMessage(msg % settings)


def handle_statsd(config):
    settings = config.get_settings()

    if settings['cliquet.statsd_url']:
        client = statsd.load_from_config(config)

        client.watch_execution_time(config.registry.cache, prefix='cache')
        client.watch_execution_time(config.registry.storage, prefix='storage')

        policy = config.registry.queryUtility(IAuthenticationPolicy)
        client.watch_execution_time(policy, prefix='authentication')

        return client


def includeme(config):
    # Monkey Patch Cornice Service to setup the global CORS configuration.
    Service.cors_origins = ('*',)
    Service.default_cors_headers = ('Backoff', 'Retry-After', 'Alert')

    monkey_patch_json(config)

    load_default_settings(config)
    settings = config.get_settings()

    # Configure cliquet logging.
    cliquet_logs.setup_logging(config)

    force_requests_url(config)
    handle_api_redirection(config)
    config.add_tween("cliquet.end_of_life_tween_factory")

    # Handle sentry
    handle_sentry(config)

    storage = config.maybe_dotted(settings['cliquet.storage_backend'])
    config.registry.storage = storage.load_from_config(config)

    cache = config.maybe_dotted(settings['cliquet.cache_backend'])
    config.registry.cache = cache.load_from_config(config)

    set_auth(config)
    attach_http_objects(config)

    # Handle StatsD
    handle_statsd(config)

    kwargs = {}

    # Ignore FxA OAuth in case it's not activated (ignored by default).
    if not asbool(settings['fxa-oauth.relier.enabled']):
        kwargs['ignore'] = 'cliquet.views.oauth.relier'

    # Include cornice and discover views.
    config.include("cornice")
    config.scan("cliquet.views", **kwargs)


def initialize_cliquet(config, version=None, project_name=None):
    """Initialize Cliquet with the given configuration, version and project
    name.

    This will basically include cliquet in Pyramid and set route prefix based
    on the specified version.

    :param config: Pyramid configuration
    :type config: pyramid.config.Configurator
    :param version: Current project version (e.g. '0.0.1') if not defined
        in application settings.
    :type version: string
    :param project_name: Project name if not defined in application settings.
    :type project_name: string
    """
    settings = config.registry.settings

    # The API version is derivated from the module version.
    project_version = settings.get('cliquet.project_version') or version
    settings['cliquet.project_version'] = project_version
    try:
        api_version = 'v%s' % project_version.split('.')[0]
    except (AttributeError, ValueError):
        raise ValueError('Invalid project version')

    project_name = settings.get('cliquet.project_name') or project_name
    settings['cliquet.project_name'] = project_name
    if not project_name:
        warnings.warn('No value specified for `project_name`')

    # Include cliquet views with the correct api version prefix.
    config.include("cliquet", route_prefix=api_version)
    config.route_prefix = api_version
