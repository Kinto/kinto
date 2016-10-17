import re

from pyramid.security import IAuthorizationPolicy
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
    '': {  # Granted via settings only.
        'bucket:create': {},
        'write': {},
        'read': {},
    },
    'bucket': {
        'write': {
            'bucket': ['write']
        },
        'read': {
            'bucket': ['write', 'read'],
        },
        'read:attributes': {
            'bucket': ['write', 'read', 'collection:create', 'group:create']
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
        },
    },
    'collection': {
        'write': {
            'bucket': ['write'],
            'collection': ['write'],
        },
        'read': {
            'bucket': ['write', 'read'],
            'collection': ['write', 'read'],
        },
        'read:attributes': {
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


def _resource_endpoint(object_uri):
    """Determine the resource name and whether it is the plural endpoint from
    the specified `object_uri`. Returns `(None, None)` for the root URL plural
    endpoint.
    """
    url_patterns = [
        ('record', r'/buckets/(.+)/collections/(.+)/records/(.+)?'),
        ('collection', r'/buckets/(.+)/collections/(.+)?'),
        ('group', r'/buckets/(.+)/groups/(.+)?'),
        ('bucket', r'/buckets/(.+)?'),
        ('', r'/(buckets)')  # Root buckets list.
    ]
    for resource_name, pattern in url_patterns:
        m = re.match(pattern, object_uri)
        if m:
            plural = '/' in m.groups()[-1]
            return resource_name, plural
    raise ValueError("%r is not a resource." % object_uri)


def _relative_object_uri(resource_name, object_uri):
    """Returns object_uri
    """
    obj_parts = object_uri.split('/')
    PARTS_LENGTH = {
        '': 1,
        'bucket': 3,
        'collection': 5,
        'group': 5,
        'record': 7
    }
    length = PARTS_LENGTH[resource_name]
    parent_uri = '/'.join(obj_parts[:length])

    if length > len(obj_parts):
        error_msg = 'Cannot get URL of resource %r from parent %r.'
        raise ValueError(error_msg % (resource_name, parent_uri))

    return parent_uri


def _inherited_permissions(object_uri, permission):
    """Build the list of all permissions that can grant access to the given
    object URI and permission.

    >>> _inherited_permissions('/buckets/blog/collections/article', 'read')
    [('/buckets/blog/collections/article', 'write'),
     ('/buckets/blog/collections/article', 'read'),
     ('/buckets/blog', 'write'),
     ('/buckets/blog', 'read')]

    """
    try:
        resource_name, plural = _resource_endpoint(object_uri)
    except ValueError:
        return []  # URL that are not resources have no inherited perms.

    object_perms_tree = PERMISSIONS_INHERITANCE_TREE[resource_name]

    # When requesting permissions for a single object, we check if they are any
    # specific inherited permissions for the attributes.
    attributes_permission = '%s:attributes' % permission if not plural else permission
    inherited_perms = object_perms_tree.get(attributes_permission, object_perms_tree[permission])

    granters = set()
    for related_resource_name, implicit_permissions in inherited_perms.items():
        for permission in implicit_permissions:
            related_uri = _relative_object_uri(related_resource_name, object_uri)
            granters.add((related_uri, permission))

    # Sort by ascending URLs.
    return sorted(granters, key=lambda uri_perm: len(uri_perm[0]), reverse=True)


@implementer(IAuthorizationPolicy)
class AuthorizationPolicy(core_authorization.AuthorizationPolicy):
    def get_bound_permissions(self, *args, **kwargs):
        return _inherited_permissions(*args, **kwargs)


class RouteFactory(core_authorization.RouteFactory):
    pass
