"""
kinto.core.scripts: utilities to build admin scripts for kinto-based services
"""

from __future__ import absolute_import, print_function
import warnings

from pyramid.settings import asbool


def migrate(env):
    """
    User-friendly frontend to run database migrations.
    """
    registry = env['registry']
    settings = registry.settings
    readonly_backends = ('storage', 'permission')
    readonly_mode = asbool(settings.get('readonly', False))

    for backend in ('cache', 'storage', 'permission'):
        if hasattr(registry, backend):
            if readonly_mode and backend in readonly_backends:
                message = ('Cannot migrate the %s backend while '
                           'in readonly mode.' % backend)
                warnings.warn(message)
            else:
                getattr(registry, backend).initialize_schema()
