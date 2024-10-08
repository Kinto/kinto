from kinto.core.events import ResourceChanged

from .listener import on_resource_changed


def includeme(config):
    config.add_api_capability(
        "quotas",
        description="Quotas Management on buckets " "and collections.",
        url="https://kinto.readthedocs.io",
    )

    # If metrics are enabled, monitor execution time of listener.
    listener = on_resource_changed
    if config.registry.metrics:
        key = "plugins.quotas"
        listener = config.registry.metrics.timer(key)(on_resource_changed)

    # Listen to every resources (except history)
    config.add_subscriber(
        listener, ResourceChanged, for_resources=("bucket", "group", "collection", "record")
    )
