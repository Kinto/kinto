from pyramid import httpexceptions as exc
from pyramid.renderers import JSON
from pyramid.response import Response


def bytes_adapter(obj, request):
    """Convert bytes objects to strings for json error renderer."""
    if isinstance(obj, bytes):
        return obj.decode("utf8")
    return obj


class JSONError(exc.HTTPError):
    def __init__(self, serializer, serializer_kw, errors, status=400):
        body = {"status": "error", "errors": errors}
        Response.__init__(self, serializer(body, **serializer_kw))
        self.status = status
        self.content_type = "application/json"


class CorniceRenderer(JSON):
    """We implement JSON serialization by extending Pyramid's default
    JSON rendering machinery using our own custom Content-Type logic `[1]`_.

    This allows developers to config the JSON renderer using Pyramid's
    configuration machinery `[2]`_.

      .. _`[1]`: https://github.com/mozilla-services/cornice/pull/116 \
                 #issuecomment-14355865
      .. _`[2]`: http://pyramid.readthedocs.io/en/latest/narr/renderers.html \
                 #serializing-custom-objects
    """

    acceptable = ("application/json", "text/plain")

    def __init__(self, *args, **kwargs):
        """Adds a `bytes` adapter by default."""
        super(CorniceRenderer, self).__init__(*args, **kwargs)
        self.add_adapter(bytes, bytes_adapter)

    def render_errors(self, request):
        """Returns an HTTPError with the given status and message.

        The HTTP error content type is "application/json"
        """
        default = self._make_default(request)
        serializer_kw = self.kw.copy()
        serializer_kw["default"] = default
        return JSONError(
            serializer=self.serializer,
            serializer_kw=serializer_kw,
            errors=request.errors,
            status=request.errors.status,
        )

    def render(self, value, system):
        """Extends the default `_render` function of the pyramid JSON renderer.

        Compared to the default `pyramid.renderers.JSON` renderer:
            1. Overrides the response with an empty string and
               no Content-Type in case of HTTP 204.
            2. Overrides the default behavior of Content-Type handling,
               forcing the use of `acceptable_offers`, instead of letting
               the user specify the Content-Type manually.
               TODO: maybe explain this a little better
        """
        request = system.get("request")
        if request is not None:
            response = request.response

            # Do not return content with ``204 No Content``
            if response.status_code == 204:
                response.content_type = None
                return ""

            ctypes = request.accept.acceptable_offers(offers=self.acceptable)
            if not ctypes:
                ctypes = [(self.acceptable[0], 1.0)]
            response.content_type = ctypes[0][0]
        default = self._make_default(request)
        return self.serializer(value, default=default, **self.kw)

    def __call__(self, info):
        """Overrides the default behavior of `pyramid.renderers.JSON`.

        Uses a public `render()` method instead of defining render inside
        `__call__`, to let the user extend it if necessary.
        """
        return self.render
