import colander
from cornice import Service
from pyramid.security import NO_PERMISSION_REQUIRED

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
    return {
        "name": "kinto",
        "description": "A minimalist JSON storage service.",
        "repository": {"url": "https://github.com/Kinto/kinto", "license": "Apache License (2.0)"},
        "participate": {
            "docs": "https://kinto.readthedocs.io/",
            "mailing-list": "kinto@mozilla.org",
            "irc": "irc://irc.freenode.net/#kinto",
        },
        "keywords": ["JSON", "Python", "Offline", "Sync", "Storage"],
        "urls": {"dev": "https://kinto.dev.mozaws.net/v1/"},
    }
