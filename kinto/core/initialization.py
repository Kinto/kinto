import warnings
from datetime import datetime
from dateutil import parser as dateparser

import structlog
from pyramid.events import NewRequest, NewResponse
from pyramid.exceptions import ConfigurationError
from pyramid.httpexceptions import HTTPTemporaryRedirect, HTTPGone
from pyramid.renderers import JSON as JSONRenderer
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.settings import asbool, aslist
from pyramid_multiauth import (MultiAuthenticationPolicy,
                               MultiAuthPolicySelected)
try:
    import newrelic.agent
except ImportError:  # pragma: no cover
    newrelic = None
try:
    from werkzeug.contrib.profiler import ProfilerMiddleware
except ImportError:  # pragma: no cover
    pass

from kinto.core import errors
from kinto.core import utils
from kinto.core import statsd
from kinto.core import cache
from kinto.core import storage
from kinto.core import permission
from kinto.core.logs import logger
from kinto.core.events import ResourceRead, ResourceChanged, ACTIONS


def setup_request_bound_data(config):
    """Attach custom data on request object, and share it with parent
    requests during batch."""
    def attach_bound_data(request):
        parent = getattr(request, 'parent', None)
        return parent.bound_data if parent else {}

    config.add_request_method(attach_bound_data, name='bound_data', reify=True)


def setup_json_serializer(config):
    import requests
    import webob

    # Monkey patch to use ujson
    webob.request.json = utils.json
    requests.models.json = utils.json

    # Override json renderer using ujson
    renderer = JSONRenderer(serializer=utils.json_serializer)
    config.add_renderer('json', renderer)


def setup_version_redirection(config):
    """Add a view which redirects to the current version of the API.
    """
    settings = config.get_settings()
    redirect_enabled = settings['version_prefix_redirect_enabled']
    version_prefix_redirection_enabled = asbool(redirect_enabled)

    route_prefix = config.route_prefix
    config.registry.route_prefix = route_prefix

    # Redirect to the current version of the API if the prefix isn't used.
    # Do not redirect if kinto.version_prefix_redirect_enabled is set to
    # False.
    if not version_prefix_redirection_enabled:
        return

    def _redirect_to_version_view(request):
        path = request.matchdict['path']
        querystring = request.url[(request.url.rindex(request.path) +
                                   len(request.path)):]
        redirect = '/%s/%s%s' % (route_prefix, path, querystring)
        raise HTTPTemporaryRedirect(redirect)

    # Disable the route prefix passed by the app.
    config.route_prefix = None

    config.add_route(name='redirect_to_version',
                     pattern='/{path:(?!v[0-9]+).*}')

    config.add_view(view=_redirect_to_version_view,
                    route_name='redirect_to_version',
                    permission=NO_PERMISSION_REQUIRED)

    config.route_prefix = route_prefix


def setup_authentication(config):
    """Let pyramid_multiauth manage authentication and authorization
    from configuration.
    """
    config.include('pyramid_multiauth')

    # Track policy used, for prefixing user_id and for logging.
    def on_policy_selected(event):
        authn_type = event.policy_name.lower()
        event.request.authn_type = authn_type
        event.request.selected_userid = event.userid
        # Add authentication info to context.
        logger.bind(uid=event.userid, authn_type=authn_type)

    config.add_subscriber(on_policy_selected, MultiAuthPolicySelected)


def setup_backoff(config):
    """Attach HTTP requests/responses objects.

    This is useful to attach objects to the request object for easier
    access, and to pre-process responses.
    """
    def on_new_response(event):
        # Add backoff in response headers.
        backoff = config.registry.settings['backoff']
        if backoff is not None:
            backoff = utils.encode_header('%s' % backoff)
            event.response.headers['Backoff'] = backoff

    config.add_subscriber(on_new_response, NewResponse)


def setup_requests_scheme(config):
    """Force server scheme, host and port at the application level."""
    settings = config.get_settings()

    http_scheme = settings['http_scheme']
    http_host = settings['http_host']

    def on_new_request(event):
        if http_scheme:
            event.request.scheme = http_scheme
        if http_host:
            event.request.host = http_host

    if http_scheme or http_host:
        config.add_subscriber(on_new_request, NewRequest)


def setup_vary_headers(config):
    """Add Vary headers to each response."""
    settings = config.get_settings()

    vary = aslist(settings.get('vary', 'Authorization'))

    def on_new_request(event):
        def vary_callback(request, response):
            response.vary = vary
        event.request.add_response_callback(vary_callback)

    config.add_subscriber(on_new_request, NewRequest)


def setup_deprecation(config):
    config.add_tween("kinto.core.initialization._end_of_life_tween_factory")


def _end_of_life_tween_factory(handler, registry):
    """Pyramid tween to handle service end of life."""
    deprecation_msg = ("The service you are trying to connect no longer exists"
                       " at this location.")

    def eos_tween(request):
        eos_date = registry.settings['eos']
        eos_url = registry.settings['eos_url']
        eos_message = registry.settings['eos_message']
        if not eos_date:
            return handler(request)

        eos_date = dateparser.parse(eos_date)
        if eos_date > datetime.now():
            code = "soft-eol"
            request.response = handler(request)
        else:
            code = "hard-eol"
            request.response = errors.http_error(
                HTTPGone(),
                errno=errors.ERRORS.SERVICE_DEPRECATED,
                message=deprecation_msg)

        errors.send_alert(request, eos_message, url=eos_url, code=code)
        return request.response

    return eos_tween


def setup_storage(config):
    settings = config.get_settings()

    id_generator = config.maybe_dotted(settings['id_generator'])
    config.registry.id_generator = id_generator()

    storage_mod = settings['storage_backend']
    if not storage_mod:
        return

    storage_mod = config.maybe_dotted(storage_mod)
    backend = storage_mod.load_from_config(config)
    if not isinstance(backend, storage.StorageBase):
        raise ConfigurationError("Invalid storage backend: %s" % backend)
    config.registry.storage = backend

    heartbeat = storage.heartbeat(backend)
    config.registry.heartbeats['storage'] = heartbeat


def setup_permission(config):
    settings = config.get_settings()
    permission_mod = settings['permission_backend']
    if not permission_mod:
        return

    permission_mod = config.maybe_dotted(permission_mod)
    backend = permission_mod.load_from_config(config)
    if not isinstance(backend, permission.PermissionBase):
        raise ConfigurationError("Invalid permission backend: %s" % backend)
    config.registry.permission = backend

    heartbeat = permission.heartbeat(backend)
    config.registry.heartbeats['permission'] = heartbeat


def setup_cache(config):
    settings = config.get_settings()
    cache_mod = settings['cache_backend']
    if not cache_mod:
        return

    cache_mod = config.maybe_dotted(cache_mod)
    backend = cache_mod.load_from_config(config)
    if not isinstance(backend, cache.CacheBase):
        raise ConfigurationError("Invalid cache backend: %s" % backend)
    config.registry.cache = backend

    heartbeat = cache.heartbeat(backend)
    config.registry.heartbeats['cache'] = heartbeat


def setup_statsd(config):
    settings = config.get_settings()
    config.registry.statsd = None

    if settings['statsd_url']:
        client = statsd.load_from_config(config)

        config.registry.statsd = client

        client.watch_execution_time(config.registry.cache, prefix='cache')
        client.watch_execution_time(config.registry.storage, prefix='storage')
        client.watch_execution_time(config.registry.permission,
                                    prefix='permission')

        # Commit so that configured policy can be queried.
        config.commit()
        policy = config.registry.queryUtility(IAuthenticationPolicy)
        if isinstance(policy, MultiAuthenticationPolicy):
            for name, subpolicy in policy.get_policies():
                client.watch_execution_time(subpolicy,
                                            prefix='authentication',
                                            classname=name)
        else:
            client.watch_execution_time(policy, prefix='authentication')

        def on_new_response(event):
            request = event.request

            # Count unique users.
            user_id = request.prefixed_userid
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
    if settings.get('newrelic_config'):
        ini_file = settings['newrelic_config']
        env = settings['newrelic_env']
        newrelic.agent.initialize(ini_file, env)
        app = newrelic.agent.WSGIApplicationWrapper(app)

    # Adds the Werkzeug profiler.
    if asbool(settings.get('profiler_enabled')):
        profile_dir = settings['profiler_dir']
        app = ProfilerMiddleware(app, profile_dir=profile_dir,
                                 restrictions=('*kinto.core*'))

    return app


def setup_logging(config):
    """Setup structured logging, and emit `request.summary` event on each
    request, as recommanded by Mozilla Services standard:

    * https://mana.mozilla.org/wiki/display/CLOUDSERVICES/Logging+Standard
    * http://12factor.net/logs
    """
    settings = config.get_settings()

    renderer_klass = config.maybe_dotted(settings['logging_renderer'])
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
                   lang=request.headers.get('Accept-Language'),
                   uid=None,
                   authn_type=None,
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
        if not hasattr(request, 'parent'):
            logger.info('request.summary')

    config.add_subscriber(on_new_response, NewResponse)


class EventActionFilter(object):
    def __init__(self, actions, config):
        actions = ACTIONS.from_string_list(actions)
        self.actions = [action.value for action in actions]

    def phash(self):
        return 'for_actions = %s' % (','.join(self.actions))

    def __call__(self, event):
        action = event.payload.get('action')
        return not action or action in self.actions


class EventResourceFilter(object):
    def __init__(self, resources, config):
        self.resources = resources

    def phash(self):
        return 'for_resources = %s' % (','.join(self.resources))

    def __call__(self, event):
        resource = event.payload.get('resource_name')
        return not resource or not self.resources or resource in self.resources


def setup_listeners(config):
    # Register basic subscriber predicates, to filter events.
    config.add_subscriber_predicate('for_actions', EventActionFilter)
    config.add_subscriber_predicate('for_resources', EventResourceFilter)

    write_actions = (ACTIONS.CREATE, ACTIONS.UPDATE, ACTIONS.DELETE)
    settings = config.get_settings()
    listeners = aslist(settings['event_listeners'])

    for name in listeners:
        logger.info('Setting up %r listener' % name)
        prefix = 'event_listeners.%s.' % name

        try:
            listener_mod = config.maybe_dotted(name)
            prefix = 'event_listeners.%s.' % name.split('.')[-1]
            listener = listener_mod.load_from_config(config, prefix)
        except (ImportError, AttributeError):
            listener_mod = config.maybe_dotted(settings[prefix + 'use'])
            listener = listener_mod.load_from_config(config, prefix)

        # If StatsD is enabled, monitor execution time of listeners.
        if getattr(config.registry, "statsd", None):
            statsd_client = config.registry.statsd
            key = 'listeners.%s' % name
            listener = statsd_client.timer(key)(listener.__call__)

        actions = aslist(settings.get(prefix + 'actions', ''))
        if len(actions) > 0:
            actions = ACTIONS.from_string_list(actions)
        else:
            actions = write_actions

        resource_names = aslist(settings.get(prefix + 'resources', ''))
        options = dict(for_actions=actions, for_resources=resource_names)

        if ACTIONS.READ in actions:
            config.add_subscriber(listener, ResourceRead, **options)
            if len(actions) == 1:
                return

        config.add_subscriber(listener, ResourceChanged, **options)


def load_default_settings(config, default_settings):
    """Read settings provided in Paste ini file, set default values and
    replace if defined as environment variable.
    """
    settings = config.get_settings()

    project_name = settings['project_name']

    def _prefixed_keys(key):
        unprefixed = key
        if key.startswith('kinto.') or key.startswith(project_name + '.'):
            unprefixed = key.split('.', 1)[1]
        project_prefix = project_name + '.' + unprefixed
        kinto_prefix = 'kinto.' + unprefixed
        return unprefixed, project_prefix, kinto_prefix

    # Fill settings with default values if not defined.
    for key, default_value in sorted(default_settings.items()):
        unprefixed, project_prefix, kinto_prefix = keys = _prefixed_keys(key)
        is_defined = len(set(settings.keys()).intersection(set(keys))) > 0
        if not is_defined:
            settings[unprefixed] = default_value

    for key, value in sorted(settings.items()):
        unprefixed, project_prefix, kinto_prefix = keys = _prefixed_keys(key)

        # Fail if not only one is defined.
        defined = set(settings.keys()).intersection(set(keys))
        distinct_values = set([str(settings[d]) for d in defined])

        if len(defined) > 1 and len(distinct_values) > 1:
            names = "', '".join(defined)
            raise ValueError("Settings '%s' are in conflict." % names)

        # Maintain backwards compatibility with old settings files that
        # have backend settings like cliquet.foo (which is now
        # kinto.core.foo).
        unprefixed, _, _ = _prefixed_keys(key)
        CONTAIN_CLIQUET_MODULE_NAMES = [
            'storage_backend',
            'cache_backend',
            'permission_backend',
            'logging_renderer',
        ]
        if unprefixed in CONTAIN_CLIQUET_MODULE_NAMES and \
                value.startswith('cliquet.'):
            new_value = value.replace('cliquet.', 'kinto.core.')
            logger.warn(
                "Backend settings referring to cliquet are DEPRECATED. "
                "Please update your {} setting to {} (was: {}).".format(
                    key, new_value, value))
            value = new_value

        # Override settings from OS env values.
        # e.g. HTTP_PORT, READINGLIST_HTTP_PORT, KINTO_HTTP_PORT
        from_env = utils.read_env(unprefixed, value)
        from_env = utils.read_env(project_prefix, from_env)
        from_env = utils.read_env(kinto_prefix, from_env)

        settings[unprefixed] = from_env

    config.add_settings(settings)


def initialize(config, version=None, project_name='', default_settings=None):
    """Initialize kinto.core with the given configuration, version and project
    name.

    This will basically include kinto.core in Pyramid and set route prefix
    based on the specified version.

    :param config: Pyramid configuration
    :type config: ~pyramid:pyramid.config.Configurator
    :param str version: Current project version (e.g. '0.0.1') if not defined
        in application settings.
    :param str project_name: Project name if not defined
        in application settings.
    :param dict default_settings: Override kinto.core default settings values.
    """
    from kinto.core import DEFAULT_SETTINGS

    settings = config.get_settings()

    project_name = settings.pop('kinto.project_name',
                                settings.get('project_name')) or project_name
    settings['project_name'] = project_name
    if not project_name:
        warnings.warn('No value specified for `project_name`')

    kinto_core_defaults = DEFAULT_SETTINGS.copy()

    if default_settings:
        kinto_core_defaults.update(default_settings)

    load_default_settings(config, kinto_core_defaults)

    # Override project version from settings.
    project_version = settings.get('project_version') or version
    if not project_version:
        error_msg = "Invalid project version: %s" % project_version
        raise ConfigurationError(error_msg)
    settings['project_version'] = project_version = str(project_version)

    # HTTP API version.
    http_api_version = settings.get('http_api_version')
    if http_api_version is None:
        # The API version is derivated from the module version if not provided.
        http_api_version = '.'.join(project_version.split('.')[0:2])
    settings['http_api_version'] = http_api_version = str(http_api_version)
    api_version = 'v%s' % http_api_version.split('.')[0]

    # Include kinto.core views with the correct api version prefix.
    config.include("kinto.core", route_prefix=api_version)
    config.route_prefix = api_version
