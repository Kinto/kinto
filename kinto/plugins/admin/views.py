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

    # Add Content-Security-Policy HTTP response header to protect against XSS:
    # only allow from local domain:
    allow_local_only = "; ".join(
        (
            "default-src 'self'",
            "img-src data: 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
        )
    )
    request.response.headers["Content-Security-Policy"] = allow_local_only

    return page_content
