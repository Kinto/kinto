from pyramid.config import Configurator
from cliquet.resource import BaseResource, ResourceSchema, crud
import colander

class MushroomSchema(ResourceSchema):
    name = colander.SchemaNode(colander.String())


@crud()
class Mushroom(BaseResource):
    mapping = MushroomSchema()


def includeme(config):
    config.include("cliquet")
    config.scan("cliquet.tests.testapp")


def main(settings=None):
    if settings is None:
        settings = {
                'cliquet.storage_backend': 'cliquet.storage.simpleredis',
                'cliquet.session_backend': 'cliquet.session.redis',
                'fxa-oauth.client_id': '89513028159972bc',
                'fxa-oauth.client_secret': '9aced230585cc0aa2932e2eb871c9a3a7d6458'
                                           'e59ccf57eb610ea0a3467dd800',
                'fxa-oauth.oauth_uri': 'https://oauth-stable.dev.lcip.org',
                'fxa-oauth.scope': 'profile'
            }
    config = Configurator(settings=settings)
    config.include(includeme, route_prefix="/v0")
    return config.make_wsgi_app()
