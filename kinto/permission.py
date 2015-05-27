# List of permissions that gives us this permission
PERMISSIONS_INHERITANCE = {
    'bucket:write': {
        'bucket': ['write']
    },
    'bucket:read': {
        'bucket': ['write', 'read']
    },
    'groups:create': {
        'bucket': ['write', 'groups:create']
    },
    'collections:create': {
        'bucket': ['write', 'collections:create']
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
    'records:create': {
        'bucket': ['write'],
        'collection': ['write', 'records:create']
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


def get_object_type(object_id):
    """Return the type of an object from its id."""
    if 'records' in object_id:
        obj_type = 'record'
    elif 'collections' in object_id:
        obj_type = 'collection'
    elif 'buckets' in object_id:
        obj_type = 'bucket'
    else:
        raise ValueError('`%s` key is an invalid object id.' % object_id)
    return obj_type


def build_perm_set_id(obj_type, perm, obj_parts):
    PARTS_LENGTH = {
        'bucket': 3,
        'collection': 5,
        'record': 7
    }
    return 'permission:%s:%s' % (
        '/'.join(obj_parts[:PARTS_LENGTH[obj_type]]),
        perm
    )


def get_perm_keys(object_id, permission):
    obj_parts = object_id.split('/')
    obj_type = get_object_type(object_id)

    permission_type = '%s:%s' % (obj_type, permission)
    keys = set([])

    for perm_obj_type, permissions in \
            PERMISSIONS_INHERITANCE[permission_type].items():
        for other_perm in permissions:
            keys.add(build_perm_set_id(perm_obj_type, other_perm, obj_parts))
    return keys
