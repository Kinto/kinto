from pyramid.security import NO_PERMISSION_REQUIRED

from kinto.core import Service


counters = Service(name="counters", description="Shows objects statistics", path="/__counters__")


@counters.get(permission=NO_PERMISSION_REQUIRED)
def counters_get(request):
    storage = request.registry.storage
    counters = {"objects": {}, "tombstones": {}}
    for resource_name in (
        "account",
        "bucket",
        "group",
        "collection",
        "record",
        "history",
        "attachments",
    ):
        count_with_deleted = storage.count_all(resource_name, parent_id="*", include_deleted=True)
        count_active = storage.count_all(resource_name, parent_id="*")
        if count_active > 0:
            counters["objects"][resource_name] = count_active
        if (count_tombstones := count_with_deleted - count_active) > 0:
            counters["tombstones"][resource_name] = count_tombstones
    return counters


def includeme(config):
    config.add_api_capability(
        "counters_endpoint",
        description="The __counters__ endpoint exposes how many objects are stored.",
        url="https://kinto.readthedocs.io/en/latest/api/1.x/counters.html",
    )
    config.add_cornice_service(counters)
