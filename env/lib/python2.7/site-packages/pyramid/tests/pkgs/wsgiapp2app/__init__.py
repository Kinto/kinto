from pyramid.view import view_config
from pyramid.wsgi import wsgiapp2

@view_config(name='hello', renderer='string')
@wsgiapp2
def hello(environ, start_response):
    assert environ['PATH_INFO'] == '/'
    assert environ['SCRIPT_NAME'] == '/hello'
    response_headers = [('Content-Type', 'text/plain')]
    start_response('200 OK', response_headers)
    return [b'Hello!']

def main():
    from pyramid.config import Configurator
    c = Configurator()
    c.scan()
    return c
