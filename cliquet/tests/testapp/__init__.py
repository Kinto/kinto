from pyramid.config import Configurator
from cliquet import initialize_cliquet


def includeme(config):
    config.scan("cliquet.tests.testapp.views")


def main(settings=None):
    if settings is None:
        settings = {
            'cliquet.project_name': 'cliquet',
            'cliquet.project_docs': 'https://cliquet.rtfd.org/',
            'cliquet.storage_backend': 'cliquet.storage.redis',
            'cliquet.session_backend': 'cliquet.session.redis',
            'fxa-oauth.client_id': '89513028159972bc',
            'fxa-oauth.client_secret': '9aced230585cc0aa2932e2eb871c9a3a7d6458'
            'e59ccf57eb610ea0a3467dd800',
            'fxa-oauth.oauth_uri': 'https://oauth-stable.dev.lcip.org',
            'fxa-oauth.scope': 'profile'
        }
    config = Configurator(settings=settings)
    initialize_cliquet(config, version='0.0.1')
    config.include(includeme)
    return config.make_wsgi_app()
