"""Main entry point
"""
import datetime
import json

from dateutil import parser as dateparser
import pkg_resources

from pyramid.events import NewRequest, NewResponse
from pyramid.httpexceptions import HTTPTemporaryRedirect, HTTPGone
from pyramid_multiauth import MultiAuthenticationPolicy
from pyramid.security import NO_PERMISSION_REQUIRED

from cliquet import authentication
from cliquet import errors
from cliquet import utils
from cliquet.session import SessionCache
from cliquet.utils import msec_time

import structlog
from cornice import Service

# Monkey Patch Cornice Service to setup the global CORS configuration.
Service.cors_origins = ('*',)
Service.default_cors_headers = ('Backoff', 'Retry-After', 'Alert')

DEFAULT_OAUTH_CACHE_SECONDS = 5 * 60


# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# The API version is derivated from the module version.
API_VERSION = 'v%s' % __version__.split('.')[0]

# Main cliquet logger
logger = structlog.get_logger(__name__)


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
    oauth_cache_ttl = int(config.registry.settings.get(
        'fxa-oauth.cache_ttl_seconds',
        DEFAULT_OAUTH_CACHE_SECONDS))

    policies = [
        authentication.Oauth2AuthenticationPolicy(
            cache=SessionCache(config.registry.session, ttl=oauth_cache_ttl)),
        authentication.BasicAuthAuthenticationPolicy(),
    ]
    authn_policy = MultiAuthenticationPolicy(policies)
    authz_policy = authentication.AuthorizationPolicy()

    config.set_authorization_policy(authz_policy)
    config.set_authentication_policy(authn_policy)
    # XXX: Should be restore as soon as Cornice is fixed (see #273)
    # config.set_default_permission('readwrite')


def attach_http_objects(config):
    """Attach HTTP requests/responses objects.

    This is useful to attach objects to the request object for easier
    access, and to pre-process responses.
    """

    def on_new_request(event):
        # Attach objects on requests for easier access.
        event.request.db = config.registry.storage

        # Force request scheme from settings.
        http_scheme = config.registry.settings.get('cliquet.http_scheme')
        if http_scheme:
            event.request.scheme = http_scheme

    config.add_subscriber(on_new_request, NewRequest)

    def on_new_response(event):
        # Add backoff in response headers.
        backoff = config.registry.settings.get("cliquet.backoff")
        if backoff is not None:
            event.request.response.headers['Backoff'] = backoff.encode('utf-8')

    config.add_subscriber(on_new_response, NewResponse)


def end_of_life_tween_factory(handler, registry):
    """Pyramid tween to handle service end of life."""

    deprecated_response = errors.http_error(
        HTTPGone(),
        errno=errors.ERRORS.SERVICE_DEPRECATED,
        message="The service you are trying to connect no longer exists "
                "at this location.")

    def eos_tween(request):
        eos_date = registry.settings.get("cliquet.eos")
        eos_url = registry.settings.get("cliquet.eos_url")
        eos_message = registry.settings.get("cliquet.eos_message")
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
            response.headers['Alert'] = json.dumps(alert)
            return response
        return handler(request)
    return eos_tween


def setup_logging(config):
    """Setup structured logging, and emit `request.summary` event on each
    request, as recommanded by Mozilla Services standard:

    * https://mana.mozilla.org/wiki/display/CLOUDSERVICES/Logging+Standard
    * http://12factor.net/logs
    """
    # XXX: if debug, render as key=value
    structlog.configure(
        processors=[
            # XXX https://github.com/hynek/structlog/pull/50
            # structlog.stdlib.filter_by_level,
            structlog.processors.format_exc_info,
            utils.MozillaHekaRenderer(config.get_settings())
        ],
        # Share the logger context by thread
        context_class=structlog.threadlocal.wrap_dict(dict),
        # Integrate with Pyramid logging facilities
        logger_factory=structlog.stdlib.LoggerFactory())

    def on_new_request(event):
        request = event.request
        # Save the time the request was received by the server.
        event.request._received_at = msec_time()

        # New logger context, with infos for request summary logger.
        logger.new(agent=request.headers.get('User-Agent'),
                   path=event.request.path,
                   method=request.method,
                   uid=request.authenticated_userid,
                   lang=request.headers.get('Accept-Language'),
                   errno=None)

    config.add_subscriber(on_new_request, NewRequest)

    def on_new_response(event):
        response = event.response
        request = event.request

        # Compute the request processing time in msec (-1 if unknown)
        current = msec_time()
        duration = current - getattr(request, '_received_at', current - 1)

        # Bind infos for request summary logger.
        logger.bind(code=response.status_code,
                    t=duration)

        # Ouput application request summary.
        logger.info('request.summary')

    config.add_subscriber(on_new_response, NewResponse)


def includeme(config):
    settings = config.get_settings()

    # Configure logging globally.
    setup_logging(config)

    handle_api_redirection(config)
    config.add_tween("cliquet.end_of_life_tween_factory")

    storage = config.maybe_dotted(settings['cliquet.storage_backend'])
    config.registry.storage = storage.load_from_config(config)

    session = config.maybe_dotted(settings['cliquet.session_backend'])
    config.registry.session = session.load_from_config(config)

    config.registry.project_name = settings['cliquet.project_name']
    config.registry.project_docs = settings['cliquet.project_docs']

    set_auth(config)
    attach_http_objects(config)

    # Include cornice and discover views.
    config.include("cornice")
    config.scan("cliquet.views")


def initialize_cliquet(config, version):
    """Initialize Cliquet with the given configuration and version"""

    # The API version is derivated from the module version.
    api_version = 'v%s' % version.split('.')[0]

    # Include cliquet views with the correct api version prefix.
    config.registry.project_version = version
    config.include("cliquet", route_prefix=api_version)
    config.route_prefix = api_version
