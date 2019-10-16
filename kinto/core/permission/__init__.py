import logging

from pyramid.settings import asbool

logger = logging.getLogger(__name__)


__HEARTBEAT_KEY__ = "__heartbeat__"


class PermissionBase:
    def __init__(self, *args, **kwargs):
        pass

    def initialize_schema(self, dry_run=False):
        """Create every necessary objects (like tables or indices) in the
        backend.

        This is executed with the ``kinto migrate`` command.

        :param bool dry_run: simulate instead of executing the operations.
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

    def get_user_principals(self, user_id):
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

    def get_object_permission_principals(self, object_id, permission):
        """Return the set of principals of a bound permission
        (unbound permission + object id).

        :param str object_id: The object_id the permission is set to.
        :param str permission: The permission to query.
        :returns: The list of user principals
        :rtype: set

        """
        raise NotImplementedError

    def get_accessible_objects(self, principals, bound_permissions=None, with_children=True):
        """Return the list of objects where the specified `principals`
        have some permissions.

        If `bound_permissions` parameter is specified, the list is limited to
        the specified object or permissions.

        :param list principals: List of user principals
        :param list bound_permissions: An optional list of tuples
            (object_id, permission) to limit the results.
            The object ids can be a pattern, (e.g. ``*``, ``'/my/articles*'``).
        :param bool with_children: Include the children of object ids or not.

        :returns: A mapping whose keys are the object_ids and the values are
            the related list of permissions.
        :rtype: dict
        """
        raise NotImplementedError

    def get_authorized_principals(self, bound_permissions):
        """Return the full set of authorized principals for a list of bound
        permissions (object + permission).

        :param str object_id: The object_id the permission is set to.
        :param list bound_permissions: An list of tuples
            (object_id, permission) to be fetched.
        :returns: The list of user principals
        :rtype: set

        """
        raise NotImplementedError

    def check_permission(self, principals, bound_permissions):
        """Test if a principal set have got a permission on an object.

        :param set principals:
            A set of user principals to test the permission against.
        :param list bound_permissions: An list of tuples
            (object_id, permission) to be checked.
        :rtype: bool
        """
        principals = set(principals)
        authorized = self.get_authorized_principals(bound_permissions)
        return len(authorized & principals) > 0

    def get_object_permissions(self, object_id, permissions=None):
        return self.get_objects_permissions([object_id], permissions)[0]

    def get_objects_permissions(self, objects_ids, permissions=None):
        """Return a list of mapping, for each object id specified, with the
        set of principals for each permission.

        :param list objects_ids: The list of object_ids.
        :param list permissions: Optional list of permissions to limit the
            results. If not specified, retrieve all.
        :returns: A list of dictionnaries with the list of user principals for
            each object permission.
        :rtype: list
        """
        raise NotImplementedError

    def replace_object_permissions(self, object_id, permissions):
        """Update the set of principals allowed to perform some actions on an
        object.

        The only update of permissions allowed by Kinto's API is
        complete replacement of some permission (e.g. I don't know who
        was previously allowed to read this object, but now it's Joe,
        Frank, and Paul). This method implements that, completely
        replacing the set of principals who are granted the given
        permissions (while leaving other permissions alone).

        :param str object_id: The object to replace permissions on.
        :param permissions: A dict of perm -> principals (where
        principals is an iterable of individuals) to be granted on
        this object.

        """
        raise NotImplementedError

    def delete_object_permissions(self, *object_id_list):
        """Delete all listed object permissions.

        :param str object_id: Remove given objects permissions.
        """
        raise NotImplementedError


def heartbeat(backend):
    def ping(request):
        """Test the permission backend is operational.

        :param request: current request object
        :type request: :class:`~pyramid:pyramid.request.Request`
        :returns: ``True`` is everything is ok, ``False`` otherwise.
        :rtype: bool
        """
        try:
            if asbool(request.registry.settings.get("readonly")):
                # Do not try to write in readonly mode.
                backend.get_user_principals(__HEARTBEAT_KEY__)
            else:
                backend.add_user_principal(__HEARTBEAT_KEY__, "alive")
                backend.remove_user_principal(__HEARTBEAT_KEY__, "alive")
        except Exception:
            logger.exception("Heartbeat Error")
            return False
        return True

    return ping
