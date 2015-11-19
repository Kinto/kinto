from cliquet import authorization as cliquet_authorization
from pyramid.security import IAuthorizationPolicy
from zope.interface import implementer


# Vocab really matters when you deal with permissions. Let's do a quick recap
# of the terms used here:
#
# Object URI:
#    An unique identifier for an object.
#    for instance, /buckets/blog/collections/articles/records/article1
#
# Object:
#    A common denomination of an object (e.g. "collection" or "record")
#
# Unbound permission:
#    A permission not bound to an object (e.g. "create")
#
# Bound permission:
#    A permission bound to an object (e.g. "collection:create")


# Dictionary which list all permissions a given permission enables.
PERMISSIONS_INHERITANCE_TREE = {
    'bucket:write': {
        'bucket': ['write']
    },
    'bucket:read': {
        'bucket': ['write', 'read']
    },
    'bucket:group:create': {
        'bucket': ['write', 'group:create']
    },
    'bucket:collection:create': {
        'bucket': ['write', 'collection:create']
    },
    'group:write': {
        'bucket': ['write'],
        'group': ['write']
    },
    'group:read': {
        'bucket': ['write', 'read'],
        'group': ['write', 'read']
    },
    'collection:write': {
        'bucket': ['write'],
        'collection': ['write'],
    },
    'collection:read': {
        'bucket': ['write', 'read'],
        'collection': ['write', 'read'],
    },
    'collection:record:create': {
        'bucket': ['write'],
        'collection': ['write', 'record:create']
    },
    'record:write': {
        'bucket': ['write'],
        'collection': ['write'],
        'record': ['write']
    },
    'record:read': {
        'bucket': ['write', 'read'],
        'collection': ['write', 'read'],
        'record': ['write', 'read']
    }
}


def get_object_type(object_uri):
    """Return the type of an object from its id."""

    obj_parts = object_uri.split('/')
    if len(obj_parts) % 2 == 0:
        object_uri = '/'.join(obj_parts[:-1])

    # Order matters here. More precise is tested first.
    if 'records' in object_uri:
        obj_type = 'record'
    elif 'collections' in object_uri:
        obj_type = 'collection'
    elif 'groups' in object_uri:
        obj_type = 'group'
    elif 'buckets' in object_uri:
        obj_type = 'bucket'
    else:
        obj_type = None
    return obj_type


def build_permission_tuple(obj_type, unbound_permission, obj_parts):
    """Returns a tuple of (object_uri, unbound_permission)"""
    PARTS_LENGTH = {
        'bucket': 3,
        'collection': 5,
        'group': 5,
        'record': 7
    }
    if obj_type not in PARTS_LENGTH:
        raise ValueError('Invalid object type: %s' % obj_type)

    if PARTS_LENGTH[obj_type] > len(obj_parts):
        raise ValueError('You cannot build children keys from its parent key.'
                         'Trying to build type "%s" from object key "%s".' % (
                             obj_type, '/'.join(obj_parts)))
    length = PARTS_LENGTH[obj_type]
    return ('/'.join(obj_parts[:length]), unbound_permission)


def build_permissions_set(object_uri, unbound_permission,
                          inheritance_tree=None):
    """Build a set of all permissions that can grant access to the given
    object URI and unbound permission.

    >>> build_required_permissions('/buckets/blog', 'write')
    set(('/buckets/blog', 'write'))

    """

    if inheritance_tree is None:
        inheritance_tree = PERMISSIONS_INHERITANCE_TREE

    obj_type = get_object_type(object_uri)

    # Unknown object type, does not map the INHERITANCE_TREE.
    # In that case, the set of related permissions is empty.
    if obj_type is None:
        return set()

    bound_permission = '%s:%s' % (obj_type, unbound_permission)
    granters = set()

    obj_parts = object_uri.split('/')
    for obj, permission_list in inheritance_tree[bound_permission].items():
        for permission in permission_list:
            granters.add(build_permission_tuple(obj, permission, obj_parts))

    return granters


@implementer(IAuthorizationPolicy)
class AuthorizationPolicy(cliquet_authorization.AuthorizationPolicy):
    def get_bound_permissions(self, *args, **kwargs):
        return build_permissions_set(*args, **kwargs)


class RouteFactory(cliquet_authorization.RouteFactory):
    pass
