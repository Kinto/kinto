"""
kinto.core.scripts: utilities to build admin scripts for kinto-based services
"""

import logging

from pyramid.settings import asbool


logger = logging.getLogger(__name__)


def migrate(env, dry_run=False):
    """
    User-friendly frontend to run database migrations.
    """
    from kinto.core.migrations import IMigratable
    from kinto.core.storage.postgresql import PostgreSQLPluginMigration
    from kinto.core.storage.postgresql import Storage as PostgreSQLStorage

    registry = env["registry"]
    settings = registry.settings
    readonly_backends = ("storage", "permission")
    readonly_mode = asbool(settings.get("readonly", False))

    for backend in ("cache", "storage", "permission"):
        if hasattr(registry, backend):
            if readonly_mode and backend in readonly_backends:
                message = f"Cannot migrate the {backend} backend while in readonly mode."
                logger.error(message)
            else:
                getattr(registry, backend).initialize_schema(dry_run=dry_run)

    for name, migration in registry.getUtilitiesFor(IMigratable):
        if not isinstance(migration, PostgreSQLPluginMigration):
            logger.warning("Migration has specific type %r for plugin %r.", type(migration), name)
        if not isinstance(registry.storage, PostgreSQLStorage):
            # Do not attempt to run PostgreSQL-specific migrations when the storage backend is not PostgreSQL.
            # (eg. do not show warning, or local development or tests will be flooded)
            continue
        logger.info("Running migrations for plugin %r.", name)
        migration.initialize_schema(registry.storage.client, dry_run=dry_run)


def purge_deleted(env, resource_names, max_retained):
    logger.info("Keep only %r tombstones per parent and resource." % max_retained)

    registry = env["registry"]

    count = 0
    for resource_name in resource_names:
        count += registry.storage.purge_deleted(
            resource_name=resource_name,
            parent_id="*",
            max_retained=max_retained,
            force_commit=True,
        )

    logger.info("%s tombstone(s) deleted." % count)
    return 0


def flush_cache(env):
    registry = env["registry"]
    registry.cache.flush()
    logger.info("Cache has been cleared.")
    return 0
