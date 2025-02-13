import importlib
from string import Template

import cornice
import cornice_swagger
import pkg_resources
from pyramid.response import Response


# hardcode for now since that will work for vast majority of users
# maybe later add minified resources for behind firewall support?
ui_css_url = "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.23.11/swagger-ui.css"
ui_js_bundle_url = "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.23.11/swagger-ui-bundle.js"
ui_js_standalone_url = (
    "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.23.11/swagger-ui-standalone-preset.js"
)


def swagger_ui_template_view(request):
    """
    Serves Swagger UI page, default Swagger UI config is used but you can
    override the callable that generates the `<script>` tag by setting
    `cornice_swagger.swagger_ui_script_generator` in pyramid config, it defaults
    to 'cornice_swagger.views:swagger_ui_script_template'

    :param request:
    :return:
    """
    script_generator = request.registry.settings.get(
        "cornice_swagger.swagger_ui_script_generator",
        "cornice_swagger.views:swagger_ui_script_template",
    )
    package, callable = script_generator.split(":")
    imported_package = importlib.import_module(package)
    script_callable = getattr(imported_package, callable)
    template = pkg_resources.resource_string("cornice_swagger", "templates/index.html").decode(
        "utf8"
    )

    html = Template(template).safe_substitute(
        ui_css_url=ui_css_url,
        ui_js_bundle_url=ui_js_bundle_url,
        ui_js_standalone_url=ui_js_standalone_url,
        swagger_ui_script=script_callable(request),
    )
    return Response(html)


def open_api_json_view(request):
    """
    :param request:
    :return:

    Generates JSON representation of Swagger spec
    """
    doc = cornice_swagger.CorniceSwagger(
        cornice.service.get_services(), pyramid_registry=request.registry
    )
    kwargs = request.registry.settings["cornice_swagger.spec_kwargs"]
    my_spec = doc.generate(**kwargs)
    return my_spec


def swagger_ui_script_template(request, **kwargs):
    """
    :param request:
    :return:

    Generates the <script> code that bootstraps Swagger UI, it will be injected
    into index template
    """
    swagger_spec_url = request.route_url("cornice_swagger.open_api_path")
    template = pkg_resources.resource_string(
        "cornice_swagger", "templates/index_script_template.html"
    ).decode("utf8")
    return Template(template).safe_substitute(
        swagger_spec_url=swagger_spec_url,
    )
