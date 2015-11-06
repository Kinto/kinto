import binascii
import os
from pyramid.renderers import render_to_response
from pyramid.scaffolds import PyramidTemplate

class generatorTemplate(PyramidTemplate):
    _template_dir = 'generator_scaffold'
    summary = 'My cool extension'
    def sample_view(request):
     return render_to_response('generator_scaffold/kinto.ini_tmpl',
                              {'foo':1, 'bar':2},
                              request=request)

