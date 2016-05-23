from __future__ import absolute_import, unicode_literals
from functools import wraps

import pymongo
from six.moves.urllib import parse as urlparse

from kinto.core import utils, logger
from kinto.core.storage import (
    exceptions, DEFAULT_ID_FIELD,
    DEFAULT_MODIFIED_FIELD, DEFAULT_DELETED_FIELD)
from kinto.core.storage import StorageBase


def create_from_config(config, prefix=''):
    """Mongo client instantiation from settings.
    """
    settings = config.get_settings()
    uri = settings[prefix + 'url']
    client = pymongo.MongoClient(uri)
    return client


class Storage(StorageBase):
    """Storage backend implementation using Mongo.

    Enable in configuration::

        kinto.storage_backend = kinto.core.storage.mongo

    *(Optional)* Instance location URI can be customized::

        kinto.storage_url = mongo://localhost:27017/test
    """

    def __init__(self, client, *args, **kwargs):
        super(Storage, self).__init__(*args, **kwargs)
        self._client = client

    def initialize_schema(self):
        """ Nothing to do
        """
        pass

    def flush(self, auth=None):
        """Remove **every** object from this storage.
        """
        pass

    def collection_timestamp(self, collection_id, parent_id, auth=None):
        """Get the highest timestamp of every objects in this `collection_id` for
        this `parent_id`.

        .. note::

            This should take deleted objects into account.

        :param str collection_id: the collection id.
        :param str parent_id: the collection parent.

        :returns: the latest timestamp of the collection.
        :rtype: int
        """
        raise NotImplementedError

    def create(self, collection_id, parent_id, record, id_generator=None,
               unique_fields=None, id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None):
        """Create the specified `object` in this `collection_id` for this `parent_id`.
        Assign the id to the object, using the attribute
        :attr:`kinto.core.resource.Model.id_field`.

        .. note::

            This will update the collection timestamp.

        :raises: :exc:`kinto.core.storage.exceptions.UnicityError`

        :param str collection_id: the collection id.
        :param str parent_id: the collection parent.

        :param dict object: the object to create.

        :returns: the newly created object.
        :rtype: dict
        """
        raise NotImplementedError

    def get(self, collection_id, parent_id, object_id,
            id_field=DEFAULT_ID_FIELD,
            modified_field=DEFAULT_MODIFIED_FIELD,
            auth=None):
        """Retrieve the object with specified `object_id`, or raise error
        if not found.

        :raises: :exc:`kinto.core.storage.exceptions.RecordNotFoundError`

        :param str collection_id: the collection id.
        :param str parent_id: the collection parent.

        :param str object_id: unique identifier of the object

        :returns: the object object.
        :rtype: dict
        """
        raise NotImplementedError

    def update(self, collection_id, parent_id, object_id, object,
               unique_fields=None, id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None):
        """Overwrite the `object` with the specified `object_id`.

        If the specified id is not found, the object is created with the
        specified id.

        .. note::

            This will update the collection timestamp.

        :raises: :exc:`kinto.core.storage.exceptions.UnicityError`

        :param str collection_id: the collection id.
        :param str parent_id: the collection parent.

        :param str object_id: unique identifier of the object
        :param dict object: the object to update or create.

        :returns: the updated object.
        :rtype: dict
        """
        raise NotImplementedError

    def delete(self, collection_id, parent_id, object_id,
               with_deleted=True, id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               deleted_field=DEFAULT_DELETED_FIELD,
               auth=None):
        """Delete the object with specified `object_id`, and raise error
        if not found.

        Deleted objects must be removed from the database, but their ids and
        timestamps of deletion must be tracked for synchronization purposes.
        (See :meth:`kinto.core.storage.StorageBase.get_all`)

        .. note::

            This will update the collection timestamp.

        :raises: :exc:`kinto.core.storage.exceptions.RecordNotFoundError`

        :param str collection_id: the collection id.
        :param str parent_id: the collection parent.

        :param str object_id: unique identifier of the object
        :param bool with_deleted: track deleted record with a tombstone

        :returns: the deleted object, with minimal set of attributes.
        :rtype: dict
        """
        raise NotImplementedError

    def delete_all(self, collection_id, parent_id, filters=None,
                   with_deleted=True, id_field=DEFAULT_ID_FIELD,
                   modified_field=DEFAULT_MODIFIED_FIELD,
                   deleted_field=DEFAULT_DELETED_FIELD,
                   auth=None):
        """Delete all objects in this `collection_id` for this `parent_id`.

        :param str collection_id: the collection id.
        :param str parent_id: the collection parent.

        :param filters: Optionnally filter the objects to delete.
        :type filters: list of :class:`kinto.core.storage.Filter`
        :param bool with_deleted: track deleted records with a tombstone

        :returns: the list of deleted objects, with minimal set of attributes.
        :rtype: list of dict
        """
        raise NotImplementedError

    def purge_deleted(self, collection_id, parent_id, before=None,
                      id_field=DEFAULT_ID_FIELD,
                      modified_field=DEFAULT_MODIFIED_FIELD,
                      auth=None):
        """Delete all deleted object tombstones in this `collection_id`
        for this `parent_id`.

        :param str collection_id: the collection id.
        :param str parent_id: the collection parent.

        :param int before: Optionnal timestamp to limit deletion (exclusive)

        :returns: The number of deleted objects.
        :rtype: int

        """
        raise NotImplementedError

    def get_all(self, collection_id, parent_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False,
                id_field=DEFAULT_ID_FIELD,
                modified_field=DEFAULT_MODIFIED_FIELD,
                deleted_field=DEFAULT_DELETED_FIELD,
                auth=None):
        """Retrieve all objects in this `collection_id` for this `parent_id`.

        :param str collection_id: the collection id.
        :param str parent_id: the collection parent.

        :param filters: Optionally filter the objects by their attribute.
            Each filter in this list is a tuple of a field, a value and a
            comparison (see `kinto.core.utils.COMPARISON`). All filters
            are combined using *AND*.
        :type filters: list of :class:`kinto.core.storage.Filter`

        :param sorting: Optionnally sort the objects by attribute.
            Each sort instruction in this list refers to a field and a
            direction (negative means descending). All sort instructions are
            cumulative.
        :type sorting: list of :class:`kinto.core.storage.Sort`

        :param pagination_rules: Optionnally paginate the list of objects.
            This list of rules aims to reduce the set of objects to the current
            page. A rule is a list of filters (see `filters` parameter),
            and all rules are combined using *OR*.
        :type pagination_rules: list of list of
            :class:`kinto.core.storage.Filter`

        :param int limit: Optionnally limit the number of objects to be
            retrieved.

        :param bool include_deleted: Optionnally include the deleted objects
            that match the filters.

        :returns: the limited list of objects, and the total number of
            matching objects in the collection (deleted ones excluded).
        :rtype: tuple (list, integer)
        """
        raise NotImplementedError


def load_from_config(config):
    client = create_from_config(config, prefix='storage_')
    return Storage(client)
