import re

from pyramid.security import IAuthorizationPolicy, Authenticated
from zope.interface import implementer

from kinto.core import authorization as core_authorization

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
    'bucket': {
        'write': {
            'bucket': ['write']
        },
        'read': {
            'bucket': ['write', 'read', 'collection:create', 'group:create'],
        },
        'group:create': {
            'bucket': ['write', 'group:create']
        },
        'collection:create': {
            'bucket': ['write', 'collection:create']
        },
    },
    'group': {
        'write': {
            'bucket': ['write'],
            'group': ['write']
        },
        'read': {
            'bucket': ['write', 'read'],
            'group': ['write', 'read']
        }
    },
    'collection': {
        'write': {
            'bucket': ['write'],
            'collection': ['write'],
        },
        'read': {
            'bucket': ['write', 'read'],
            'collection': ['write', 'read', 'record:create'],
        },
        'record:create': {
            'bucket': ['write'],
            'collection': ['write', 'record:create']
        },
    },
    'record': {
        'write': {
            'bucket': ['write'],
            'collection': ['write'],
            'record': ['write']
        },
        'read': {
            'bucket': ['write', 'read'],
            'collection': ['write', 'read'],
            'record': ['write', 'read']
        },
    }
}


def get_object_type(object_uri):
    """Return the type of an object from its id."""
    if re.match(r'/buckets/(.+)/collections/(.+)/records/(.+)?', object_uri):
        return 'record'
    if re.match(r'/buckets/(.+)/collections/(.+)?', object_uri):
        return 'collection'
    if re.match(r'/buckets/(.+)/groups/(.+)?', object_uri):
        return 'group'
    if re.match(r'/buckets/(.+)?', object_uri):
        return 'bucket'
    return None


def relative_object_uri(obj_type, object_uri):
    """Returns object_uri
    """
    obj_parts = object_uri.split('/')
    PARTS_LENGTH = {
        'bucket': 3,
        'collection': 5,
        'group': 5,
        'record': 7
    }
    if obj_type not in PARTS_LENGTH:
        raise ValueError('Invalid object type: %s' % obj_type)

    length = PARTS_LENGTH[obj_type]
    parent_uri = '/'.join(obj_parts[:length])

    if length > len(obj_parts):
        error_msg = ('You cannot build children keys from its parent key. '
                     'Trying to build type "%s" from object key "%s".')
        raise ValueError(error_msg % (obj_type, parent_uri))

    return parent_uri


def build_permissions_set(object_uri, permission):
    """Build a set of all permissions that can grant access to the given
    object URI and unbound permission.

    >>> build_permissions_set('/buckets/blog', 'read')
    set(('/buckets/blog', 'write'))
    set(('/buckets/blog', 'write'))

    """
    obj_type = get_object_type(object_uri)

    # Unknown object type, does not map the INHERITANCE_TREE.
    # In that case, the set of related permissions is empty.
    if obj_type is None:
        return set()

    inherited_perms = PERMISSIONS_INHERITANCE_TREE[obj_type][permission].items()

    granters = set()
    for related_obj_type, implicit_permissions in inherited_perms:
        for permission in implicit_permissions:
            related_uri = relative_object_uri(related_obj_type, object_uri)
            granters.add((related_uri, permission))

    return granters


@implementer(IAuthorizationPolicy)
class AuthorizationPolicy(core_authorization.AuthorizationPolicy):
    def get_bound_permissions(self, *args, **kwargs):
        return build_permissions_set(*args, **kwargs)


class RouteFactory(core_authorization.RouteFactory):
    pass


class BucketRouteFactory(RouteFactory):
    def fetch_shared_records(self, perm, principals, get_bound_permissions):
        """Buckets list is authorized even if no object is accessible for
        the current principals.
        """
        shared = super(BucketRouteFactory, self).fetch_shared_records(perm,
                                                                      principals,
                                                                      get_bound_permissions)
        if shared is None and Authenticated in principals:
            self.shared_ids = []
        return self.shared_ids
