def app(environ, start_response): # pragma: no cover
    body = b'abcdefghi'
    cl = len(body)
    if environ['PATH_INFO'] == '/short_body':
        cl = len(body) + 1
    if environ['PATH_INFO'] == '/long_body':
        cl = len(body) - 1
    start_response(
        '200 OK',
        [('Content-Length', str(cl)), ('Content-Type', 'text/plain')]
    )
    return [body]
