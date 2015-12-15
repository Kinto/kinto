class DummyTweens(object):
    def __init__(self, implicit, explicit):
        self._implicit = implicit
        self.explicit = explicit
        self.name_to_alias = {}
    def implicit(self):
        return self._implicit

class Dummy:
    pass

dummy_root = Dummy()

class DummyRegistry(object):
    settings = {}
    def queryUtility(self, iface, default=None, name=''):
        return default

dummy_registry = DummyRegistry()

class DummyShell(object):
    env = {}
    help = ''

    def __call__(self, env, help):
        self.env = env
        self.help = help

class DummyInteractor:
    def __call__(self, banner, local):
        self.banner = banner
        self.local = local

class DummyBPythonShell:
    def __call__(self, locals_, banner):
        self.locals_ = locals_
        self.banner = banner

class DummyIPShell(object):
    IP = Dummy()
    IP.BANNER = 'foo'

    def set_banner(self, banner):
        self.banner = banner

    def __call__(self):
        self.called = True

class DummyIPShellFactory(object):
    def __call__(self, **kw):
        self.kw = kw
        self.shell = DummyIPShell()
        return self.shell

class DummyApp:
    def __init__(self):
        self.registry = dummy_registry

class DummyMapper(object):
    def __init__(self, *routes):
        self.routes = routes

    def get_routes(self, include_static=False):
        return self.routes

class DummyRoute(object):
    def __init__(self, name, pattern, factory=None,
                 matchdict=None, predicate=None):
        self.name = name
        self.path = pattern
        self.pattern = pattern
        self.factory = factory
        self.matchdict = matchdict
        self.predicates = []
        if predicate is not None:
            self.predicates = [predicate]

    def match(self, route):
        return self.matchdict

class DummyRequest:
    application_url = 'http://example.com:5432'
    script_name = ''
    def __init__(self, environ):
        self.environ = environ
        self.matchdict = {}

class DummyView(object):
    def __init__(self, **attrs):
        self.__request_attrs__ = attrs

from zope.interface import implementer
from pyramid.interfaces import IMultiView
@implementer(IMultiView)
class DummyMultiView(object):

    def __init__(self, *views, **attrs):
        self.views = [(None, view, None) for view in views]
        self.__request_attrs__ = attrs

class DummyConfigParser(object):
    def __init__(self, result):
        self.result = result

    def read(self, filename):
        self.filename = filename

    def items(self, section):
        self.section = section
        if self.result is None:
            from pyramid.compat import configparser
            raise configparser.NoSectionError(section)
        return self.result

class DummyConfigParserFactory(object):
    items = None

    def __call__(self):
        self.parser = DummyConfigParser(self.items)
        return self.parser

class DummyCloser(object):
    def __call__(self):
        self.called = True

class DummyBootstrap(object):
    def __init__(self, app=None, registry=None, request=None, root=None,
                 root_factory=None, closer=None):
        self.app = app or DummyApp()
        if registry is None:
            registry = DummyRegistry()
        self.registry = registry
        if request is None:
            request = DummyRequest({})
        self.request = request
        if root is None:
            root = Dummy()
        self.root = root
        if root_factory is None:
            root_factory = Dummy()
        self.root_factory = root_factory
        if closer is None:
            closer = DummyCloser()
        self.closer = closer

    def __call__(self, *a, **kw):
        self.a = a
        self.kw = kw
        registry = kw.get('registry', self.registry)
        request = kw.get('request', self.request)
        request.registry = registry
        return {
            'app': self.app,
            'registry': registry,
            'request': request,
            'root': self.root,
            'root_factory': self.root_factory,
            'closer': self.closer,
        }
