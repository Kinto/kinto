"""
Deprecated module. Moved to :mod:`kinto.core.resource.schema`.
"""
import warnings

from kinto.core.resource import ResourceSchema as NewResourceSchema  # NOQA


class ResourceSchema(NewResourceSchema):
    def __init__(self, *args, **kwargs):
        message = ('kinto.core.schema is now deprecated. '
                   'Please use `kinto.core.resource.schema` instead')
        warnings.warn(message, DeprecationWarning)
        super(ResourceSchema, self).__init__(*args, **kwargs)
