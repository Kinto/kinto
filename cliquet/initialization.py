import warnings
from datetime import datetime
from dateutil import parser as dateparser

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

from cliquet import errors
from cliquet import logger
from cliquet import utils
from cliquet import statsd
from cliquet import authorization

from pyramid.events import NewRequest, NewResponse
from pyramid.httpexceptions import HTTPTemporaryRedirect, HTTPGone
from pyramid.renderers import JSON as JSONRenderer
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.settings import asbool
from pyramid_multiauth import MultiAuthPolicySelected


def setup_json_serializer(config):
    # Monkey patch to use ujson
    webob.request.json = utils.json
    requests.models.json = utils.json

    # Override json renderer using ujson
    renderer = JSONRenderer(serializer=lambda v, **kw: utils.json.dumps(v))
    config.add_renderer('json', renderer)


def setup_version_redirection(config):
    """Add a view which redirects to the current version of the API.
    """
    settings = config.get_settings()
    redirect_enabled = settings['cliquet.version_prefix_redirect_enabled']
    version_prefix_redirection_enabled = asbool(redirect_enabled)

    # Redirect to the current version of the API if the prefix isn't used.
    # Do not redirect if cliquet.version_prefix_redirect_enabled is set to
    # False.
    if not version_prefix_redirection_enabled:
        return

    def _redirect_to_version_view(request):
        raise HTTPTemporaryRedirect(
            '/%s/%s' % (route_prefix, request.matchdict['path']))

    # Disable the route prefix passed by the app.
    route_prefix = config.route_prefix
    config.route_prefix = None

    config.add_route(name='redirect_to_version',
                     pattern='/{path:(?!%s).*}' % route_prefix)

    config.add_view(view=_redirect_to_version_view,
                    route_name='redirect_to_version',
                    permission=NO_PERMISSION_REQUIRED)

    config.route_prefix = route_prefix


def setup_authentication(config):
    """Let pyramid_multiauth manage authentication and authorization
    from configuration.
    """
    config.include('pyramid_multiauth')
    # By default, permissions are handled dynamically.
    config.set_default_permission(authorization.DYNAMIC)

    # Track policy for logging.
    def on_policy_selected(event):
        value = event.policy.__class__.__name__
        value = value.replace('Authentication', '').replace('Policy', '')
        event.request.authn_type = value

    config.add_subscriber(on_policy_selected, MultiAuthPolicySelected)


def setup_backoff(config):
    """Attach HTTP requests/responses objects.

    This is useful to attach objects to the request object for easier
    access, and to pre-process responses.
    """
    def on_new_response(event):
        # Add backoff in response headers.
        backoff = config.registry.settings['cliquet.backoff']
        if backoff is not None:
            backoff = ('%s' % backoff).encode('utf-8')
            event.request.response.headers['Backoff'] = backoff

    config.add_subscriber(on_new_response, NewResponse)


def setup_requests_scheme(config):
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


def setup_deprecation(config):
    config.add_tween("cliquet.initialization._end_of_life_tween_factory")


def _end_of_life_tween_factory(handler, registry):
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

            if eos_date > datetime.now():
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


def setup_storage(config):
    settings = config.get_settings()
    storage = config.maybe_dotted(settings['cliquet.storage_backend'])
    config.registry.storage = storage.load_from_config(config)
    config.registry.heartbeats['storage'] = config.registry.storage.ping
    id_generator = config.maybe_dotted(settings['cliquet.id_generator'])
    config.registry.id_generator = id_generator()


def setup_permission(config):
    settings = config.get_settings()
    permission = config.maybe_dotted(settings['cliquet.permission_backend'])
    config.registry.permission = permission.load_from_config(config)
    config.registry.heartbeats['permission'] = config.registry.permission.ping


def setup_cache(config):
    settings = config.get_settings()
    cache = config.maybe_dotted(settings['cliquet.cache_backend'])
    config.registry.cache = cache.load_from_config(config)
    config.registry.heartbeats['cache'] = config.registry.cache.ping


def setup_statsd(config):
    settings = config.get_settings()

    if settings['cliquet.statsd_url']:
        client = statsd.load_from_config(config)

        client.watch_execution_time(config.registry.cache, prefix='cache')
        client.watch_execution_time(config.registry.storage, prefix='storage')

        # Commit so that configured policy can be queried.
        config.commit()
        policy = config.registry.queryUtility(IAuthenticationPolicy)
        client.watch_execution_time(policy, prefix='authentication')

        def on_new_response(event):
            request = event.request

            # Count unique users.
            user_id = request.authenticated_userid
            if user_id:
                client.count('users', unique=user_id)

            # Count authentication verifications.
            if hasattr(request, 'authn_type'):
                client.count('%s.%s' % ('authn_type', request.authn_type))

            # Count view calls.
            pattern = request.matched_route.pattern
            services = request.registry.cornice_services
            service = services.get(pattern)
            if service:
                client.count('view.%s.%s' % (service.name, request.method))

        config.add_subscriber(on_new_response, NewResponse)

        return client


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


def setup_logging(config):
    """Setup structured logging, and emit `request.summary` event on each
    request, as recommanded by Mozilla Services standard:

    * https://mana.mozilla.org/wiki/display/CLOUDSERVICES/Logging+Standard
    * http://12factor.net/logs
    """
    settings = config.get_settings()

    renderer_klass = config.maybe_dotted(settings['cliquet.logging_renderer'])
    renderer = renderer_klass(settings)

    structlog.configure(
        # Share the logger context by thread.
        context_class=structlog.threadlocal.wrap_dict(dict),
        # Integrate with Pyramid logging facilities.
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        # Setup logger output format.
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.processors.format_exc_info,
            renderer,
        ])

    def on_new_request(event):
        request = event.request
        # Save the time the request was received by the server.
        event.request._received_at = utils.msec_time()

        # New logger context, with infos for request summary logger.
        logger.new(agent=request.headers.get('User-Agent'),
                   path=event.request.path,
                   method=request.method,
                   querystring=dict(request.GET),
                   uid=request.authenticated_userid,
                   lang=request.headers.get('Accept-Language'),
                   authn_type=getattr(request, 'authn_type', None),
                   errno=None)

    config.add_subscriber(on_new_request, NewRequest)

    def on_new_response(event):
        response = event.response
        request = event.request

        # Compute the request processing time in msec (-1 if unknown)
        current = utils.msec_time()
        duration = current - getattr(request, '_received_at', current - 1)
        isotimestamp = datetime.fromtimestamp(current/1000).isoformat()

        # Bind infos for request summary logger.
        logger.bind(time=isotimestamp,
                    code=response.status_code,
                    t=duration)

        # Ouput application request summary.
        logger.info('request.summary')

    config.add_subscriber(on_new_response, NewResponse)


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
