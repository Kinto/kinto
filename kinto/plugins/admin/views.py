import json
import os

from pyramid.settings import aslist

from kinto.core.decorators import cache_forever

HERE = os.path.abspath(os.path.dirname(__file__))


# Configured home page
@cache_forever
def admin_home_view(request):
    settings = {
        "authMethods": aslist(request.registry.settings.get('multiauth.policies'))
    }
    globalSettings = "<script>window.globalSettings = {};</script>".format(json.dumps(settings))

    # Update the file built by react-scripts to load the globalSettings.
    with open(os.path.join(HERE, 'build/index.html')) as f:
        return f.read().replace('<script', globalSettings + '<script')
