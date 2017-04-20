from pyramid.config import Configurator
from pyramid.request import Request

def view_one(request):
    subreq = Request.blank('/view_two')
    response = request.invoke_subrequest(subreq, use_tweens=False)
    return response

def view_two(request):
    return 'This came from view_two'

def view_three(request):
    subreq = Request.blank('/view_four')
    try:
        return request.invoke_subrequest(subreq, use_tweens=True)
    except: # pragma: no cover
        request.response.body = b'Value error raised'
        return request.response

def view_four(request):
    raise ValueError('foo')

def view_five(request):
    subreq = Request.blank('/view_four')
    try:
        return request.invoke_subrequest(subreq, use_tweens=False)
    except ValueError:
        request.response.body = b'Value error raised'
        return request.response

def excview(request):
    request.response.status_int = 500
    request.response.body = b'Bad stuff happened'
    return request.response

def main():
    config = Configurator()
    config.add_route('one', '/view_one')
    config.add_route('two', '/view_two')
    config.add_route('three', '/view_three')
    config.add_route('four', '/view_four')
    config.add_route('five', '/view_five')
    config.add_view(excview, context=Exception)
    config.add_view(view_one, route_name='one')
    config.add_view(view_two, route_name='two', renderer='string')
    config.add_view(view_three, route_name='three')
    config.add_view(view_four, route_name='four')
    config.add_view(view_five, route_name='five')
    return config

