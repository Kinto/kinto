from pyramid.view import view_config


@view_config(route_name='home', renderer='kinto_project_2:templates/mytemplate.jinja2')
def my_view(request):
    return {'project': 'kinto_project_2'}
