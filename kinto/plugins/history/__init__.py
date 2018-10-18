from kinto.authorization import PERMISSIONS_INHERITANCE_TREE
from kinto.core.events import ResourceChanged

from .listener import on_resource_changed


def includeme(config):
    config.add_api_capability(
        "history",
        description="Track changes on data.",
        url="http://kinto.readthedocs.io/en/latest/api/1.x/history.html",
    )

    # Activate end-points.
    config.scan("kinto.plugins.history.views")

    # If StatsD is enabled, monitor execution time of listener.
    listener = on_resource_changed
    if config.registry.statsd:
        key = "plugins.history"
        listener = config.registry.statsd.timer(key)(on_resource_changed)

    # Listen to every resources (except history)
    config.add_subscriber(
        listener, ResourceChanged, for_resources=("bucket", "group", "collection", "record")
    )

    # Register the permission inheritance for history entries.
    PERMISSIONS_INHERITANCE_TREE["history"] = {
        "read": {"bucket": ["write", "read"], "history": ["write", "read"]},
        "write": {"bucket": ["write"], "history": ["write"]},
    }
