from pyramid.settings import asbool

from cliquet.logs import logger


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

    def remove_principal(self, principal):
        """Remove a principal from every user.

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

    def principals_accessible_objects(self, principals, permission,
                                      object_id_match=None,
                                      get_bound_permissions=None):
        """Return the list of objects id where the specified `principals`
        have the specified `permission`.

        :param list principal: List of user principals
        :param str permission: The permission to query.
        :param str object_id_match: Filter object ids based on a pattern
            (e.g. ``'*articles*'``).
        :param function get_bound_permissions:
            The methods to call in order to generate the list of permission to
            verify against. (ie: if you can write, you can read)
        :returns: The list of object ids
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

    def object_permissions(self, object_id, permissions=None):
        """Return the set of principals for each object permission.

        :param str object_id: The object_id the permission is set to.
        :param list permissions: List of permissions to retrieve.
                                 If not define will try to find them all.
        :returns: The dictionnary with the list of user principals for
                  each object permissions
        :rtype: dict

        """
        raise NotImplementedError

    def replace_object_permissions(self, object_id, permissions):
        """Replace given object permissions.

        :param str object_id: The object to replace permissions to.
        :param str permissions: The permissions dict to replace.
        """
        raise NotImplementedError

    def delete_object_permissions(self, *object_id_list):
        """Delete all listed object permissions.

        :param str object_id: Remove given objects permissions.
        """
        raise NotImplementedError


def heartbeat(backend):
    def ping(request):
        """Test the permission backend is operationnal.

        :param request: current request object
        :type request: :class:`~pyramid:pyramid.request.Request`
        :returns: ``True`` is everything is ok, ``False`` otherwise.
        :rtype: bool
        """
        try:
            if asbool(request.registry.settings.get('readonly')):
                # Do not try to write in readonly mode.
                backend.user_principals(__HEARTBEAT_KEY__)
            else:
                backend.add_user_principal(__HEARTBEAT_KEY__, 'alive')
                backend.remove_user_principal(__HEARTBEAT_KEY__, 'alive')
        except:
            logger.exception("Heartbeat Error")
            return False
        return True
    return ping
