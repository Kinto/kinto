from pyramid.view import view_config
from pyramid.renderers import null_renderer

@view_config(name='subsubpackage_init', renderer=null_renderer)
def subpackage_init(context, request):
    return 'subsubpackage_init'
