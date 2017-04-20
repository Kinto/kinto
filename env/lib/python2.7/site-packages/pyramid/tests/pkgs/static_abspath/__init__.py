import os

def includeme(config):
    here =  here = os.path.dirname(__file__)
    fixtures = os.path.normpath(os.path.join(here, '..', '..', 'fixtures'))
    config.add_static_view('/', fixtures)

