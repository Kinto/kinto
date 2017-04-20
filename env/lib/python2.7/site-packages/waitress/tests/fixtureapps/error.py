def app(environ, start_response): # pragma: no cover
    cl = environ.get('CONTENT_LENGTH', None)
    if cl is not None:
        cl = int(cl)
    body = environ['wsgi.input'].read(cl)
    cl = str(len(body))
    if environ['PATH_INFO'] == '/before_start_response':
        raise ValueError('wrong')
    write = start_response(
        '200 OK',
        [('Content-Length', cl), ('Content-Type', 'text/plain')]
    )
    if environ['PATH_INFO'] == '/after_write_cb':
        write('abc')
    if environ['PATH_INFO'] == '/in_generator':
        def foo():
            yield 'abc'
            raise ValueError
        return foo()
    raise ValueError('wrong')
