def includeme(config):
    config.add_view('.views.fixture_view')
    config.add_view('.views.exception_view', context=RuntimeError)
    config.add_view('.views.protected_view', name='protected.html')
    config.add_view('.views.erroneous_view', name='error.html')
    config.add_view('.views.fixture_view', name='dummyskin.html',
                    request_type='.views.IDummy')
    from .models import fixture, IFixture
    config.registry.registerUtility(fixture, IFixture)
    config.add_view('.views.fixture_view', name='another.html')

    
