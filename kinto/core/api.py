from cornice_swagger import CorniceSwagger
from cornice_swagger.converters.schema import TypeConverter

from kinto.core.schema import Any


class AnyTypeConverter(TypeConverter):
    """Convert type agnostic parameter to swagger."""

    def __call__(self, schema_node):
        return {}


class OpenAPI(CorniceSwagger):

    custom_type_converters = {Any: AnyTypeConverter}
    """Kinto additional type converters."""

    def __init__(self, services, request):
        super(OpenAPI, self).__init__(services)

        self.request = request
        self.settings = request.registry.settings

        self.api_title = self.settings['project_name']
        self.api_version = self.settings['http_api_version']
        self.ignore_ctypes = ['application/json-patch+json']

        try:
            self.base_path = '/v{}'.format(self.api_version.split('.')[0])
        except KeyError:
            self.base_path = '/'

    def generate(self):

        base_spec = {
            'host': self.request.host,
            'schemes': [self.settings.get('http_scheme') or 'http'],
        }

        return super(OpenAPI, self).generate(swagger=base_spec)
