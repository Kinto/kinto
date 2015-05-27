__HEARTBEAT_KEY__ = '__heartbeat__'


class PermissionBase(object):

    def __init__(self, *args, **kwargs):
        pass

    def initialize_schema(self):
        """Create every necessary objects (like tables or indices) in the
        backend.

        This is excuted when the ``cliquet migrate`` command is ran.
        """
        raise NotImplementedError

    def flush(self):
        """Delete every values."""
        raise NotImplementedError

    def add_user_principal(self, user_id, principal):
        """Add a principal to a user.

        :param user_id: The user_id to add the principal to.
        :type user_id: string
        :param principal: The principal to add to the user.
        :type user_id: string
        """
        raise NotImplementedError

    def remove_user_principal(self, user_id, principal):
        """Remove a principal to a user.

        :param user_id: The user_id to remove the principal to.
        :type user_id: string
        :param principal: The principal to remove to the user.
        :type user_id: string
        """
        raise NotImplementedError

    def add_object_permission_principal(self, object_id, permission,
                                        principal):
        """Add a principal to an Access Control Entry.

        :param object_id: The object to add the permission principal to.
        :type object_id: string
        :param permission: The permission object to add the principal to.
        :type permission: string
        :param principal: The principal to add to the ACE.
        :type user_id: string
        """
        raise NotImplementedError

    def remove_object_permission_principal(self, object_id, permission,
                                           principal):
        """Remove a principal to an Access Control Entry.

        :param object_id: The object to remove the permission principal to.
        :type object_id: string
        :param permission: The permission object to remove the principal to.
        :type permission: string
        :param principal: The principal to remove to the ACE.
        :type user_id: string
        """
        raise NotImplementedError

    def has_permission(self, object_id, permission, user_id):
        """Test if a principal set have got a permission on an object.

        :param object_id: The object concerned by the permission.
        :type object_id: string
        :param permission: The permission on the object.
        :type permission: string
        :param principal: The principals list of the user to test.
        :type user_id: set
        """
        raise NotImplementedError

    def ping(self, request):
        """Test that cache backend is operationnal.

        :param request: current request object
        :type request: :class:`~pyramid:pyramid.request.Request`
        :returns: ``True`` is everything is ok, ``False`` otherwise.
        :rtype: bool
        """
        self.add_user_principal(__HEARTBEAT_KEY__, 'alive')
        self.remove_user_principal(__HEARTBEAT_KEY__, 'alive')
