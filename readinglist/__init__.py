"""Main entry point
"""
import pkg_resources

import six

from pyramid.config import Configurator
from pyramid.events import NewRequest, NewResponse
from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid_multiauth import MultiAuthenticationPolicy

from readinglist import authentication


# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# The API version is derivated from the module version.
API_VERSION = 'v%s' % __version__.split('.')[0]


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

    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)


def attach_http_objects(config):
    """Attach HTTP requests/responses objects.

    This is useful to attach objects to the request object for easier
    access, and to pre-process responses.
    """
    def on_new_request(event):
        # Attach objects on requests for easier access.
        event.request.db = config.registry.backend

        # Track incoming request timestamp
        event.request.timestamp = config.registry.backend.now()

        http_scheme = config.registry.settings.get('readinglist.http_scheme')
        if http_scheme:
            event.request.scheme = http_scheme

    config.add_subscriber(on_new_request, NewRequest)

    def on_new_response(event):
        # Add request timestamp info in response headers.
        timestamp = six.text_type(event.request.timestamp)
        event.request.response.headers['Timestamp'] = timestamp.encode('utf-8')

        # Add backoff in response headers
        backoff = config.registry.settings.get("readinglist.backoff")
        if backoff is not None:
            event.request.response.headers['Backoff'] = backoff.encode('utf-8')

    config.add_subscriber(on_new_response, NewResponse)


def main(global_config, **settings):
    config = Configurator(settings=settings)
    handle_api_redirection(config)

    config.route_prefix = '/%s' % API_VERSION

    backend_module = config.maybe_dotted(settings['readinglist.backend'])
    config.registry.backend = backend_module.load_from_config(config)

    set_auth(config)

    # Include cornice and discover views.
    config.include("cornice")
    config.scan("readinglist.views")

    attach_http_objects(config)

    return config.make_wsgi_app()
