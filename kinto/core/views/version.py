import json
import os

import colander
from pyramid.security import NO_PERMISSION_REQUIRED
from kinto.core import Service

HERE = os.path.dirname(__file__)
ORIGIN = os.path.dirname(HERE)


class VersionResponseSchema(colander.MappingSchema):
    body = colander.SchemaNode(colander.Mapping(unknown="preserve"))


version_response_schemas = {
    "200": VersionResponseSchema(description="Return the running Instance version information.")
}


version = Service(name="version", path="/__version__", description="Version")


@version.get(
    permission=NO_PERMISSION_REQUIRED,
    tags=["Utilities"],
    operation_id="__version__",
    response_schemas=version_response_schemas,
)
def version_view(request):
    try:
        return version_view.__json__
    except AttributeError:
        pass

    location = request.registry.settings["version_json_path"]
    files = [
        location,  # Default is current working dir.
        os.path.join(ORIGIN, "version.json"),  # Relative to the package root.
        os.path.join(HERE, "version.json"),  # Relative to this file.
    ]
    for version_file in files:
        if os.path.exists(version_file):
            with open(version_file) as f:
                version_view.__json__ = json.load(f)
                return version_view.__json__  # First one wins.

    raise FileNotFoundError("Version file missing from {}".format(files.join(",")))
