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
