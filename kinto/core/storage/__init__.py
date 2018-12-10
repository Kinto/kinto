import json
import logging
import random
import warnings
from collections import namedtuple

from pyramid.settings import asbool
import ujson

from . import generators


class Missing:
    """Dummy value to represent a value that is completely absent from an object.

    Handling these correctly is important for pagination.
    """

    pass


MISSING = Missing()


logger = logging.getLogger(__name__)


Filter = namedtuple("Filter", ["field", "value", "operator"])
"""Filtering properties."""

Sort = namedtuple("Sort", ["field", "direction"])
"""Sorting properties."""

DEFAULT_ID_FIELD = "id"
DEFAULT_MODIFIED_FIELD = "last_modified"
DEFAULT_DELETED_FIELD = "deleted"

_HEARTBEAT_DELETE_RATE = 0.6
_HEARTBEAT_RESOURCE_NAME = "__heartbeat__"
_HEART_PARENT_ID = _HEARTBEAT_RESOURCE_NAME
_HEARTBEAT_OBJECT = {"__heartbeat__": True}


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

    def __init__(self, strict_json=True):
        """initialize json (de)serializer to be the strict, slow json or ujson"""
        if strict_json:
            self.json = json
        else:
            self.json = ujson

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

    def resource_timestamp(self, resource_name, parent_id, auth=None):
        """Get the highest timestamp of every objects in this `resource_name` for
        this `parent_id`.

        .. note::

            This should take deleted objects into account.

        :param str resource_name: the resource name.
        :param str parent_id: the resource parent.

        :returns: the latest timestamp of the resource.
        :rtype: int
        """
        raise NotImplementedError

    def create(
        self,
        resource_name,
        parent_id,
        obj,
        id_generator=None,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        auth=None,
    ):
        """Create the specified `obj` in this `resource_name` for this `parent_id`.
        Assign the id to the object, using the attribute
        :attr:`kinto.core.resource.model.Model.id_field`.

        .. note::

            This will update the resource timestamp.

        :raises: :exc:`kinto.core.storage.exceptions.UnicityError`

        :param str resource_name: the resource name.
        :param str parent_id: the resource parent.
        :param dict obj: the object to create.

        :returns: the newly created object.
        :rtype: dict
        """
        raise NotImplementedError

    def get(
        self,
        resource_name,
        parent_id,
        object_id,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        auth=None,
    ):
        """Retrieve the object with specified `object_id`, or raise error
        if not found.

        :raises: :exc:`kinto.core.storage.exceptions.ObjectNotFoundError`

        :param str resource_name: the resource name.
        :param str parent_id: the resource parent.

        :param str object_id: unique identifier of the object

        :returns: the stored object.
        :rtype: dict
        """
        raise NotImplementedError

    def update(
        self,
        resource_name,
        parent_id,
        object_id,
        obj,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        auth=None,
    ):
        """Overwrite the `obj` with the specified `object_id`.

        If the specified id is not found, the object is created with the
        specified id.

        .. note::

            This will update the resource timestamp.

        :param str resource_name: the resource name.
        :param str parent_id: the resource parent.
        :param str object_id: unique identifier of the object
        :param dict obj: the object to update or create.

        :returns: the updated object.
        :rtype: dict
        """
        raise NotImplementedError

    def delete(
        self,
        resource_name,
        parent_id,
        object_id,
        id_field=DEFAULT_ID_FIELD,
        with_deleted=True,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
        auth=None,
        last_modified=None,
    ):
        """Delete the object with specified `object_id`, and raise error
        if not found.

        Deleted objects must be removed from the database, but their ids and
        timestamps of deletion must be tracked for synchronization purposes.
        (See :meth:`kinto.core.storage.StorageBase.get_all`)

        .. note::

            This will update the resource timestamp.

        :raises: :exc:`kinto.core.storage.exceptions.ObjectNotFoundError`

        :param str resource_name: the resource name.
        :param str parent_id: the resource parent.

        :param str object_id: unique identifier of the object
        :param bool with_deleted: track deleted object with a tombstone

        :returns: the deleted object, with minimal set of attributes.
        :rtype: dict
        """
        raise NotImplementedError

    def delete_all(
        self,
        resource_name,
        parent_id,
        filters=None,
        sorting=None,
        pagination_rules=None,
        limit=None,
        id_field=DEFAULT_ID_FIELD,
        with_deleted=True,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
        auth=None,
    ):
        """Delete all objects in this `resource_name` for this `parent_id`.

        :param str resource_name: the resource name.
        :param str parent_id: the resource parent.

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

        :param bool with_deleted: track deleted objects with a tombstone

        :returns: the list of deleted objects, with minimal set of attributes.
        :rtype: list
        """
        raise NotImplementedError

    def purge_deleted(
        self,
        resource_name,
        parent_id,
        before=None,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        auth=None,
    ):
        """Delete all deleted object tombstones in this `resource_name`
        for this `parent_id`.

        :param str resource_name: the resource name.
        :param str parent_id: the resource parent.

        :param int before: Optionnal timestamp to limit deletion (exclusive)

        :returns: The number of deleted objects.
        :rtype: int

        """
        raise NotImplementedError

    def get_all(
        self,
        resource_name,
        parent_id,
        filters=None,
        sorting=None,
        pagination_rules=None,
        limit=None,
        include_deleted=False,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
        auth=None,
    ):
        """Retrieve all objects in this `resource_name` for this `parent_id`.

        :param str resource_name: the resource name.

        :param str parent_id: the resource parent, possibly
            containing a wildcard '*'. (This can happen when
            implementing "administrator" operations on a UserResource,
            for example.)

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
            matching objects in the resource (deleted ones excluded).
        :rtype: tuple
        """
        raise NotImplementedError

    def collection_timestamp(self, collection_id, parent_id, auth=None):
        message = "`collection_timestamp()` is deprecated, use `resource_timestamp()` instead."
        warnings.warn(message, DeprecationWarning)
        return self.resource_timestamp(resource_name=collection_id, parent_id=parent_id, auth=auth)


def heartbeat(backend):
    def ping(request):
        """Test that storage is operational.

        :param request: current request object
        :type request: :class:`~pyramid:pyramid.request.Request`
        :returns: ``True`` is everything is ok, ``False`` otherwise.
        :rtype: bool
        """
        try:
            auth = request.headers.get("Authorization")
            storage_kw = dict(
                resource_name=_HEARTBEAT_RESOURCE_NAME, parent_id=_HEART_PARENT_ID, auth=auth
            )
            if asbool(request.registry.settings.get("readonly")):
                # Do not try to write in readonly mode.
                backend.get_all(**storage_kw)
            else:
                if random.SystemRandom().random() < _HEARTBEAT_DELETE_RATE:
                    backend.delete_all(**storage_kw)
                    backend.purge_deleted(**storage_kw)  # Kinto/kinto#985
                else:
                    backend.create(obj=_HEARTBEAT_OBJECT, **storage_kw)
            return True
        except Exception:
            logger.exception("Heartbeat Error")
            return False

    return ping
