import base64
import optparse
import sys
import textwrap

from pyramid.compat import url_unquote
from pyramid.request import Request
from pyramid.paster import get_app
from pyramid.scripts.common import parse_vars

def main(argv=sys.argv, quiet=False):
    command = PRequestCommand(argv, quiet)
    return command.run()

class PRequestCommand(object):
    description = """\
    Run a request for the described application.

    This command makes an artifical request to a web application that uses a
    PasteDeploy (.ini) configuration file for the server and application.

    Use "prequest config.ini /path" to request "/path".

    Use "prequest --method=POST config.ini /path < data" to do a POST with
    the given request body.

    Use "prequest --method=PUT config.ini /path < data" to do a
    PUT with the given request body.

    Use "prequest --method=PATCH config.ini /path < data" to do a
    PATCH with the given request body.

    Use "prequest --method=OPTIONS config.ini /path" to do an
    OPTIONS request.

    Use "prequest --method=PROPFIND config.ini /path" to do a
    PROPFIND request.

    If the path is relative (doesn't begin with "/") it is interpreted as
    relative to "/".  The path passed to this script should be URL-quoted.
    The path can be succeeded with a query string (e.g. `/path?a=1&=b2').

    The variable "environ['paste.command_request']" will be set to "True" in
    the request's WSGI environment, so your application can distinguish these
    calls from normal requests.
    """
    usage = "usage: %prog config_uri path_info [args/options]"
    parser = optparse.OptionParser(
        usage=usage,
        description=textwrap.dedent(description)
        )
    parser.add_option(
        '-n', '--app-name',
        dest='app_name',
        metavar= 'NAME',
        help="Load the named application from the config file (default 'main')",
        type="string",
        )
    parser.add_option(
        '--header',
        dest='headers',
        metavar='NAME:VALUE',
        type='string',
        action='append',
        help="Header to add to request (you can use this option multiple times)"
        )
    parser.add_option(
        '-d', '--display-headers',
        dest='display_headers',
        action='store_true',
        help='Display status and headers before the response body'
        )
    parser.add_option(
        '-m', '--method',
        dest='method',
        choices=['GET', 'HEAD', 'POST', 'PUT', 'PATCH','DELETE',
                 'PROPFIND', 'OPTIONS'],
        type='choice',
        help='Request method type (GET, POST, PUT, PATCH, DELETE, '
             'PROPFIND, OPTIONS)',
        )
    parser.add_option(
        '-l', '--login',
        dest='login',
        type='string',
        help='HTTP basic auth username:password pair',
        )

    get_app = staticmethod(get_app)
    stdin = sys.stdin

    def __init__(self, argv, quiet=False):
        self.quiet = quiet
        self.options, self.args = self.parser.parse_args(argv[1:])

    def out(self, msg): # pragma: no cover
        if not self.quiet:
            print(msg)

    def run(self):
        if not len(self.args) >= 2:
            self.out('You must provide at least two arguments')
            return 2
        app_spec = self.args[0]
        path = self.args[1]
        if not path.startswith('/'):
            path = '/' + path

        try:
            path, qs = path.split('?', 1)
        except ValueError:
            qs = ''

        path = url_unquote(path)

        headers = {}
        if self.options.login:
            enc = base64.b64encode(self.options.login.encode('ascii'))
            headers['Authorization'] = 'Basic ' + enc.decode('ascii')

        if self.options.headers:
            for item in self.options.headers:
                if ':' not in item:
                    self.out(
                        "Bad --header=%s option, value must be in the form "
                        "'name:value'" % item)
                    return 2
                name, value = item.split(':', 1)
                headers[name] = value.strip()

        app = self.get_app(app_spec, self.options.app_name,
                options=parse_vars(self.args[2:]))

        request_method = (self.options.method or 'GET').upper()

        environ = {
            'REQUEST_METHOD': request_method,
            'SCRIPT_NAME': '',           # may be empty if app is at the root
            'PATH_INFO': path,
            'SERVER_NAME': 'localhost',  # always mandatory
            'SERVER_PORT': '80',         # always mandatory
            'SERVER_PROTOCOL': 'HTTP/1.0',
            'CONTENT_TYPE': 'text/plain',
            'REMOTE_ADDR':'127.0.0.1',
            'wsgi.run_once': True,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.errors': sys.stderr,
            'wsgi.url_scheme': 'http',
            'wsgi.version': (1, 0),
            'QUERY_STRING': qs,
            'HTTP_ACCEPT': 'text/plain;q=1.0, */*;q=0.1',
            'paste.command_request': True,
            }

        if request_method in ('POST', 'PUT', 'PATCH'):
            environ['wsgi.input'] = self.stdin
            environ['CONTENT_LENGTH'] = '-1'

        for name, value in headers.items():
            if name.lower() == 'content-type':
                name = 'CONTENT_TYPE'
            else:
                name = 'HTTP_'+name.upper().replace('-', '_')
            environ[name] = value

        request = Request.blank(path, environ=environ)
        response = request.get_response(app)
        if self.options.display_headers:
            self.out(response.status)
            for name, value in response.headerlist:
                self.out('%s: %s' % (name, value))
        if response.charset:
            self.out(response.ubody)
        else:
            self.out(response.body)
        return 0

if __name__ == '__main__': # pragma: no cover
    sys.exit(main() or 0)
