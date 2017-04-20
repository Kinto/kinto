from collections import defaultdict
from cornice import Service
from cornice import resource

_USERS = defaultdict(dict)


class ThingImp(object):

    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    def collection_get(self):
        """Returns yay."""
        return 'yay'


def get_info(request):
    """Returns the user data."""
    username = request.matchdict['username']
    return _USERS[username]


def validate(request):
    """Dummy validation."""
    return request


def includeme(config):
    # FIXME this should also work in includeme
    user_info = Service(name='users', path='/{username}/info',
                        validators=('validate'))
    user_info.add_view('get', get_info)
    config.add_cornice_service(user_info)

    resource.add_view(ThingImp.collection_get, permission='read')
    thing_resource = resource.add_resource(
        ThingImp, collection_path='/thing', path='/thing/{id}',
        name='thing_service')
    config.add_cornice_resource(thing_resource)
