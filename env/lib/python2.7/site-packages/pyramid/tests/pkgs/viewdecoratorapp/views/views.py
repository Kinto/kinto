from pyramid.view import view_config

@view_config(renderer='json', name='first')
def first(request):
    return {'result':'OK1'}

@view_config(
    renderer='json',
             name='second')
def second(request):
    return {'result':'OK2'}

