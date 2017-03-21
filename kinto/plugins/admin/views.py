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

    try:
        with open(os.path.join(HERE, 'build/index.html')) as f:
            index_content = f.read()
    except FileNotFoundError:  # pragma: no cover
        with open(os.path.join(HERE, 'public/help.html')) as f:
            index_content = f.read()
    # Update the file built by react-scripts to load the globalSettings.
    return index_content.replace('<script', globalSettings + '<script')
