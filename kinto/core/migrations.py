from zope.interface import Interface


class IMigratable(Interface):  # ty: ignore[unsupported-base]
    """
    Interface for plugin storage migration objects.
    Register via ``config.add_migration(name, migration)`` in a plugin's
    ``includeme()``. The ``kinto migrate`` command will call
    ``initialize_schema()`` on every registered migration.
    """

    def initialize_schema(client=None, dry_run=False):
        """
        Create or upgrade the plugin's storage schema.
        Receives an optional ``client`` (backend specific)
        and ``dry_run=True`` when called with ``--dry-run``.
        """
