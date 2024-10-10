from kinto.core import metrics
from kinto.core.events import ResourceChanged

from .listener import on_resource_changed


def includeme(config):
    config.add_api_capability(
        "quotas",
        description="Quotas Management on buckets " "and collections.",
        url="https://kinto.readthedocs.io",
    )

    wrapped_listener = metrics.listener_with_timer(config, "plugins.quotas", on_resource_changed)

    # Listen to every resources (except history)
    config.add_subscriber(
        wrapped_listener,
        ResourceChanged,
        for_resources=("bucket", "group", "collection", "record"),
    )
