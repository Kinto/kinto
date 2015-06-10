from cliquet.storage.exceptions import BackendError

__HEARTBEAT_KEY__ = '__heartbeat__'


class PermissionBase(object):

    def __init__(self, *args, **kwargs):
        pass

    def initialize_schema(self):
        """Create every necessary objects (like tables or indices) in the
        backend.

        This is excuted with the ``cliquet migrate`` command.
        """
        raise NotImplementedError

    def flush(self):
        """Delete all data stored in the permission backend."""
        raise NotImplementedError

    def add_user_principal(self, user_id, principal):
        """Add an additional principal to a user.

        :param str user_id: The user_id to add the principal to.
        :param str principal: The principal to add.
        """
        raise NotImplementedError

    def remove_user_principal(self, user_id, principal):
        """Remove an additional principal from a user.

        :param str user_id: The user_id to remove the principal to.
        :param str principal: The principal to remove.
        """
        raise NotImplementedError

    def user_principals(self, user_id):
        """Return the set of additionnal principals given to a user.

        :param str user_id: The user_id to get the list of groups for.
        :returns: The list of group principals the user is in.
        :rtype: set

        """
        raise NotImplementedError

    def add_principal_to_ace(self, object_id, permission, principal):
        """Add a principal to an Access Control Entry.

        :param str object_id: The object to add the permission principal to.
        :param str permission: The permission to add the principal to.
        :param str principal: The principal to add to the ACE.
        """
        raise NotImplementedError

    def remove_principal_from_ace(self, object_id, permission, principal):
        """Remove a principal to an Access Control Entry.

        :param str object_id: The object to remove the permission principal to.
        :param str permission: The permission that should be removed.
        :param str principal: The principal to remove to the ACE.
        """
        raise NotImplementedError

    def object_permission_principals(self, object_id, permission):
        """Return the set of principals of a bound permission
        (unbound permission + object id).

        :param str object_id: The object_id the permission is set to.
        :param str permission: The permission to query.
        :returns: The list of user principals
        :rtype: set

        """
        raise NotImplementedError

    def object_permission_authorized_principals(self, object_id, permission,
                                                get_bound_permissions=None):
        """Return the full set of authorized principals for a given
        permission + object (bound permission).

        :param str object_id: The object_id the permission is set to.
        :param str permission: The permission to query.
        :param function get_bound_permissions:
            The methods to call in order to generate the list of permission to
            verify against. (ie: if you can write, you can read)

        :returns: The list of user principals
        :rtype: set

        """
        raise NotImplementedError

    def check_permission(self, object_id, permission, principals,
                         get_bound_permissions=None):
        """Test if a principal set have got a permission on an object.

        :param str object_id:
            The identifier of the object concerned by the permission.
        :param str permission: The permission to test.
        :param set principals:
            A set of user principals to test the permission against.
        :param function get_bound_permissions:
            The method to call in order to generate the set of
            permission to verify against. (ie: if you can write, you can read)

        """
        principals = set(principals)
        authorized_principals = self.object_permission_authorized_principals(
            object_id, permission, get_bound_permissions)
        return len(authorized_principals & principals) > 0

    def ping(self, request):
        """Test the permission backend is operationnal.

        :param request: current request object
        :type request: :class:`~pyramid:pyramid.request.Request`
        :returns: ``True`` is everything is ok, ``False`` otherwise.
        :rtype: bool
        """
        try:
            self.add_user_principal(__HEARTBEAT_KEY__, 'alive')
            self.remove_user_principal(__HEARTBEAT_KEY__, 'alive')
        except BackendError:
            return False
        return True
