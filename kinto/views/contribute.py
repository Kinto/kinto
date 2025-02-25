import json
import os

import colander
from pyramid.security import NO_PERMISSION_REQUIRED

from kinto.core import Service


HERE = os.path.dirname(__file__)
ORIGIN = os.path.dirname(HERE)  # package root.
_CONTRIBUTE_INFO = None

contribute = Service(
    name="contribute.json", description="Open-source information", path="/contribute.json"
)


class ContributeResponseSchema(colander.MappingSchema):
    body = colander.SchemaNode(colander.Mapping(unknown="preserve"))


contribute_responses = {
    "200": ContributeResponseSchema(description="Return open source contributing information.")
}


@contribute.get(
    permission=NO_PERMISSION_REQUIRED,
    tags=["Utilities"],
    operation_id="contribute",
    response_schemas=contribute_responses,
)
def contribute_get(request):
    global _CONTRIBUTE_INFO
    if _CONTRIBUTE_INFO is None:
        with open(os.path.join(ORIGIN, "contribute.json")) as f:
            _CONTRIBUTE_INFO = json.load(f)
    return _CONTRIBUTE_INFO
