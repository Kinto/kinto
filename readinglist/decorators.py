from readinglist.backend.exceptions import RecordNotFoundError


def exists_or_404():
    """View decorator to catch unknown record errors in backend."""
    def wrap(view):
        def wrapped_view(request, *args, **kwargs):
            try:
                return view(request, *args, **kwargs)
            except RecordNotFoundError as e:
                request.errors.add('path', 'record_id', str(e))
                request.errors.status = "404 Not Found"
        return wrapped_view
    return wrap
