from cornice import Service
from readinglist import __version__ as VERSION


hello = Service(name="hello", path='/', description="Welcome")


@hello.get()
def get_hello(request):
    """Return information regarding the current instance."""
    return dict(readinglist='hello',
                version=VERSION,
                url=request.host_url)
