import copy

from pyramid.httpexceptions import HTTPInsufficientStorage
from kinto.core.errors import http_error, ERRORS
from kinto.core.utils import instance_uri

from .utils import record_size, strip_stats_keys


def has_stats(uri):
    parts = uri.strip('/').split('/')
    parts_count = len(parts)
    # Is a bucket
    if parts_count == 2 and parts[0] == 'buckets':
        return True
    # Is a collection
    if (parts_count == 4 and parts[0] == 'buckets' and
            parts[2] == 'collections'):
        return True
    return False


def on_resource_changed(event):
    """
    Everytime an object is created/changed/deleted, we update the
    bucket counters. The entries are served as read-only in the
    :mod:`kinto.plugins.quotas.views` module.

    If a new object override the quotas, we reject the request.
    """
    payload = copy.deepcopy(event.payload)
    action = payload['action']
    resource_name = payload['resource_name']
    event_uri = payload['uri']

    settings = event.request.registry.settings

    bucket_id = payload.pop('bucket_id')
    bucket_uri = instance_uri(event.request,
                              'bucket',
                              id=bucket_id)
    collection_id = None
    collection_uri = None
    if 'collection_id' in payload:
        collection_id = payload['collection_id']
        collection_uri = instance_uri(event.request,
                                      'collection',
                                      bucket_id=bucket_id,
                                      id=collection_id)

    bucket_max_bytes = settings.get(
        'quotas.bucket_{}_max_bytes'.format(bucket_id),  # bucket specific
        settings.get('quotas.bucket_max_bytes', None)  # Global to all buckets
    )

    collection_max_bytes = settings.get(
        # Specific for a collection in a bucket
        'quotas.collection_{}_{}_max_bytes'.format(bucket_id, collection_id),
        # Specific to bucket collections
        settings.get('quotas.collection_{}_max_bytes'.format(bucket_id),
                     # Global to all buckets
                     settings.get('quotas.collection_max_bytes', None)))

    storage = event.request.registry.storage

    targets = []
    for impacted in event.impacted_records:
        target = impacted['new' if action != 'delete' else 'old']
        obj_id = target['id']
        # On POST .../records, the URI does not contain the newly created
        # record id. Make sure it does:
        if event_uri.endswith(obj_id):
            uri = event_uri
        else:
            uri = event_uri + '/' + obj_id

        old = impacted.get('old', {})
        new = impacted.get('new', {})
        targets.append((uri, obj_id, old, new))

    if action == 'delete' and resource_name == 'bucket':
        # In that case, metadata are already deleted with the bucket.
        return

    bucket_info = copy.deepcopy(
        storage.get("bucket", "", bucket_id))

    bucket_info.setdefault('collection_count', 0)
    bucket_info.setdefault('record_count', 0)
    bucket_info.setdefault('storage_size', 0)

    if collection_id and not (
            resource_name == 'collection' and action == 'delete'):
        collection_info = copy.deepcopy(
            storage.get("collection", bucket_uri, collection_id))
        if collection_id and resource_name == 'collection':
            collection_info.update(event.request.response.json['data'])

    else:
        collection_info = {}

    collection_info.setdefault('record_count', 0)
    collection_info.setdefault('storage_size', 0)

    # Update the bucket quotas values for each impacted record.
    for (uri, obj_id, old, new) in targets:
        if has_stats(uri):
            old = strip_stats_keys(old)
            new = strip_stats_keys(new)

        old_size = record_size(old)
        new_size = record_size(new)

        if action == 'create':
            bucket_info['storage_size'] += new_size
            if resource_name == 'collection':
                bucket_info['collection_count'] += 1
                collection_info['storage_size'] += new_size
            if resource_name == 'record':
                bucket_info['record_count'] += 1
                collection_info['record_count'] += 1
                collection_info['storage_size'] += new_size
        elif action == 'update':
            bucket_info['storage_size'] -= old_size
            bucket_info['storage_size'] += new_size
            if resource_name in ('collection', 'record'):
                collection_info['storage_size'] -= old_size
                collection_info['storage_size'] += new_size
        elif action == 'delete':
            bucket_info['storage_size'] -= old_size
            if resource_name == 'collection':
                bucket_info['collection_count'] -= 1
                # When we delete the collection all the records in it
                # are deleted without notification.
                collection_records, _ = storage.get_all('record',
                                                        collection_uri)
                for r in collection_records:
                    old_record_size = record_size(r)
                    bucket_info['record_count'] -= 1
                    bucket_info['storage_size'] -= old_record_size
                    collection_info['record_count'] -= 1
                    collection_info['storage_size'] -= old_record_size
                collection_info['storage_size'] -= old_size

            if resource_name == 'record':
                bucket_info['record_count'] -= 1
                collection_info['record_count'] -= 1
                collection_info['storage_size'] -= old_size

    if bucket_max_bytes is not None:
        if bucket_info['storage_size'] > bucket_max_bytes:
            raise http_error(HTTPInsufficientStorage(),
                             errno=ERRORS.FORBIDDEN.value,
                             message=HTTPInsufficientStorage.explanation)

    if collection_max_bytes is not None:
        if collection_info['storage_size'] > collection_max_bytes:
            raise http_error(HTTPInsufficientStorage(),
                             errno=ERRORS.FORBIDDEN.value,
                             message=HTTPInsufficientStorage.explanation)

    storage.update(parent_id="",
                   collection_id='bucket',
                   object_id=bucket_id,
                   record=bucket_info)

    if not (resource_name == 'collection' and action == 'delete'):
        storage.update(parent_id=bucket_uri,
                       collection_id='collection',
                       object_id=collection_id,
                       record=collection_info)
