from pyramid.view import view_config

@view_config(name='two', renderer='string')
def two(request):
    return 'two'

