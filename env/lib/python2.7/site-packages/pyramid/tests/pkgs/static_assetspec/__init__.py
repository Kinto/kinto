def includeme(config):
    config.add_static_view('/', 'pyramid.tests:fixtures')

