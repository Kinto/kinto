from pyramid.httpexceptions import HTTPException

def includeme(config):
    config.add_route('route_raise_exception', 'route_raise_exception')
    config.add_route('route_raise_httpexception', 'route_raise_httpexception')
    config.add_route('route_raise_exception2', 'route_raise_exception2',
                     factory='.models.route_factory')
    config.add_route('route_raise_exception3', 'route_raise_exception3',
                    factory='.models.route_factory2')
    config.add_route('route_raise_exception4', 'route_raise_exception4')
    config.add_view('.views.maybe')
    config.add_view('.views.no', context='.models.NotAnException')
    config.add_view('.views.yes', context=".models.AnException")
    config.add_view('.views.raise_exception', name='raise_exception')
    config.add_view('.views.raise_exception',
                    route_name='route_raise_exception')
    config.add_view('.views.raise_exception',
                    route_name='route_raise_exception2')
    config.add_view('.views.raise_exception',
                    route_name='route_raise_exception3')
    config.add_view('.views.whoa', context='.models.AnException',
                    route_name='route_raise_exception3')
    config.add_view('.views.raise_exception',
                    route_name='route_raise_exception4')
    config.add_view('.views.whoa', context='.models.AnException',
                    route_name='route_raise_exception4')
    config.add_view('.views.raise_httpexception',
                    route_name='route_raise_httpexception')
    config.add_view('.views.catch_httpexception', context=HTTPException)
    
                    
