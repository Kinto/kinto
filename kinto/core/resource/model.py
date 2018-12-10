import warnings


class Model:
    """A resource stores and manipulate objects in its attached storage.

    It is not aware of HTTP environment nor HTTP API.

    Objects are isolated according to the provided `name` and `parent_id`.

    Those notions have no particular semantic and can represent anything.
    For example, the resource `name` can be the *type* of objects stored, and
    `parent_id` can be the current *user id* or *a group* where the resource
    belongs. If left empty, the resource objects are not isolated.
    """

    id_field = "id"
    """Name of `id` field in objects"""

    modified_field = "last_modified"
    """Name of `last modified` field in objects"""

    deleted_field = "deleted"
    """Name of `deleted` field in deleted objects"""

    def __init__(self, storage, id_generator=None, resource_name="", parent_id="", auth=None):
        """
        :param storage: an instance of storage
        :type storage: :class:`kinto.core.storage.Storage`
        :param id_generator: an instance of id generator, used by storage
            on object creation.

        :param str resource_name: the resource name
        :param str parent_id: the default parent id
        """
        self.storage = storage
        self.id_generator = id_generator
        self.parent_id = parent_id
        self.resource_name = resource_name
        self.auth = auth

    def timestamp(self, parent_id=None):
        """Fetch the resource current timestamp.

        :param str parent_id: optional filter for parent id
        :rtype: int
        """
        parent_id = parent_id or self.parent_id
        return self.storage.resource_timestamp(
            resource_name=self.resource_name, parent_id=parent_id, auth=self.auth
        )

    def get_objects(
        self,
        filters=None,
        sorting=None,
        pagination_rules=None,
        limit=None,
        include_deleted=False,
        parent_id=None,
    ):
        """Fetch the resource objects.

        Override to post-process objects after feching them from storage.

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

        :param str parent_id: optional filter for parent id

        :returns: A tuple with the list of objects in the current page,
            the total number of objects in the result set.
        :rtype: tuple
        """
        parent_id = parent_id or self.parent_id
        objects, total_objects = self.storage.get_all(
            resource_name=self.resource_name,
            parent_id=parent_id,
            filters=filters,
            sorting=sorting,
            pagination_rules=pagination_rules,
            limit=limit,
            include_deleted=include_deleted,
            id_field=self.id_field,
            modified_field=self.modified_field,
            deleted_field=self.deleted_field,
            auth=self.auth,
        )
        return objects, total_objects

    def delete_objects(
        self, filters=None, sorting=None, pagination_rules=None, limit=None, parent_id=None
    ):
        """Delete multiple resource objects.

        Override to post-process objects after their deletion from storage.

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

        :param pagination_rules: Optionnally paginate the deletion of objects.
            This list of rules aims to reduce the set of objects to the current
            page. A rule is a list of filters (see `filters` parameter),
            and all rules are combined using *OR*.
        :type pagination_rules: list of list of
            :class:`kinto.core.storage.Filter`

        :param int limit: Optionnally limit the number of objects to be
           deleted.

        :param str parent_id: optional filter for parent id

        :returns: The list of deleted objects from storage.
        """
        parent_id = parent_id or self.parent_id
        return self.storage.delete_all(
            resource_name=self.resource_name,
            parent_id=parent_id,
            filters=filters,
            sorting=sorting,
            pagination_rules=pagination_rules,
            limit=limit,
            id_field=self.id_field,
            modified_field=self.modified_field,
            deleted_field=self.deleted_field,
            auth=self.auth,
        )

    def get_object(self, object_id, parent_id=None):
        """Fetch current view related object, and raise 404 if missing.

        :param str object_id: object identifier
        :param str parent_id: optional filter for parent id

        :returns: the object from storage
        :rtype: dict
        """
        parent_id = parent_id or self.parent_id
        return self.storage.get(
            resource_name=self.resource_name,
            parent_id=parent_id,
            object_id=object_id,
            id_field=self.id_field,
            modified_field=self.modified_field,
            auth=self.auth,
        )

    def create_object(self, obj, parent_id=None):
        """Create an object in the resource.

        Override to perform actions or post-process objects after their
        creation in storage.

        .. code-block:: python

            def create_object(self, obj):
                obj = super().create_object(obj)
                idx = index.store(obj)
                object['index'] = idx
                return object

        :param dict obj: object to store
        :param str parent_id: optional filter for parent id

        :returns: the newly created object.
        :rtype: dict
        """
        parent_id = parent_id or self.parent_id
        return self.storage.create(
            resource_name=self.resource_name,
            parent_id=parent_id,
            obj=obj,
            id_generator=self.id_generator,
            id_field=self.id_field,
            modified_field=self.modified_field,
            auth=self.auth,
        )

    def update_object(self, obj, parent_id=None):
        """Update an object in the resource.

        Override to perform actions or post-process objects after their
        modification in storage.

        .. code-block:: python

            def update_object(self, obj, parent_id=None):
                obj = super().update_object(obj, parent_id)
                subject = f'Object {record[self.id_field]} was changed'
                send_email(subject)
                return object

        :param dict obj: object to store
        :param str parent_id: optional filter for parent id
        :returns: the updated object.
        :rtype: dict
        """
        parent_id = parent_id or self.parent_id
        object_id = obj[self.id_field]
        return self.storage.update(
            resource_name=self.resource_name,
            parent_id=parent_id,
            object_id=object_id,
            obj=obj,
            id_field=self.id_field,
            modified_field=self.modified_field,
            auth=self.auth,
        )

    def delete_object(self, obj, parent_id=None, last_modified=None):
        """Delete an object in the resource.

        Override to perform actions or post-process objects after deletion
        from storage for example:

        .. code-block:: python

            def delete_object(self, obj):
                deleted = super().delete_object(obj)
                erase_media(obj)
                deleted['media'] = 0
                return deleted

        :param dict obj: the object to delete
        :param str parent_id: optional filter for parent id
        :returns: the deleted object.
        :rtype: dict
        """
        parent_id = parent_id or self.parent_id
        object_id = obj[self.id_field]
        return self.storage.delete(
            resource_name=self.resource_name,
            parent_id=parent_id,
            object_id=object_id,
            id_field=self.id_field,
            modified_field=self.modified_field,
            deleted_field=self.deleted_field,
            auth=self.auth,
            last_modified=last_modified,
        )

    @property
    def collection_id(self):
        message = "`collection_id` is deprecated, use `resource_name` instead."
        warnings.warn(message, DeprecationWarning)
        return self.resource_name

    def get_records(self, *args, **kwargs):
        message = "`get_records()` is deprecated, use `get_objects()` instead."
        warnings.warn(message, DeprecationWarning)
        return self.get_objects(*args, **kwargs)

    def delete_records(self, *args, **kwargs):
        message = "`delete_records()` is deprecated, use `delete_objects()` instead."
        warnings.warn(message, DeprecationWarning)
        return self.delete_objects(*args, **kwargs)

    def get_record(self, record_id, parent_id=None):
        message = "`get_record()` is deprecated, use `get_object()` instead."
        warnings.warn(message, DeprecationWarning)
        return self.get_object(object_id=record_id, parent_id=parent_id)

    def create_record(self, record, parent_id=None):
        message = "`create_record()` is deprecated, use `create_object()` instead."
        warnings.warn(message, DeprecationWarning)
        return self.create_object(obj=record, parent_id=parent_id)

    def update_record(self, record, parent_id=None):
        message = "`update_record()` is deprecated, use `update_object()` instead."
        warnings.warn(message, DeprecationWarning)
        return self.update_object(obj=record, parent_id=parent_id)

    def delete_record(self, record, parent_id=None, last_modified=None):
        message = "`delete_record()` is deprecated, use `delete_object()` instead."
        warnings.warn(message, DeprecationWarning)
        return self.delete_object(obj=record, parent_id=parent_id, last_modified=last_modified)


class ShareableModel(Model):
    """A protected resource interacts with the permission backend.
    """

    permissions_field = "__permissions__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Permission backend.
        self.permission = None
        # Object permission id.
        self.get_permission_object_id = None
        # Current user main principal.
        self.current_principal = None
        self.prefixed_principals = None

    def _allow_write(self, perm_object_id):
        """Helper to give the ``write`` permission to the current user.
        """
        self.permission.add_principal_to_ace(perm_object_id, "write", self.current_principal)

    def _annotate(self, obj, perm_object_id):
        permissions = self.permission.get_object_permissions(perm_object_id)
        # Permissions are not returned if user only has read permission.
        writers = permissions.get("write", [])
        principals = self.prefixed_principals + [self.current_principal]
        if len(set(writers) & set(principals)) == 0:
            permissions = {}
        # Insert the permissions values in the response.
        annotated = {**obj, self.permissions_field: permissions}
        return annotated

    def delete_objects(
        self, filters=None, sorting=None, pagination_rules=None, limit=None, parent_id=None
    ):
        """Delete permissions when resource objects are deleted in bulk.
        """
        deleted = super().delete_objects(filters, sorting, pagination_rules, limit, parent_id)
        # Take a huge shortcut in case we want to delete everything.
        if not filters:
            perm_ids = [self.get_permission_object_id(object_id="*")]
        else:
            perm_ids = [self.get_permission_object_id(object_id=r[self.id_field]) for r in deleted]
        self.permission.delete_object_permissions(*perm_ids)
        return deleted

    def get_object(self, object_id, parent_id=None):
        """Fetch current permissions and add them to returned object.
        """
        obj = super().get_object(object_id, parent_id)
        perm_object_id = self.get_permission_object_id(object_id)

        return self._annotate(obj, perm_object_id)

    def create_object(self, obj, parent_id=None):
        """Create object and set specified permissions.

        The current principal is added to the owner (``write`` permission).
        """
        permissions = obj.pop(self.permissions_field, {})
        obj = super().create_object(obj, parent_id)
        object_id = obj[self.id_field]
        perm_object_id = self.get_permission_object_id(object_id)
        self.permission.replace_object_permissions(perm_object_id, permissions)
        self._allow_write(perm_object_id)

        return self._annotate(obj, perm_object_id)

    def update_object(self, obj, parent_id=None):
        """Update object and the specified permissions.

        If no permissions is specified, the current permissions are not
        modified.

        The current principal is added to the owner (``write`` permission).
        """
        permissions = obj.pop(self.permissions_field, {})
        obj = super().update_object(obj, parent_id)
        object_id = obj[self.id_field]
        perm_object_id = self.get_permission_object_id(object_id)
        self.permission.replace_object_permissions(perm_object_id, permissions)
        self._allow_write(perm_object_id)

        return self._annotate(obj, perm_object_id)

    def delete_object(self, object_id, parent_id=None, last_modified=None):
        """Delete object and its associated permissions.
        """
        obj = super().delete_object(object_id, parent_id, last_modified=last_modified)
        perm_object_id = self.get_permission_object_id(object_id)
        self.permission.delete_object_permissions(perm_object_id)

        return obj
