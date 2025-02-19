from pyramid.security import NO_PERMISSION_REQUIRED

from kinto.core.cornice_swagger.swagger import CorniceSwagger


__author__ = """Josip Delic"""
__email__ = "delicj@delijati.net"
__version__ = "0.3.0"


__all__ = ["CorniceSwagger"]


class CorniceSwaggerPredicate(object):
    """Predicate to add simple information to Cornice Swagger."""

    def __init__(self, schema, config):
        self.schema = schema

    def phash(self):
        return str(self.schema)

    def __call__(self, context, request):
        return self.schema


def includeme(config):
    # Custom view parameters
    config.add_view_predicate("response_schemas", CorniceSwaggerPredicate)
    config.add_view_predicate("tags", CorniceSwaggerPredicate)
    config.add_view_predicate("operation_id", CorniceSwaggerPredicate)
    config.add_view_predicate("api_security", CorniceSwaggerPredicate)
    config.add_directive("cornice_enable_openapi_view", cornice_enable_openapi_view)
    config.add_directive("cornice_enable_openapi_explorer", cornice_enable_openapi_explorer)


def cornice_enable_openapi_view(
    config,
    api_path="/api-explorer/swagger.json",
    permission=NO_PERMISSION_REQUIRED,
    route_factory=None,
    **kwargs,
):
    """
    :param config:
        Pyramid configurator object
    :param api_path:
        where to expose swagger JSON definition view
    :param permission:
        pyramid permission for those views
    :param route_factory:
        factory for context object for those routes
    :param kwargs:
        kwargs that will be passed to CorniceSwagger's `generate()`

    This registers and configures the view that serves api definitions
    """
    config.registry.settings["cornice_swagger.spec_kwargs"] = kwargs
    config.add_route("cornice_swagger.open_api_path", api_path, factory=route_factory)
    config.add_view(
        "cornice_swagger.views.open_api_json_view",
        renderer="json",
        permission=permission,
        route_name="cornice_swagger.open_api_path",
    )


def cornice_enable_openapi_explorer(
    config,
    api_explorer_path="/api-explorer",
    permission=NO_PERMISSION_REQUIRED,
    route_factory=None,
    **kwargs,
):
    """
    :param config:
        Pyramid configurator object
    :param api_explorer_path:
        where to expose Swagger UI interface view
    :param permission:
        pyramid permission for those views
    :param route_factory:
        factory for context object for those routes

    This registers and configures the view that serves api explorer
    """
    config.add_route("cornice_swagger.api_explorer_path", api_explorer_path, factory=route_factory)
    config.add_view(
        "cornice_swagger.views.swagger_ui_template_view",
        permission=permission,
        route_name="cornice_swagger.api_explorer_path",
    )
