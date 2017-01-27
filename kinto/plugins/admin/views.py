import json
import os

from pyramid.settings import aslist

HERE = os.path.abspath(os.path.dirname(__file__))
RESPONSE_CACHED = None


# Configured home page
def admin_home_view(request):
    global RESPONSE_CACHED
    if RESPONSE_CACHED is not None:
        request.response.write(RESPONSE_CACHED)
        return request.response

    settings = {
        "authMethods": aslist(request.registry.settings.get('multiauth.policies'))
    }
    globalSettings = "<script>window.globalSettings = %s;</script>" % json.dumps(settings)

    with open(os.path.join(HERE, 'build/index.html')) as f:
        RESPONSE_CACHED = f.read().replace('<script', globalSettings + '<script')

    request.response.write(RESPONSE_CACHED)
    return request.response
