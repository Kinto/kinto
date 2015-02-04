from cornice import Service
from readinglist import __version__ as VERSION


hello = Service(name="hello", path='/', description="Welcome")


@hello.get()
def get_hello(request):
    """Return information regarding the current instance."""
    data = dict(
        hello='readinglist',
        version=VERSION,
        url=request.host_url,
        documentation="https://readinglist.rtfd.org/"
    )

    eos = request.registry.settings.get('readinglist.eos', '').strip() or None
    if eos:
        data['eos'] = eos

    return data
