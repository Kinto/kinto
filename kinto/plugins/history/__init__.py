from pyramid.settings import aslist

from kinto.authorization import PERMISSIONS_INHERITANCE_TREE
from kinto.core import metrics
from kinto.core.events import ResourceChanged

from .listener import on_resource_changed


def uri_to_dict(uri):
    """
    Convert a resource URI to a dictionary with its components.
    We don't use `kinto.core.view_lookup_registry()` here because it requires
    a request context or an initialized registry, which is not available at
    this point.
    """
    parts = uri.split("/")
    if len(parts) == 3:
        _, _buckets, bid = parts
        return {"bucket": bid}
    if len(parts) == 5:
        _, _buckets, bid, resource, rid = parts
        if resource == "collections":
            return {"bucket": bid, "collection": rid}
        return {"bucket": bid, "group": rid}
    if len(parts) == 7:
        _, _buckets, bid, _collections, cid, _records, rid = parts
        return {"bucket": bid, "collection": cid, "record": rid}
    raise ValueError(f"Invalid URI: {uri}")  # pragma: no cover


def includeme(config):
    settings = config.get_settings()
    exposed_settings = {}
    if (trim_history_max := int(settings.get("history.auto_trim_max_count", "-1"))) > 0:
        exposed_settings["auto_trim_max_count"] = trim_history_max
    if trim_user_ids := aslist(settings.get("history.auto_trim_user_ids", "")):
        exposed_settings["auto_trim_user_ids"] = trim_user_ids
    if excluded_resources := aslist(settings.get("history.exclude_resources", "")):
        exposed_settings["excluded_resources"] = [uri_to_dict(uri) for uri in excluded_resources]

    config.add_api_capability(
        "history",
        description="Track changes on data.",
        url="http://kinto.readthedocs.io/en/latest/api/1.x/history.html",
        **exposed_settings,
    )

    # Activate end-points.
    config.scan("kinto.plugins.history.views")

    wrapped_listener = metrics.listener_with_timer(config, "plugins.history", on_resource_changed)

    # Listen to every resources (except history)
    config.add_subscriber(
        wrapped_listener,
        ResourceChanged,
        for_resources=("bucket", "group", "collection", "record"),
    )

    # Register the permission inheritance for history entries.
    PERMISSIONS_INHERITANCE_TREE["history"] = {
        "read": {"bucket": ["write", "read"], "history": ["write", "read"]},
        "write": {"bucket": ["write"], "history": ["write"]},
    }
