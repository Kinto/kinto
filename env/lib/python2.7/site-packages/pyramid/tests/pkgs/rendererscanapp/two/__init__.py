from pyramid.view import view_config

@view_config(name='two', renderer='json')
def two(request):
    return {'nameagain':'Two!'}

