import six

from kinto.core.utils import DeprecatedMeta


class Model(object):
    """A collection stores and manipulate records in its attached storage.

    It is not aware of HTTP environment nor protocol.

    Records are isolated according to the provided `name` and `parent_id`.

    Those notions have no particular semantic and can represent anything.
    For example, the collection `name` can be the *type* of objects stored, and
    `parent_id` can be the current *user id* or *a group* where the collection
    belongs. If left empty, the collection records are not isolated.
    """
    id_field = 'id'
    """Name of `id` field in records"""

    modified_field = 'last_modified'
    """Name of `last modified` field in records"""

    deleted_field = 'deleted'
    """Name of `deleted` field in deleted records"""

    def __init__(self, storage, id_generator=None, collection_id='',
                 parent_id='', auth=None):
        """
        :param storage: an instance of storage
        :type storage: :class:`kinto.core.storage.Storage`
        :param id_generator: an instance of id generator, used by storage
            on record creation.

        :param str collection_id: the collection id
        :param str parent_id: the default parent id
        """
        self.storage = storage
        self.id_generator = id_generator
        self.parent_id = parent_id
        self.collection_id = collection_id
        self.auth = auth

    def timestamp(self, parent_id=None):
        """Fetch the collection current timestamp.

        :param str parent_id: optional filter for parent id
        :rtype: integer
        """
        parent_id = parent_id or self.parent_id
        return self.storage.collection_timestamp(
            collection_id=self.collection_id,
            parent_id=parent_id,
            auth=self.auth)

    def get_records(self, filters=None, sorting=None, pagination_rules=None,
                    limit=None, include_deleted=False, parent_id=None):
        """Fetch the collection records.

        Override to post-process records after feching them from storage.

        :param filters: Optionally filter the records by their attribute.
            Each filter in this list is a tuple of a field, a value and a
            comparison (see `kinto.core.utils.COMPARISON`). All filters
            are combined using *AND*.
        :type filters: list of :class:`kinto.core.storage.Filter`

        :param sorting: Optionnally sort the records by attribute.
            Each sort instruction in this list refers to a field and a
            direction (negative means descending). All sort instructions are
            cumulative.
        :type sorting: list of :class:`kinto.core.storage.Sort`

        :param pagination_rules: Optionnally paginate the list of records.
            This list of rules aims to reduce the set of records to the current
            page. A rule is a list of filters (see `filters` parameter),
            and all rules are combined using *OR*.
        :type pagination_rules: list of list of
            :class:`kinto.core.storage.Filter`

        :param int limit: Optionnally limit the number of records to be
            retrieved.

        :param bool include_deleted: Optionnally include the deleted records
            that match the filters.

        :param str parent_id: optional filter for parent id

        :returns: A tuple with the list of records in the current page,
            the total number of records in the result set.
        :rtype: tuple
        """
        parent_id = parent_id or self.parent_id
        records, total_records = self.storage.get_all(
            collection_id=self.collection_id,
            parent_id=parent_id,
            filters=filters,
            sorting=sorting,
            pagination_rules=pagination_rules,
            limit=limit,
            include_deleted=include_deleted,
            id_field=self.id_field,
            modified_field=self.modified_field,
            deleted_field=self.deleted_field,
            auth=self.auth)
        return records, total_records

    def delete_records(self, filters=None, parent_id=None):
        """Delete multiple collection records.

        Override to post-process records after their deletion from storage.

        :param filters: Optionally filter the records by their attribute.
            Each filter in this list is a tuple of a field, a value and a
            comparison (see `kinto.core.utils.COMPARISON`). All filters
            are combined using *AND*.
        :type filters: list of :class:`kinto.core.storage.Filter`

        :param str parent_id: optional filter for parent id

        :returns: The list of deleted records from storage.
        """
        parent_id = parent_id or self.parent_id
        return self.storage.delete_all(collection_id=self.collection_id,
                                       parent_id=parent_id,
                                       filters=filters,
                                       id_field=self.id_field,
                                       modified_field=self.modified_field,
                                       deleted_field=self.deleted_field,
                                       auth=self.auth)

    def get_record(self, record_id, parent_id=None):
        """Fetch current view related record, and raise 404 if missing.

        :param str record_id: record identifier
        :param str parent_id: optional filter for parent id

        :returns: the record from storage
        :rtype: dict
        """
        parent_id = parent_id or self.parent_id
        return self.storage.get(collection_id=self.collection_id,
                                parent_id=parent_id,
                                object_id=record_id,
                                id_field=self.id_field,
                                modified_field=self.modified_field,
                                auth=self.auth)

    def create_record(self, record, parent_id=None, unique_fields=None):
        """Create a record in the collection.

        Override to perform actions or post-process records after their
        creation in storage.

        .. code-block:: python

            def create_record(self, record):
                record = super(MyModel, self).create_record(record)
                idx = index.store(record)
                record['index'] = idx
                return record

        :param dict record: record to store
        :param str parent_id: optional filter for parent id
        :param tuple unique_fields: list of fields that should remain unique

        :returns: the newly created record.
        :rtype: dict
        """
        parent_id = parent_id or self.parent_id
        return self.storage.create(collection_id=self.collection_id,
                                   parent_id=parent_id,
                                   record=record,
                                   id_generator=self.id_generator,
                                   unique_fields=unique_fields,
                                   id_field=self.id_field,
                                   modified_field=self.modified_field,
                                   auth=self.auth)

    def update_record(self, record, parent_id=None, unique_fields=None):
        """Update a record in the collection.

        Override to perform actions or post-process records after their
        modification in storage.

        .. code-block:: python

            def update_record(self, record, parent_id=None,unique_fields=None):
                record = super(MyModel, self).update_record(record,
                                                            parent_id,
                                                            unique_fields)
                subject = 'Record {} was changed'.format(record[self.id_field])
                send_email(subject)
                return record

        :param dict record: record to store
        :param str parent_id: optional filter for parent id
        :param tuple unique_fields: list of fields that should remain unique
        :returns: the updated record.
        :rtype: dict
        """
        parent_id = parent_id or self.parent_id
        record_id = record[self.id_field]
        return self.storage.update(collection_id=self.collection_id,
                                   parent_id=parent_id,
                                   object_id=record_id,
                                   record=record,
                                   unique_fields=unique_fields,
                                   id_field=self.id_field,
                                   modified_field=self.modified_field,
                                   auth=self.auth)

    def delete_record(self, record, parent_id=None, last_modified=None):
        """Delete a record in the collection.

        Override to perform actions or post-process records after deletion
        from storage for example:

        .. code-block:: python

            def delete_record(self, record):
                deleted = super(MyModel, self).delete_record(record)
                erase_media(record)
                deleted['media'] = 0
                return deleted

        :param dict record: the record to delete
        :param dict record: record to store
        :param str parent_id: optional filter for parent id
        :returns: the deleted record.
        :rtype: dict
        """
        parent_id = parent_id or self.parent_id
        record_id = record[self.id_field]
        return self.storage.delete(collection_id=self.collection_id,
                                   parent_id=parent_id,
                                   object_id=record_id,
                                   id_field=self.id_field,
                                   modified_field=self.modified_field,
                                   deleted_field=self.deleted_field,
                                   auth=self.auth,
                                   last_modified=last_modified)


class ShareableModel(Model):
    """A protected collection interacts with the permission backend.
    """
    permissions_field = '__permissions__'

    def __init__(self, *args, **kwargs):
        super(ShareableModel, self).__init__(*args, **kwargs)
        # Permission backend.
        self.permission = None
        # Object permission id.
        self.get_permission_object_id = None
        # Current user main principal.
        self.current_principal = None

    def _allow_write(self, perm_object_id):
        """Helper to give the ``write`` permission to the current user.
        """
        self.permission.add_principal_to_ace(perm_object_id,
                                             'write',
                                             self.current_principal)

    def delete_records(self, filters=None, parent_id=None):
        """Delete permissions when collection records are deleted in bulk.
        """
        deleted = super(ShareableModel, self).delete_records(filters,
                                                             parent_id)
        perm_ids = [self.get_permission_object_id(record_id=r[self.id_field])
                    for r in deleted]
        self.permission.delete_object_permissions(*perm_ids)
        return deleted

    def get_record(self, record_id, parent_id=None):
        """Fetch current permissions and add them to returned record.
        """
        record = super(ShareableModel, self).get_record(record_id, parent_id)
        perm_object_id = self.get_permission_object_id(record_id)
        permissions = self.permission.object_permissions(perm_object_id)

        annotated = record.copy()
        annotated[self.permissions_field] = permissions
        return annotated

    def create_record(self, record, parent_id=None, unique_fields=None):
        """Create record and set specified permissions.

        The current principal is added to the owner (``write`` permission).
        """
        permissions = record.pop(self.permissions_field, {})
        record = super(ShareableModel, self).create_record(record,
                                                           parent_id,
                                                           unique_fields)
        record_id = record[self.id_field]
        perm_object_id = self.get_permission_object_id(record_id)
        self.permission.replace_object_permissions(perm_object_id, permissions)
        self._allow_write(perm_object_id)
        permissions = self.permission.object_permissions(perm_object_id)

        annotated = record.copy()
        annotated[self.permissions_field] = permissions
        return annotated

    def update_record(self, record, parent_id=None, unique_fields=None):
        """Update record and the specified permissions.

        If no permissions is specified, the current permissions are not
        modified.

        The current principal is added to the owner (``write`` permission).
        """
        permissions = record.pop(self.permissions_field, {})
        record = super(ShareableModel, self).update_record(record,
                                                           parent_id,
                                                           unique_fields)
        record_id = record[self.id_field]
        perm_object_id = self.get_permission_object_id(record_id)
        self.permission.replace_object_permissions(perm_object_id, permissions)
        self._allow_write(perm_object_id)
        permissions = self.permission.object_permissions(perm_object_id)

        annotated = record.copy()
        annotated[self.permissions_field] = permissions
        return annotated

    def delete_record(self, record_id, parent_id=None, last_modified=None):
        """Delete record and its associated permissions.
        """
        record = super(ShareableModel, self).delete_record(
            record_id, parent_id, last_modified=last_modified)
        perm_object_id = self.get_permission_object_id(record_id)
        self.permission.delete_object_permissions(perm_object_id)

        return record


@six.add_metaclass(DeprecatedMeta)
class ProtectedModel(ShareableModel):
    __deprecation_warning__ = ('ProtectedModel is deprecated. '
                               'Use ShareableModel instead.')
