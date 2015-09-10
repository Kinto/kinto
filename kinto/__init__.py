import pkg_resources
import logging

import cliquet
from pyramid.config import Configurator
from pyramid.settings import asbool
from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid.security import Authenticated, NO_PERMISSION_REQUIRED
from cliquet.authorization import RouteFactory

# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# Main kinto logger
logger = logging.getLogger(__name__)


DEFAULT_SETTINGS = {
    'cliquet.cache_backend': 'cliquet.cache.memory',
    'cliquet.permission_backend': 'cliquet.permission.memory',
    'cliquet.storage_backend': 'cliquet.storage.memory',
    'cliquet.project_name': 'Kinto',
    'cliquet.project_docs': 'https://kinto.readthedocs.org/',
    'cliquet.bucket_create_principals': Authenticated,
    'multiauth.authorization_policy': (
        'kinto.authorization.AuthorizationPolicy'),
    'multiauth.groupfinder': (
        'kinto.authorization.groupfinder'),
    'kinto.experimental_collection_schema_validation': 'False',
}


def setup_redirect_trailing_slash(config):
    """URLs of Webservices built with Django usually have a trailing slash.
    Kinto does not, and removes it with a redirection.
    """
    def _view(request):
        route_prefix = request.registry.route_prefix
        path = request.matchdict['path']
        querystring = request.url[(request.url.rindex(request.path) +
                                   len(request.path)):]
        redirect = '/%s/%s%s' % (route_prefix, path, querystring)
        raise HTTPTemporaryRedirect(redirect)

    config.add_route(name='redirect_no_trailing_slash',
                     pattern='/{path:.+}/')
    config.add_view(view=_view,
                    route_name='redirect_no_trailing_slash',
                    permission=NO_PERMISSION_REQUIRED)


def main(global_config, **settings):
    config = Configurator(settings=settings, root_factory=RouteFactory)
    cliquet.initialize(config,
                       version=__version__,
                       default_settings=DEFAULT_SETTINGS)

    # Redirect default to the right endpoint
    config.add_route('default_bucket_collection',
                     '/buckets/default/{subpath:.*}')
    config.add_route('default_bucket', '/buckets/default')

    # Redirect to remove trailing slash
    setup_redirect_trailing_slash(config)

    # Scan Kinto views.
    settings = config.get_settings()
    kwargs = {}
    flush_enabled = asbool(settings.get('kinto.flush_endpoint_enabled'))
    if not flush_enabled:
        kwargs['ignore'] = 'kinto.views.flush'
    config.scan("kinto.views", **kwargs)

    return config.make_wsgi_app()
