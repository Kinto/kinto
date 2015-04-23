import random
from collections import namedtuple


Filter = namedtuple('Filter', ['field', 'value', 'operator'])
"""Filtering properties."""

Sort = namedtuple('Sort', ['field', 'direction'])
"""Sorting properties."""


_HEARTBEAT_DELETE_RATE = 0.6
_HEARTBEAT_USER_ID = '__heartbeat__'
_HEARTBEAT_RECORD = {'__heartbeat__': True}


class StorageBase(object):
    """Storage abstraction used by resource views.

    It is meant to be instantiated at application startup.
    Any operation may raise a `HTTPServiceUnavailable` error if an error
    occurs with the underlying service.

    Configuration can be changed to choose which storage backend will
    persist the records.

    :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPServiceUnavailable`
    """
    def initialize_schema(self):
        """Create every necessary objects (like tables or indices) in the
        backend.

        This is excuted when the ``cliquet migrate`` command is ran.
        """
        raise NotImplementedError

    def flush(self):
        """Remove **every** record from this storage.
        """
        raise NotImplementedError

    def ping(self, request):
        """Test that storage is operationnal.

        :param key: current request object
        :type key: :class:`~pyramid:pyramid.request.Request`
        :returns: ``True`` is everything is ok, ``False`` otherwise.
        :rtype: bool
        """
        from cliquet.resource import BaseResource

        resource = BaseResource(request)
        try:
            if random.random() < _HEARTBEAT_DELETE_RATE:
                self.delete_all(resource, _HEARTBEAT_USER_ID)
            else:
                self.create(resource, _HEARTBEAT_USER_ID, _HEARTBEAT_RECORD)
            return True
        except:
            return False

    def collection_timestamp(self, resource, user_id):
        """Get the highest timestamp of every records in this `resource` for
        this `user_id`.

        .. note::

            This should take deleted records into account.

        :param resource: the record associated resource
        :type resource: :class:`cliquet.resource.BaseResource`

        :param str user_id: the owner of the record

        :returns: the latest timestamp of the collection.
        :rtype: int
        """
        raise NotImplementedError

    def create(self, resource, user_id, record):
        """Create the specified `record` in this `resource` for this `user_id`.
        Assign the id to the record, using the attribute
        :attr:`cliquet.resource.BaseResource.id_field`.

        .. note::

            This will update the collection timestamp.

        :raises: :exc:`cliquet.storage.exceptions.UnicityError`

        :param resource: the record associated resource
        :type resource: :class:`cliquet.resource.BaseResource`

        :param str user_id: the owner of the record
        :param dict record: the record to create.

        :returns: the newly created record.
        :rtype: dict
        """
        raise NotImplementedError

    def get(self, resource, user_id, record_id):
        """Retrieve the record with specified `record_id`, or raise error
        if not found.

        :raises: :exc:`cliquet.storage.exceptions.RecordNotFoundError`

        :param resource: the record associated resource
        :type resource: :class:`cliquet.resource.BaseResource`

        :param str user_id: the owner of the record
        :param str record_id: unique identifier of the record

        :returns: the record object.
        :rtype: dict
        """
        raise NotImplementedError

    def update(self, resource, user_id, record_id, record):
        """Overwrite the `record` with the specified `record_id`.

        If the specified id is not found, the record is created with the
        specified id.

        .. note::

            This will update the collection timestamp.

        :raises: :exc:`cliquet.storage.exceptions.UnicityError`

        :param resource: the record associated resource
        :type resource: :class:`cliquet.resource.BaseResource`

        :param str user_id: the owner of the record
        :param str record_id: unique identifier of the record
        :param dict record: the record to update or create.

        :returns: the updated record.
        :rtype: dict
        """
        raise NotImplementedError

    def delete(self, resource, user_id, record_id):
        """Delete the record with specified `record_id`, and raise error
        if not found.

        Deleted records must be removed from the database, but their ids and
        timestamps of deletion must be tracked for synchronization purposes.
        (See :meth:`cliquet.storage.StorageBase.get_all`)

        .. note::

            This will update the collection timestamp.

        :raises: :exc:`cliquet.storage.exceptions.RecordNotFoundError`

        :param resource: the record associated resource
        :type resource: :class:`cliquet.resource.BaseResource`

        :param str user_id: the owner of the record
        :param str record_id: unique identifier of the record

        :returns: the deleted record, with minimal set of attributes.
        :rtype: dict
        """
        raise NotImplementedError

    def delete_all(self, resource, user_id, filters=None):
        """Delete all records in this `resource` for this `user_id`.

        :param resource: the record associated resource
        :type resource: :class:`cliquet.resource.BaseResource`

        :param str user_id: the owner of the record

        :param filters: Optionnally filter the records to delete.
        :type filters: list of :class:`cliquet.storage.Filter`

        :returns: the list of deleted records, with minimal set of attributes.
        :rtype: list of dict
        """
        raise NotImplementedError

    def get_all(self, resource, user_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False):
        """Retrieve all records in this `resource` for this `user_id`.

        :param resource: the record associated resource
        :type resource: :class:`cliquet.resource.BaseResource`

        :param str user_id: the owner of the record

        :param filters: Optionally filter the records by their attribute.
            Each filter in this list is a tuple of a field, a value and a
            comparison (see `cliquet.utils.COMPARISON`). All filters
            are combined using *AND*.
        :type filters: list of :class:`cliquet.storage.Filter`

        :param sorting: Optionnally sort the records by attribute.
            Each sort instruction in this list refers to a field and a
            direction (negative means descending). All sort instructions are
            cumulative.
        :type sorting: list of :class:`cliquet.storage.Sort`

        :param pagination_rules: Optionnally paginate the list of records.
            This list of rules aims to reduce the set of records to the current
            page. A rule is a list of filters (see `filters` parameter),
            and all rules are combined using *OR*.
        :type pagination_rules: list of list of :class:`cliquet.storage.Filter`

        :param int limit: Optionnally limit the number of records to be
            retrieved.

        :param bool include_deleted: Optionnally include the deleted records
            that match the filters.

        :returns: the limited list of records, and the total number of
            matching records in the collection (deleted ones excluded).
        :rtype: tuple (list, integer)
        """
        raise NotImplementedError
