from pyramid.view import view_config
from pyramid.events import subscriber

class Yup(object):
    def __init__(self, val, config):
        self.val = val

    def text(self):
        return 'path_startswith = %s' % (self.val,)

    phash = text

    def __call__(self, event):
        return getattr(event.response, 'yup', False)

class Foo(object):
    def __init__(self, response):
        self.response = response

class Bar(object):
    pass

@subscriber(Foo)
def foo(event):
    event.response.text += 'foo '

@subscriber(Foo, yup=True)
def fooyup(event):
    event.response.text += 'fooyup '
    
@subscriber([Foo, Bar])
def foobar(event):
    event.response.text += 'foobar '

@subscriber([Foo, Bar])
def foobar2(event, context):
    event.response.text += 'foobar2 '

@subscriber([Foo, Bar], yup=True)
def foobaryup(event):
    event.response.text += 'foobaryup '

@subscriber([Foo, Bar], yup=True)
def foobaryup2(event, context):
    event.response.text += 'foobaryup2 '

@view_config(name='sendfoo')
def sendfoo(request):
    response = request.response
    response.yup = True
    request.registry.notify(Foo(response))
    return response

@view_config(name='sendfoobar')
def sendfoobar(request):
    response = request.response
    response.yup = True
    request.registry.notify(Foo(response), Bar())
    return response

def includeme(config):
    config.add_subscriber_predicate('yup', Yup)
    config.scan('pyramid.tests.pkgs.eventonly')
    
