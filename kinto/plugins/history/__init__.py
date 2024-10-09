from kinto.authorization import PERMISSIONS_INHERITANCE_TREE
from kinto.core import metrics
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
