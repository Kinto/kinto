import logging
import random
import re
import warnings
from datetime import datetime

from dateutil import parser as dateparser
from dockerflow.logging import get_or_generate_request_id, request_id_context
from pyramid.events import ApplicationCreated, NewRequest, NewResponse
from pyramid.exceptions import ConfigurationError
from pyramid.httpexceptions import (
    HTTPBadRequest,
    HTTPGone,
    HTTPMethodNotAllowed,
    HTTPTemporaryRedirect,
)
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.renderers import JSON as JSONRenderer
from pyramid.response import Response
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.settings import asbool, aslist
from pyramid_multiauth import MultiAuthenticationPolicy, MultiAuthPolicySelected

from kinto.core import cache, errors, metrics, permission, storage, utils
from kinto.core.events import ACTIONS, ResourceChanged, ResourceRead


try:
    import newrelic.agent
except ImportError:  # pragma: no cover
    newrelic = None
try:
    from werkzeug.middleware.profiler import ProfilerMiddleware
except ImportError:  # pragma: no cover
    ProfilerMiddleware = False
try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.pyramid import PyramidIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
except ImportError:  # pragma: no cover
    sentry_sdk = None


logger = logging.getLogger(__name__)
summary_logger = logging.getLogger("request.summary")


def setup_request_bound_data(config):
    """Attach custom data on request object, and share it with parent
    requests during batch."""

    def attach_bound_data(request):
        parent = getattr(request, "parent", None)
        return parent.bound_data if parent else {}

    config.add_request_method(attach_bound_data, name="bound_data", reify=True)


def setup_json_serializer(config):
    import requests
    import webob

    # Monkey patch to use rapidjson
    webob.request.json = utils.json
    requests.models.json = utils.json

    # Override json renderer using rapidjson
    renderer = JSONRenderer(serializer=utils.json_serializer)
    config.add_renderer("ultrajson", renderer)  # See `kinto.core.Service`


def setup_csp_headers(config):
    """Content-Security-Policy HTTP response header helps reduce XSS risks on
    modern browsers by declaring, which dynamic resources are allowed to load.
    On APIs, we disable everything.
    """
    disable_all = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; "

    def on_new_response(event):
        event.response.headers.setdefault("Content-Security-Policy", disable_all)

    config.add_subscriber(on_new_response, NewResponse)


def restrict_http_methods_if_readonly(config):
    """Prevent write operations if server is configured as read-only.

    This is an additional layer of security on top of the verifications done
    in :method:`kinto.core.Resource.register_service`, in case an installed
    plugin does not take this setting into account in the definition of its
    ad-hoc Pyramid views.
    """
    settings = config.get_settings()

    def on_new_request(event):
        if event.request.method.lower() not in ("get", "head", "options"):
            raise HTTPMethodNotAllowed()

    if asbool(settings["readonly"]):
        config.add_subscriber(on_new_request, NewRequest)


def setup_version_redirection(config):
    """Add a view which redirects to the current version of the API."""
    settings = config.get_settings()
    redirect_enabled = settings["version_prefix_redirect_enabled"]
    version_prefix_redirection_enabled = asbool(redirect_enabled)
    cache_seconds = int(settings["version_prefix_redirect_ttl_seconds"])

    route_prefix = config.route_prefix
    config.registry.route_prefix = route_prefix

    # Redirect to the current version of the API if the prefix isn't used.
    # Do not redirect if kinto.version_prefix_redirect_enabled is set to
    # False.
    if not version_prefix_redirection_enabled:
        return

    def _redirect_to_version_view(request):
        if request.method.lower() == "options":
            # CORS responses should always have status 200.
            return utils.reapply_cors(request, Response())

        querystring = request.url[(request.url.rindex(request.path) + len(request.path)) :]
        redirect = f"/{route_prefix}{request.path}{querystring}"
        resp = HTTPTemporaryRedirect(redirect)
        if cache_seconds >= 0:
            resp.cache_expires(cache_seconds)
        raise resp

    # Disable the route prefix passed by the app.
    config.route_prefix = None

    config.add_route(name="redirect_to_version", pattern=r"/{path:(?!v[0-9]+)[^\r\n]*}")

    config.add_view(
        view=_redirect_to_version_view,
        route_name="redirect_to_version",
        permission=NO_PERMISSION_REQUIRED,
    )

    config.route_prefix = route_prefix


def setup_authentication(config):
    """Let pyramid_multiauth manage authentication and authorization
    from configuration.
    """
    config.include("pyramid_multiauth")
    settings = config.get_settings()

    policies = aslist(settings["multiauth.policies"])
    if "basicauth" in policies:
        config.include("kinto.core.authentication")

    # Track policy used, for prefixing user_id and for logging.
    def on_policy_selected(event):
        request = event.request
        # If the authn policy has a name attribute, we use it rather
        # than using the one specified in settings.
        authn_type = getattr(event.policy, "name", event.policy_name.lower())
        request.authn_type = authn_type
        request.selected_userid = event.userid
        # Add authentication info to context.
        request.log_context(uid=event.userid, authn_type=authn_type)

    config.add_subscriber(on_policy_selected, MultiAuthPolicySelected)


def setup_backoff(config):
    """Attach HTTP requests/responses objects.

    This is useful to attach objects to the request object for easier
    access, and to pre-process responses.
    """

    def on_new_response(event):
        # Add backoff in response headers.
        backoff = config.registry.settings["backoff"]
        if backoff is not None:
            backoff_percentage = config.registry.settings["backoff_percentage"]
            if backoff_percentage is not None:
                if random.random() < (float(backoff_percentage) / 100.0):
                    event.response.headers["Backoff"] = str(backoff)
            else:
                event.response.headers["Backoff"] = str(backoff)

    config.add_subscriber(on_new_response, NewResponse)


def setup_requests_scheme(config):
    """Force server scheme, host and port at the application level."""
    settings = config.get_settings()

    http_scheme = settings["http_scheme"]
    http_host = settings["http_host"]

    def on_new_request(event):
        if http_scheme:
            event.request.scheme = http_scheme
        if http_host:
            event.request.host = http_host

    if http_scheme or http_host:
        config.add_subscriber(on_new_request, NewRequest)


def setup_deprecation(config):
    config.add_tween("kinto.core.initialization._end_of_life_tween_factory")


def _end_of_life_tween_factory(handler, registry):
    """Pyramid tween to handle service end of life."""
    deprecation_msg = "The service you are trying to connect no longer exists at this location."

    def eos_tween(request):
        eos_date = registry.settings["eos"]
        eos_url = registry.settings["eos_url"]
        eos_message = registry.settings["eos_message"]
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
                message=deprecation_msg,
            )

        errors.send_alert(request, eos_message, url=eos_url, code=code)
        return utils.reapply_cors(request, request.response)

    return eos_tween


def setup_storage(config):
    settings = config.get_settings()

    # Id generators by resource name.
    config.registry.id_generators = {}
    for key, value in settings.items():
        m = re.match(r"^([^_]*)_?id_generator", key)
        if m is None:
            continue
        resource_name = m.group(1)
        id_generator = config.maybe_dotted(value)
        config.registry.id_generators[resource_name] = id_generator()

    storage_mod = settings["storage_backend"]
    if not storage_mod:
        return

    storage_mod = config.maybe_dotted(storage_mod)
    backend = storage_mod.load_from_config(config)
    if not isinstance(backend, storage.StorageBase):
        raise ConfigurationError(f"Invalid storage backend: {backend}")
    config.registry.storage = backend

    heartbeat = storage.heartbeat(backend)
    config.registry.heartbeats["storage"] = heartbeat


def setup_permission(config):
    settings = config.get_settings()
    permission_mod = settings["permission_backend"]
    if not permission_mod:
        return

    permission_mod = config.maybe_dotted(permission_mod)
    backend = permission_mod.load_from_config(config)
    if not isinstance(backend, permission.PermissionBase):
        raise ConfigurationError(f"Invalid permission backend: {backend}")
    config.registry.permission = backend

    heartbeat = permission.heartbeat(backend)
    config.registry.heartbeats["permission"] = heartbeat


def setup_cache(config):
    settings = config.get_settings()
    cache_mod = settings["cache_backend"]
    if not cache_mod:
        return

    cache_mod = config.maybe_dotted(cache_mod)
    backend = cache_mod.load_from_config(config)
    if not isinstance(backend, cache.CacheBase):
        raise ConfigurationError(f"Invalid cache backend: {backend}")
    config.registry.cache = backend

    heartbeat = cache.heartbeat(backend)
    config.registry.heartbeats["cache"] = heartbeat


def setup_sentry(config):
    settings = config.get_settings()

    # Note: SENTRY_DSN and SENTRY_ENV env variables will override
    # .ini values thanks to `load_default_settings()`.

    dsn = settings["sentry_dsn"]
    if dsn:  # pragma: no cover
        env_options = {}
        env = settings["sentry_env"]
        if env:
            env_options["environment"] = env

        breadcrumbs_level = settings["sentry_breadcrumbs_min_level"]
        events_level = settings["sentry_events_min_level"]
        sentry_sdk.init(
            dsn,
            integrations=[
                PyramidIntegration(),
                SqlalchemyIntegration(),
                LoggingIntegration(
                    # Logs to be captured as breadcrumbs (debug and above by default)
                    level=breadcrumbs_level,
                    # Logs to be catpured as events (warning and above by default)
                    event_level=events_level,
                ),
            ],
            **env_options,
        )

        def on_app_created(event):
            msg = "Running {project_name} {project_version}.".format_map(settings)
            sentry_sdk.capture_message(msg, "info")

        config.add_subscriber(on_app_created, ApplicationCreated)


def install_middlewares(app, settings):
    "Install a set of middlewares defined in the ini file on the given app."
    # Setup new-relic.
    if settings.get("newrelic_config"):
        ini_file = settings["newrelic_config"]
        env = settings["newrelic_env"]
        newrelic.agent.initialize(ini_file, env)
        app = newrelic.agent.WSGIApplicationWrapper(app)

    # Adds the Werkzeug profiler.
    if asbool(settings.get("profiler_enabled")):
        profile_dir = settings["profiler_dir"]
        app = ProfilerMiddleware(app, profile_dir=profile_dir, restrictions=("*kinto.core*"))

    return app


def setup_logging(config):
    """Setup structured logging, and emit `request.summary` event on each
    request, as recommended by Mozilla Services standard:

    * https://mana.mozilla.org/wiki/display/CLOUDSERVICES/Logging+Standard
    * http://12factor.net/logs
    """

    def on_new_request(event):
        request = event.request
        # Save the time the request was received by the server.
        event.request._received_at = utils.msec_time()

        try:
            # Pyramid fails if the URL contains invalid UTF-8 characters.
            request_path = event.request.path
        except UnicodeDecodeError:
            raise errors.http_error(
                HTTPBadRequest(),
                errno=errors.ERRORS.INVALID_PARAMETERS,
                message="Invalid URL path.",
            )

        rid = get_or_generate_request_id(headers=request.headers)
        request_id_context.set(rid)

        request.log_context(
            agent=request.headers.get("User-Agent"),
            path=request_path,
            method=request.method,
            lang=request.headers.get("Accept-Language"),
            rid=rid,
            errno=0,
        )
        qs = dict(errors.request_GET(request))
        if qs:
            request.log_context(querystring=qs)

        if summary_logger.level == logging.DEBUG:
            request.log_context(headers=dict(request.headers), body=request.body)

    config.add_subscriber(on_new_request, NewRequest)

    def on_new_response(event):
        response = event.response
        request = event.request

        # Compute the request processing time in msec (-1 if unknown)
        current = utils.msec_time()
        duration = current - getattr(request, "_received_at", current - 1)
        isotimestamp = datetime.fromtimestamp(current / 1000).isoformat()

        # Bind infos for request summary logger.
        request.log_context(time=isotimestamp, code=response.status_code, t=duration)

        if summary_logger.level == logging.DEBUG:
            request.log_context(response=dict(headers=dict(response.headers), body=response.body))

        try:
            # If error response, bind errno.
            request.log_context(errno=response.errno)
        except AttributeError:
            pass

        if not hasattr(request, "parent"):
            # Ouput application request summary.
            summary_logger.info("", extra=request.log_context())

    config.add_subscriber(on_new_response, NewResponse)


def setup_metrics(config):
    settings = config.get_settings()

    # Register a no-op metrics service by default.
    config.registry.registerUtility(metrics.NoOpMetricsService(), metrics.IMetricsService)

    # This does not fully respect the Pyramid/ZCA patterns, but the rest of Kinto uses
    # `registry.storage`, `registry.cache`, etc. Consistency seems more important.
    config.registry.__class__.metrics = property(
        lambda reg: reg.queryUtility(metrics.IMetricsService)
    )

    def deprecated_registry(self):
        warnings.warn(
            "``config.registry.statsd`` is now deprecated. Use ``config.registry.metrics`` instead.",
            DeprecationWarning,
        )
        return self.metrics

    config.registry.__class__.statsd = property(deprecated_registry)

    def on_app_created(event):
        config = event.app
        metrics_service = config.registry.metrics

        metrics.watch_execution_time(metrics_service, config.registry.cache, prefix="backend")
        metrics.watch_execution_time(metrics_service, config.registry.storage, prefix="backend")
        metrics.watch_execution_time(metrics_service, config.registry.permission, prefix="backend")

        policy = config.registry.queryUtility(IAuthenticationPolicy)
        if isinstance(policy, MultiAuthenticationPolicy):
            for name, subpolicy in policy.get_policies():
                metrics.watch_execution_time(
                    metrics_service, subpolicy, prefix="authentication", classname=name
                )
        else:
            metrics.watch_execution_time(metrics_service, policy, prefix="authentication")

        # Set cache metrics backend
        cache_backend = config.registry.cache
        if isinstance(cache_backend, cache.CacheBase):
            cache_backend.set_metrics_backend(metrics_service)

    config.add_subscriber(on_app_created, ApplicationCreated)

    def on_new_response(event):
        request = event.request
        metrics_service = config.registry.metrics

        # Count unique users.
        user_id = request.prefixed_userid
        if user_id:
            # Get rid of colons in metric packet (see #1282).
            auth, user_id = user_id.split(":")
            metrics_service.count("users", unique=[("auth", auth), ("userid", user_id)])

        status = event.response.status_code

        if status >= 400:
            # Prevent random values of 404 responses to become label values.
            request_matchdict = {}
        else:
            request_matchdict = dict(request.matchdict or {})

        # Add extra labels to metrics, based on fields extracted from the request matchdict.
        metrics_matchdict_fields = aslist(settings["metrics_matchdict_fields"])
        # Turn the `id` field of object endpoints into `{resource}_id` (eg. `mushroom_id`, `bucket_id`)
        enhanced_matchdict = request_matchdict
        try:
            enhanced_matchdict[request.current_resource_name + "_id"] = enhanced_matchdict.get(
                "id", ""
            )
        except AttributeError:
            # Not on a resource.
            pass
        metrics_matchdict_labels = [
            (field, enhanced_matchdict.get(field, "")) for field in metrics_matchdict_fields
        ]

        service = request.current_service
        if service:
            # Use the service name as endpoint if available.
            endpoint = service.name
        elif route := request.matched_route:
            # Use the route name as endpoint if we're not on a Cornice service.
            endpoint = route.name
        else:
            endpoint = (
                "unnamed" if status != 404 else "unknown"
            )  # Do not multiply cardinality for unknown endpoints.

        request_labels = [
            ("method", request.method.lower()),
            ("endpoint", endpoint),
        ] + metrics_matchdict_labels

        # Count served requests.
        metrics_service.count("request_summary", unique=request_labels + [("status", str(status))])

        try:
            current = utils.msec_time()
            duration = (current - request._received_at) / 1000
            metrics_service.timer(
                "request_duration_seconds",
                value=duration,
                labels=request_labels,
            )
        except AttributeError:  # pragma: no cover
            # Logging was not setup in this Kinto app (unlikely but possible)
            pass

        # Observe response size.
        metrics_service.observe(
            "request_size", len(event.response.body or b""), labels=request_labels
        )

        # Count authentication verifications.
        try:
            metrics_service.count("authentication", unique=[("type", request.authn_type)])
        except AttributeError:
            # Not authenticated
            pass

    config.add_subscriber(on_new_response, NewResponse)


class EventActionFilter:
    def __init__(self, actions, config):
        actions = ACTIONS.from_string_list(actions)
        self.actions = [action.value for action in actions]

    def phash(self):
        return f"for_actions = {','.join(self.actions)}"

    def __call__(self, event):
        action = event.payload.get("action")
        return not action or action in self.actions


class EventResourceFilter:
    def __init__(self, resources, config):
        self.resources = resources

    def phash(self):
        return f"for_resources = {','.join(self.resources)}"

    def __call__(self, event):
        resource = event.payload.get("resource_name")
        return not resource or not self.resources or resource in self.resources


def setup_listeners(config):
    # Register basic subscriber predicates, to filter events.
    config.add_subscriber_predicate("for_actions", EventActionFilter)
    config.add_subscriber_predicate("for_resources", EventResourceFilter)

    write_actions = (ACTIONS.CREATE, ACTIONS.UPDATE, ACTIONS.DELETE)
    settings = config.get_settings()
    settings_prefix = settings.get("settings_prefix", "")
    listeners = aslist(settings["event_listeners"])

    for name in listeners:
        logger.info(f"Setting up '{name}' listener")
        prefix = f"event_listeners.{name}."

        try:
            listener_mod = config.maybe_dotted(name)
            prefix = f"event_listeners.{name.split('.')[-1]}."
            listener = listener_mod.load_from_config(config, prefix)
        except (ImportError, AttributeError):
            module_setting = prefix + "use"
            # Read from ENV or settings.
            module_value = utils.read_env(
                f"{settings_prefix}.{module_setting}", settings.get(module_setting)
            )
            listener_mod = config.maybe_dotted(module_value)
            listener = listener_mod.load_from_config(config, prefix)

        wrapped_listener = metrics.listener_with_timer(
            config, f"listeners.{name}", listener.__call__
        )

        # Optional filter by event action.
        actions_setting = prefix + "actions"
        # Read from ENV or settings.
        actions_value = utils.read_env(
            f"{settings_prefix}.{actions_setting}", settings.get(actions_setting, "")
        )
        actions = aslist(actions_value)
        if len(actions) > 0:
            actions = ACTIONS.from_string_list(actions)
        else:
            actions = write_actions

        # Optional filter by event resource name.
        resource_setting = prefix + "resources"
        # Read from ENV or settings.
        resource_value = utils.read_env(
            f"{settings_prefix}.{resource_setting}", settings.get(resource_setting, "")
        )
        resource_names = aslist(resource_value)

        # Pyramid event predicates.
        options = dict(for_actions=actions, for_resources=resource_names)

        if ACTIONS.READ in actions:
            config.add_subscriber(wrapped_listener, ResourceRead, **options)
            actions = [a for a in actions if a != ACTIONS.READ]

        if len(actions) > 0:
            config.add_subscriber(wrapped_listener, ResourceChanged, **options)


def load_default_settings(config, default_settings):
    """Read settings provided in Paste ini file, set default values and
    replace if defined as environment variable.
    """
    settings = config.get_settings()

    settings_prefix = settings["settings_prefix"]

    def _prefixed_keys(key):
        unprefixed = key
        if key.startswith(settings_prefix + "."):
            unprefixed = key.split(".", 1)[1]
        project_prefix = f"{settings_prefix}.{unprefixed}"
        return unprefixed, project_prefix

    # Fill settings with default values if not defined.
    for key, default_value in sorted(default_settings.items()):
        unprefixed, project_prefix = keys = _prefixed_keys(key)
        is_defined = len(set(settings.keys()).intersection(set(keys))) > 0
        if not is_defined:
            settings[unprefixed] = default_value

    for key, value in sorted(settings.items()):
        value = utils.native_value(value)
        unprefixed, project_prefix = keys = _prefixed_keys(key)

        # Fail if not only one is defined.
        defined = set(settings.keys()).intersection(set(keys))
        distinct_values = set([str(settings[d]) for d in defined])

        if len(defined) > 1 and len(distinct_values) > 1:
            names = "', '".join(defined)
            raise ValueError(f"Settings '{names}' are in conflict.")

        # Override settings from OS env values.
        # e.g. HTTP_PORT, READINGLIST_HTTP_PORT, KINTO_HTTP_PORT
        from_env = utils.read_env(unprefixed, value)
        from_env = utils.read_env(project_prefix, from_env)

        settings[unprefixed] = from_env

    config.add_settings(settings)


def initialize(config, version=None, settings_prefix="", default_settings=None):
    """Initialize kinto.core with the given configuration, version and project
    name.

    This will basically include kinto.core in Pyramid and set route prefix
    based on the specified version.

    :param config: Pyramid configuration
    :type config: :class:`~pyramid:pyramid.config.Configurator`
    :param str version: Current project version (e.g. '0.0.1') if not defined
        in application settings.
    :param str settings_prefix: Project name if not defined
        in application settings.
    :param dict default_settings: Override kinto.core default settings values.
    """
    from kinto.core import DEFAULT_SETTINGS

    settings = config.get_settings()

    settings_prefix = (
        settings.pop("kinto.settings_prefix", settings.get("settings_prefix")) or settings_prefix
    )
    settings["settings_prefix"] = settings_prefix
    if not settings_prefix:
        warnings.warn("No value specified for `settings_prefix`")

    kinto_core_defaults = {**DEFAULT_SETTINGS}

    if default_settings:
        kinto_core_defaults.update(default_settings)

    load_default_settings(config, kinto_core_defaults)

    http_scheme = settings["http_scheme"]
    if http_scheme != "https":
        warnings.warn("HTTPS is not enabled")

    # Override project version from settings.
    project_version = settings.get("project_version") or version
    if not project_version:
        error_msg = f"Invalid project version: {project_version}"
        raise ConfigurationError(error_msg)
    settings["project_version"] = project_version = str(project_version)

    # HTTP API version.
    http_api_version = settings.get("http_api_version")
    if http_api_version is None:
        # The API version is derivated from the module version if not provided.
        http_api_version = ".".join(project_version.split(".")[0:2])
    settings["http_api_version"] = http_api_version = str(http_api_version)
    api_version = f"v{http_api_version.split('.')[0]}"

    # Include kinto.core views with the correct api version prefix.
    config.include("kinto.core", route_prefix=api_version)
    config.route_prefix = api_version
