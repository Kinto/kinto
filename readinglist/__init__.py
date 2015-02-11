"""Main entry point
"""
import datetime
import json

from dateutil import parser as dateparser
import pkg_resources
import logging

from cornice import Service
from pyramid.config import Configurator
from pyramid.events import NewRequest, NewResponse
from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid_multiauth import MultiAuthenticationPolicy
from pyramid.security import NO_PERMISSION_REQUIRED

from readinglist import authentication
from readinglist.errors import HTTPServiceDeprecated
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
                    route_name='redirect_to_version',
                    permission=NO_PERMISSION_REQUIRED)

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
    # XXX: Should be restore as soon as Cornice is fixed (see #273)
    # config.set_default_permission('readwrite')


def attach_http_objects(config):
    """Attach HTTP requests/responses objects.

    This is useful to attach objects to the request object for easier
    access, and to pre-process responses.
    """

    def on_new_request(event):
        # Save the time the request was received by the server.
        event.request._received_at = msec_time()

        # Attach objects on requests for easier access.
        event.request.db = config.registry.storage

        http_scheme = config.registry.settings.get('readinglist.http_scheme')
        if http_scheme:
            event.request.scheme = http_scheme

    config.add_subscriber(on_new_request, NewRequest)

    def on_new_response(event):
        if hasattr(event.request, '_received_at'):
            duration = (msec_time() - event.request._received_at)
        else:
            duration = "unknown"

        # Display the status of the request as well as the time spent
        # on the server.
        pattern = '"{method} {path}" {status} {size} ({duration} ms)'
        msg = pattern.format(
            method=event.request.method,
            path=event.request.path,
            status=event.response.status_code,
            size=event.response.content_length,
            duration=duration)
        logger.debug(msg)

        # Add backoff in response headers.
        backoff = config.registry.settings.get("readinglist.backoff")
        if backoff is not None:
            event.request.response.headers['Backoff'] = backoff.encode('utf-8')

    config.add_subscriber(on_new_response, NewResponse)


def end_of_life_tween_factory(handler, registry):
    """Pyramid tween to handle service end of life."""

    def eos_tween(request):
        eos_date = registry.settings.get("readinglist.eos")
        eos_url = registry.settings.get("readinglist.eos_url")
        if eos_date:
            eos_date = dateparser.parse(eos_date)
            alert = {}
            if eos_url is not None:
                alert['url'] = eos_url

            if eos_date > datetime.datetime.now():
                alert['code'] = "soft-eol"
                response = handler(request)
            else:
                response = HTTPServiceDeprecated()
                alert['code'] = "hard-eol"
                response.headers = {}
            response.headers['Alert'] = json.dumps(alert)
            return response
        return handler(request)
    return eos_tween


def main(global_config, **settings):
    Service.cors_origins = ('*',)
    config = Configurator(settings=settings)
    config.add_tween("readinglist.end_of_life_tween_factory")

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
