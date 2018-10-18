import os

from kinto.core.decorators import cache_forever

HERE = os.path.dirname(__file__)


# Configured home page
@cache_forever
def admin_home_view(request):
    try:
        with open(os.path.join(HERE, "build/index.html")) as f:
            page_content = f.read()
    except FileNotFoundError:  # pragma: no cover
        with open(os.path.join(HERE, "public/help.html")) as f:
            page_content = f.read()
    return page_content
