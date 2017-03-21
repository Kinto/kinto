import logging
import random
from collections import namedtuple

from pyramid.settings import asbool

from . import generators


logger = logging.getLogger(__name__)


Filter = namedtuple('Filter', ['field', 'value', 'operator'])
"""Filtering properties."""

Sort = namedtuple('Sort', ['field', 'direction'])
"""Sorting properties."""

DEFAULT_ID_FIELD = 'id'
DEFAULT_MODIFIED_FIELD = 'last_modified'
DEFAULT_DELETED_FIELD = 'deleted'

_HEARTBEAT_DELETE_RATE = 0.6
_HEARTBEAT_COLLECTION_ID = '__heartbeat__'
_HEART_PARENT_ID = _HEARTBEAT_COLLECTION_ID
_HEARTBEAT_RECORD = {'__heartbeat__': True}


class StorageBase:
    """Storage abstraction used by resource views.

    It is meant to be instantiated at application startup.
    Any operation may raise a `HTTPServiceUnavailable` error if an error
    occurs with the underlying service.

    Configuration can be changed to choose which storage backend will
    persist the objects.

    :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPServiceUnavailable`
    """

    id_generator = generators.UUID4()
    """Id generator used when no one is provided for create."""

    def initialize_schema(self, dry_run=False):
        """Create every necessary objects (like tables or indices) in the
        backend.

        This is executed when the ``kinto migrate`` command is run.

        :param bool dry_run: simulate instead of executing the operations.
        """
        raise NotImplementedError

    def flush(self, auth=None):
        """Remove **every** object from this storage.
        """
        raise NotImplementedError

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
               id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None, ignore_conflict=False):
        """Create the specified `object` in this `collection_id` for this `parent_id`.
        Assign the id to the object, using the attribute
        :attr:`kinto.core.resource.model.Model.id_field`.

        .. note::

            This will update the collection timestamp.

        :raises: :exc:`kinto.core.storage.exceptions.UnicityError`

        :param str collection_id: the collection id.
        :param str parent_id: the collection parent.
        :param dict record: the object to create.
        :param bool ignore_conflict: Do not raise the UnicityError on conflict.

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

    def update(self, collection_id, parent_id, object_id, record,
               id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None):
        """Overwrite the `object` with the specified `object_id`.

        If the specified id is not found, the object is created with the
        specified id.

        .. note::

            This will update the collection timestamp.

        :param str collection_id: the collection id.
        :param str parent_id: the collection parent.
        :param str object_id: unique identifier of the object
        :param dict record: the object to update or create.

        :returns: the updated object.
        :rtype: dict
        """
        raise NotImplementedError

    def delete(self, collection_id, parent_id, object_id,
               id_field=DEFAULT_ID_FIELD, with_deleted=True,
               modified_field=DEFAULT_MODIFIED_FIELD,
               deleted_field=DEFAULT_DELETED_FIELD,
               auth=None, last_modified=None):
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
                   sorting=None, pagination_rules=None, limit=None,
                   id_field=DEFAULT_ID_FIELD, with_deleted=True,
                   modified_field=DEFAULT_MODIFIED_FIELD,
                   deleted_field=DEFAULT_DELETED_FIELD,
                   auth=None):
        """Delete all objects in this `collection_id` for this `parent_id`.

        :param str collection_id: the collection id.
        :param str parent_id: the collection parent.

        :param filters: Optionnally filter the objects to delete.
        :type filters: list of :class:`kinto.core.storage.Filter`
        :param sorting: Optionnally sort the objects by attribute.
            Each sort instruction in this list refers to a field and a
            direction (negative means descending). All sort instructions are
            cumulative.
        :type sorting: list of :class:`kinto.core.storage.Sort`

        :param pagination_rules: Optionnally paginate the deletion of objects.
            This list of rules aims to reduce the set of objects to the current
            page. A rule is a list of filters (see `filters` parameter),
            and all rules are combined using *OR*.
        :type pagination_rules: list of list of
            :class:`kinto.core.storage.Filter`

        :param int limit: Optionnally limit the number of objects to be
            deleted.

        :param bool with_deleted: track deleted records with a tombstone

        :returns: the list of deleted objects, with minimal set of attributes.
        :rtype: list
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
        :rtype: tuple
        """
        raise NotImplementedError


def heartbeat(backend):
    def ping(request):
        """Test that storage is operationnal.

        :param request: current request object
        :type request: :class:`~pyramid:pyramid.request.Request`
        :returns: ``True`` is everything is ok, ``False`` otherwise.
        :rtype: bool
        """
        try:
            auth = request.headers.get('Authorization')
            storage_kw = dict(collection_id=_HEARTBEAT_COLLECTION_ID,
                              parent_id=_HEART_PARENT_ID,
                              auth=auth)
            if asbool(request.registry.settings.get('readonly')):
                # Do not try to write in readonly mode.
                backend.get_all(**storage_kw)
            else:
                if random.SystemRandom().random() < _HEARTBEAT_DELETE_RATE:
                    backend.delete_all(**storage_kw)
                    backend.purge_deleted(**storage_kw)  # Kinto/kinto#985
                else:
                    backend.create(record=_HEARTBEAT_RECORD, **storage_kw)
            return True
        except:
            logger.exception("Heartbeat Error")
            return False

    return ping
