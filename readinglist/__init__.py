"""Main entry point
"""
import pkg_resources

import six

from pyramid.config import Configurator
from pyramid.events import NewRequest
from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid_multiauth import MultiAuthenticationPolicy

from readinglist import authentication
from readinglist.resource import TimeStamp


# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# The API version is derivated from the module version.
API_VERSION = 'v%s' % __version__.split('.')[0]


def redirect_to_version(request):
    """Redirect to the current version of the API."""
    raise HTTPTemporaryRedirect(
        '/%s/%s' % (API_VERSION, request.matchdict['path']))


def main(global_config, **settings):
    config = Configurator(settings=settings)

    # Redirect to the current version of the API if the prefix isn't used.
    config.add_route(name='redirect_to_version',
                     pattern='/{path:(?!%s).*}' % API_VERSION)
    config.add_view(view=redirect_to_version, route_name='redirect_to_version')

    config.route_prefix = '/%s' % API_VERSION

    backend_module = config.maybe_dotted(settings['readinglist.backend'])
    config.registry.backend = backend_module.load_from_config(config)

    policies = [
        authentication.Oauth2AuthenticationPolicy(),
        authentication.BasicAuthAuthenticationPolicy(),
    ]
    authn_policy = MultiAuthenticationPolicy(policies)
    authz_policy = authentication.AuthorizationPolicy()

    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)

    config.include("cornice")
    config.scan("readinglist.views")

    def on_new_request(event):
        # Attach objects on requests for easier access.
        event.request.db = config.registry.backend
        http_scheme = config.registry.settings.get('readinglist.http_scheme')
        if http_scheme:
            event.request.scheme = http_scheme

    config.add_subscriber(on_new_request, NewRequest)

    def on_new_response(event):
        # Add timestamp info in response headers.
        timestamp = six.text_type(TimeStamp.now())
        event.request.response.headers['Timestamp'] = timestamp.encode('utf-8')

    config.add_subscriber(on_new_response, NewRequest)

    return config.make_wsgi_app()
