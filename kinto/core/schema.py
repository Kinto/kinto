"""
Deprecated module. Moved to :mod:`cliquet.resource.schema`.
"""
import warnings

from cliquet.resource import ResourceSchema as NewResourceSchema  # NOQA


class ResourceSchema(NewResourceSchema):
    def __init__(self, *args, **kwargs):
        message = ('cliquet.schema is now deprecated. '
                   'Please use `cliquet.resource.schema` instead')
        warnings.warn(message, DeprecationWarning)
        super(ResourceSchema, self).__init__(*args, **kwargs)
