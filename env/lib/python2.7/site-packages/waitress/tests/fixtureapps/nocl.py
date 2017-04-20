def chunks(l, n): # pragma: no cover
    """ Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]

def gen(body): # pragma: no cover
    for chunk in chunks(body, 10):
        yield chunk

def app(environ, start_response): # pragma: no cover
    cl = environ.get('CONTENT_LENGTH', None)
    if cl is not None:
        cl = int(cl)
    body = environ['wsgi.input'].read(cl)
    start_response(
        '200 OK',
        [('Content-Type', 'text/plain')]
    )
    if environ['PATH_INFO'] == '/list':
        return [body]
    if environ['PATH_INFO'] == '/list_lentwo':
        return [body[0:1], body[1:]]
    return gen(body)
