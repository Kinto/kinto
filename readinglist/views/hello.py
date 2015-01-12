from cornice import Service
from readinglist import __version__ as VERSION


hello = Service(name="hello", path='/', description="Welcome")


@hello.get()
def get_hello(request):
    """Return information regarding the current instance."""
    eos = request.registry.settings.get('readinglist.eos', '').strip() or None
    return dict(hello='readinglist',
                version=VERSION,
                url=request.host_url,
                eos=eos)
