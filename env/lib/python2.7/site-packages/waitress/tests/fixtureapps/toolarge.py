def app(environ, start_response): # pragma: no cover
    body = b'abcdef'
    cl = len(body)
    start_response(
        '200 OK',
        [('Content-Length', str(cl)), ('Content-Type', 'text/plain')]
    )
    return [body]
