"""Main entry point
"""
import pkg_resources
import logging

from cornice import Service
from pyramid.config import Configurator
from pyramid.events import NewRequest, NewResponse
from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid_multiauth import MultiAuthenticationPolicy

from readinglist import authentication
from readinglist.utils import msec_time


# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# The API version is derivated from the module version.
API_VERSION = 'v%s' % __version__.split('.')[0]

# Main readinglist logger
logger = logging.getLogger(__name__)


def handle_api_redirection(config):
    """Add a view which redirects to the current version of the API.
    """

    def _redirect_to_version_view(request):
        raise HTTPTemporaryRedirect(
            '/%s/%s' % (API_VERSION, request.matchdict['path']))

    # Redirect to the current version of the API if the prefix isn't used.
    config.add_route(name='redirect_to_version',
                     pattern='/{path:(?!%s).*}' % API_VERSION)

    config.add_view(view=_redirect_to_version_view,
                    route_name='redirect_to_version')

    config.route_prefix = '/%s' % API_VERSION


def set_auth(config):
    """Define the authentication and authorization policies.
    """
    policies = [
        authentication.Oauth2AuthenticationPolicy(),
        authentication.BasicAuthAuthenticationPolicy(),
    ]
    authn_policy = MultiAuthenticationPolicy(policies)
    authz_policy = authentication.AuthorizationPolicy()

    config.set_authorization_policy(authz_policy)
    config.set_authentication_policy(authn_policy)


def attach_http_objects(config):
    """Attach HTTP requests/responses objects.

    This is useful to attach objects to the request object for easier
    access, and to pre-process responses.
    """
    def on_new_request(event):
        # Save the time the request was received by the server
        event.request._received_at = msec_time()

        # Attach objects on requests for easier access.
        event.request.db = config.registry.storage

        http_scheme = config.registry.settings.get('readinglist.http_scheme')
        if http_scheme:
            event.request.scheme = http_scheme

    config.add_subscriber(on_new_request, NewRequest)

    def on_new_response(event):
        # Display the status of the request as well as the time spend
        # on the server.
        pattern = '"{method} {path}" {status} {size} ({duration} ms)'
        msg = pattern.format(
            method=event.request.method,
            path=event.request.path,
            status=event.response.status_code,
            size=event.response.content_length,
            duration=(msec_time() - event.request._received_at))
        logger.debug(msg)

        # Add backoff in response headers
        backoff = config.registry.settings.get("readinglist.backoff")
        if backoff is not None:
            event.request.response.headers['Backoff'] = backoff.encode('utf-8')

    config.add_subscriber(on_new_response, NewResponse)


def main(global_config, **settings):
    Service.cors_origins = ('*',)
    config = Configurator(settings=settings)
    handle_api_redirection(config)

    config.route_prefix = '/%s' % API_VERSION

    storage = config.maybe_dotted(settings['readinglist.storage_backend'])
    config.registry.storage = storage.load_from_config(config)

    session = config.maybe_dotted(settings['readinglist.session_backend'])
    config.registry.session = session.load_from_config(config)

    set_auth(config)

    # Include cornice and discover views.
    config.include("cornice")
    config.scan("readinglist.views")

    attach_http_objects(config)

    return config.make_wsgi_app()
