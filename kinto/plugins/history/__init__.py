from datetime import datetime

from kinto.core.events import ResourceChanged


def on_resource_changed(event):
    bucket_id = event.payload['bucket_id']

    # XXX: POST on /buckets/test/collections does not give collection_id

    storage = event.request.registry.storage
    for impacted in event.impacted_records:
        entry = dict(userid=event.request.prefixed_userid,
                     date=datetime.now().isoformat(),
                     **event.payload)
        storage.create(parent_id="/buckets/%s" % bucket_id,
                       collection_id="history",
                       record=entry)


def includeme(config):
    config.add_api_capability("history",
                              description="Track changes on data.",
                              url="https://kinto.readthedocs.io")

    # Activate end-points.
    config.scan('kinto.plugins.history.views')

    # Listen to every resources (except history)
    config.add_subscriber(on_resource_changed, ResourceChanged,
                          for_resources=('bucket', 'group',
                                         'collection', 'record'))
