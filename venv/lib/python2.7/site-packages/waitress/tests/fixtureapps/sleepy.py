import time

def app(environ, start_response): # pragma: no cover
    if environ['PATH_INFO'] == '/sleepy':
        time.sleep(2)
        body = b'sleepy returned'
    else:
        body = b'notsleepy returned'
    cl = str(len(body))
    start_response(
        '200 OK',
        [('Content-Length', cl), ('Content-Type', 'text/plain')]
    )
    return [body]
