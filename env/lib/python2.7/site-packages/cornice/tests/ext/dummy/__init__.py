from pyramid.config import Configurator


def main(global_config, **settings):
    config = Configurator(settings=settings)
    # adds cornice
    config.include("cornice")
    # adds application-specific views
    config.include("cornice.tests.ext.dummy.views.includeme")
    return config.make_wsgi_app()


if __name__ == '__main__':
    main({})
