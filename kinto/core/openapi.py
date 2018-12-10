from cornice_swagger import CorniceSwagger
from cornice_swagger.converters.schema import TypeConverter

from kinto.core.schema import Any


class AnyTypeConverter(TypeConverter):
    """Convert type agnostic parameter to swagger."""

    def __call__(self, schema_node):
        return {}


class OpenAPI(CorniceSwagger):
    """OpenAPI documentation generator."""

    custom_type_converters = {Any: AnyTypeConverter}
    """Kinto additional type converters."""

    security_definitions = {}
    """Kinto security definitions. May be used for setting other security methods."""

    security_roles = {}
    """Kinto resource security roles. May be used for setting OAuth roles by plugins."""

    @classmethod
    def expose_authentication_method(cls, method_name, definition):
        """Allow security extensions to expose authentication methods on the
        OpenAPI documentation. The definition field should correspond to a
        valid OpenAPI security definition. Refer the OpenAPI 2.0 specification
        for more information.
        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md

        Below are some examples for BasicAuth and OAuth2::

            {
                "type": "basic",
                "description" "My basicauth method."

            }

            {
                "type": "oauth2",
                "authorizationUrl": "https://oauth-stable.dev.lcip.org/v1",
                "flow": "implicit",
                "scopes": {"kinto": "Kinto user scope."}
            }

        """
        cls.security_definitions[method_name] = definition
        cls.security_roles[method_name] = definition.get("scopes", {}).keys()

    def __init__(self, services, request):
        super().__init__(services)

        self.request = request
        self.settings = request.registry.settings

        self.api_title = self.settings["project_name"]
        self.api_version = self.settings["http_api_version"]
        self.ignore_ctypes = ["application/json-patch+json"]

        # Matches the base routing address - See kinto.core.initialization
        self.base_path = f"/v{self.api_version.split('.')[0]}"

    def generate(self):
        base_spec = {
            "host": self.request.host,
            "schemes": [self.settings.get("http_scheme") or "http"],
            "securityDefinitions": self.security_definitions,
        }

        return super(OpenAPI, self).generate(swagger=base_spec)

    def default_tags(self, service, method):
        """Povides default tags to views."""

        base_tag = service.name.capitalize()
        base_tag = base_tag.replace("-plural", "s")
        base_tag = base_tag.replace("-object", "s")

        return [base_tag]

    def default_op_ids(self, service, method):
        """Povides default operation ids to methods if not defined on view."""

        method = method.lower()
        method_mapping = {"post": "create", "put": "update"}
        if method in method_mapping:
            method = method_mapping[method]

        resource = service.name
        if method == "create":
            resource = resource.replace("-plural", "")

        resource = resource.replace("-plural", "s")
        resource = resource.replace("-object", "")
        op_id = f"{method}_{resource}"

        return op_id

    def default_security(self, service, method):
        """Provides OpenAPI security properties based on kinto policies."""

        definitions = service.definitions

        # Get method view arguments
        for definition in definitions:  # pragma: no branch
            met, view, args = definition
            if met == method:
                break

        if args.get("permission") == "__no_permission_required__":
            return []
        else:
            return [{name: list(roles)} for name, roles in self.security_roles.items()]
