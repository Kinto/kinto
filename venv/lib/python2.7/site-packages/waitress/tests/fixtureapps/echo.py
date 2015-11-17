def app(environ, start_response): # pragma: no cover
    cl = environ.get('CONTENT_LENGTH', None)
    if cl is not None:
        cl = int(cl)
    body = environ['wsgi.input'].read(cl)
    cl = str(len(body))
    start_response(
        '200 OK',
        [('Content-Length', cl), ('Content-Type', 'text/plain')]
    )
    return [body]
