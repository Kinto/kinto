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
    import newrelic.agent
except ImportError:  # pragma: no cover
    pass

try:
    from werkzeug.contrib.profiler import ProfilerMiddleware
except ImportError:  # pragma: no cover
    pass


from cornice import Service
from pyramid.events import NewRequest, NewResponse
from pyramid.httpexceptions import HTTPTemporaryRedirect, HTTPGone
from pyramid.renderers import JSON as JSONRenderer
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.interfaces import IAuthenticationPolicy
from pyramid_multiauth import MultiAuthenticationPolicy
from pyramid.settings import asbool

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
    'cliquet.backoff': None,
    'cliquet.basic_auth_enabled': False,
    'cliquet.batch_max_requests': 25,
    'cliquet.cache_backend': 'cliquet.cache.redis',
    'cliquet.cache_pool_size': 10,
    'cliquet.cache_url': '',
    'cliquet.delete_collection_enabled': True,
    'cliquet.eos': None,
    'cliquet.eos_message': None,
    'cliquet.eos_url': None,
    'cliquet.http_host': None,
    'cliquet.http_scheme': None,
    'cliquet.id_generator': 'cliquet.storage.generators.UUID4',
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
    settings = config.get_settings()
    policies = [authentication.Oauth2AuthenticationPolicy(config), ]
    basic_auth_enabled = asbool(settings['cliquet.basic_auth_enabled'])
    if basic_auth_enabled:
        policies.append(authentication.BasicAuthAuthenticationPolicy())

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

    deprecation_msg = ("The service you are trying to connect no longer exists"
                       " at this location.")

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
                response = errors.http_error(
                    HTTPGone(),
                    errno=errors.ERRORS.SERVICE_DEPRECATED,
                    message=deprecation_msg)
                alert['code'] = "hard-eol"
            response.headers['Alert'] = utils.json.dumps(alert)
            return response
        return handler(request)
    return eos_tween


def handle_statsd(config):
    settings = config.get_settings()

    if settings['cliquet.statsd_url']:
        client = statsd.load_from_config(config)

        client.watch_execution_time(config.registry.cache, prefix='cache')
        client.watch_execution_time(config.registry.storage, prefix='storage')

        policy = config.registry.queryUtility(IAuthenticationPolicy)
        client.watch_execution_time(policy, prefix='authentication')

        def on_new_response(event):
            request = event.request

            # Count unique users.
            user_id = request.authenticated_userid
            if user_id:
                client.count('users', unique=user_id)

            # Count authentication verifications.
            if hasattr(request, 'auth_type'):
                client.count('%s.%s' % ('auth_type', request.auth_type))

            # Count view calls.
            pattern = request.matched_route.pattern
            services = request.registry.cornice_services
            service = services.get(pattern)
            if service:
                client.count('view.%s.%s' % (service.name, request.method))

        config.add_subscriber(on_new_response, NewResponse)

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

    storage = config.maybe_dotted(settings['cliquet.storage_backend'])
    config.registry.storage = storage.load_from_config(config)

    cache = config.maybe_dotted(settings['cliquet.cache_backend'])
    config.registry.cache = cache.load_from_config(config)

    id_generator = config.maybe_dotted(settings['cliquet.id_generator'])
    config.registry.id_generator = id_generator()

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

    # Give sign of life.
    msg = "%(cliquet.project_name)s %(cliquet.project_version)s starting."
    logger.info(msg % settings)


def initialize_cliquet(*args, **kwargs):
    message = ('cliquet.initialize_cliquet is now deprecated. '
               'Please use "cliquet.initialize" instead')

    warnings.warn(message, DeprecationWarning)
    initialize(*args, **kwargs)


def initialize(config, version=None, project_name=None, default_settings=None):
    """Initialize Cliquet with the given configuration, version and project
    name.

    This will basically include cliquet in Pyramid and set route prefix based
    on the specified version.

    :param config: Pyramid configuration
    :type config: ~pyramid:pyramid.config.Configurator
    :param str version: Current project version (e.g. '0.0.1') if not defined
        in application settings.
    :param str project_name: Project name if not defined
        in application settings.
    :param dict default_settings: Override cliquet default settings values.
    """
    if default_settings:
        config.add_settings(default_settings)

    settings = config.get_settings()

    # The API version is derivated from the module version.
    project_version = settings.get('cliquet.project_version') or version
    config.add_settings({'cliquet.project_version': project_version})
    try:
        api_version = 'v%s' % project_version.split('.')[0]
    except (AttributeError, ValueError):
        raise ValueError('Invalid project version')

    project_name = settings.get('cliquet.project_name') or project_name
    config.add_settings({'cliquet.project_name': project_name})
    if not project_name:
        warnings.warn('No value specified for `project_name`')

    # Include cliquet views with the correct api version prefix.
    config.include("cliquet", route_prefix=api_version)
    config.route_prefix = api_version


def install_middlewares(app, settings):
    "Install a set of middlewares defined in the ini file on the given app."

    # Setup new-relic.
    if settings.get('cliquet.newrelic_config'):
        ini_file = settings['cliquet.newrelic_config']
        env = settings['cliquet.newrelic_env']
        newrelic.agent.initialize(ini_file, env)
        app = newrelic.agent.WSGIApplicationWrapper(app)

    # Adds the Werkzeug profiler.
    if asbool(settings.get('cliquet.profiler_enabled')):
        profile_dir = settings['cliquet.profiler_dir'],
        app = ProfilerMiddleware(app, profile_dir=profile_dir,
                                 restrictions=('*cliquet*'))

    return app
