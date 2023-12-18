import logging

import transaction as current_transaction
from pyramid.settings import asbool

from kinto.plugins.quotas import scripts as quotas


logger = logging.getLogger(__name__)


def rebuild_quotas(env, dry_run=False):
    """Administrative command to rebuild quota usage information.

    This command recomputes the amount of space used by all
    collections and all buckets and updates the quota objects in the
    storage backend to their correct values. This can be useful when
    cleaning up after a bug like e.g.
    https://github.com/Kinto/kinto/issues/1226.
    """
    registry = env["registry"]
    settings = registry.settings
    readonly_mode = asbool(settings.get("readonly", False))

    # FIXME: readonly_mode is not meant to be a "maintenance mode" but
    # rather used with a database user that has read-only permissions.
    # If we ever introduce a maintenance mode, we should maybe enforce
    # it here.
    if readonly_mode:
        message = "Cannot rebuild quotas while in readonly mode."
        logger.error(message)
        return 41

    if "kinto.plugins.quotas" not in settings["includes"]:
        message = "Cannot rebuild quotas when quotas plugin is not installed."
        logger.error(message)
        return 42

    quotas.rebuild_quotas(registry.storage, dry_run=dry_run)
    current_transaction.commit()
    return 0
