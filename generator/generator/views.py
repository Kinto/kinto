from pyramid.view import view_config


@view_config(route_name='home', renderer='generator/scaffolds/generator_scaffold/kinto.ini_tmpl')
def my_view(request):
    return {'secret': 'generator'}
