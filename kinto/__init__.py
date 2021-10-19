import logging

import pkg_resources
from pyramid.authorization import Authenticated, Everyone
from pyramid.config import Configurator
from pyramid.settings import asbool

import kinto.core
from kinto.authorization import RouteFactory
from kinto.core import utils

# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

# Implemented HTTP API Version
HTTP_API_VERSION = "1.22"

# Main kinto logger
logger = logging.getLogger(__name__)


DEFAULT_SETTINGS = {
    "retry_after_seconds": 3,
    "cache_backend": "kinto.core.cache.memory",
    "permission_backend": "kinto.core.permission.memory",
    "storage_backend": "kinto.core.storage.memory",
    "project_docs": "https://kinto.readthedocs.io/",
    "bucket_create_principals": Authenticated,
    "permissions_read_principals": Everyone,
    "multiauth.authorization_policy": ("kinto.authorization.AuthorizationPolicy"),
    "experimental_collection_schema_validation": False,
    "experimental_permissions_endpoint": False,
    "http_api_version": utils.json_serializer(HTTP_API_VERSION),
    "bucket_id_generator": "kinto.views.NameGenerator",
    "collection_id_generator": "kinto.views.NameGenerator",
    "group_id_generator": "kinto.views.NameGenerator",
    "record_id_generator": "kinto.views.RelaxedUUID",
    "project_name": "kinto",
}


def main(global_config, config=None, **settings):
    if not config:
        config = Configurator(settings=settings, root_factory=RouteFactory)

    config.registry.command = global_config and global_config.get("command", None)

    # Force settings prefix.
    config.add_settings({"kinto.settings_prefix": "kinto"})

    kinto.core.initialize(config, version=__version__, default_settings=DEFAULT_SETTINGS)

    settings = config.get_settings()

    # Expose capability
    schema_enabled = asbool(settings["experimental_collection_schema_validation"])
    if schema_enabled:
        config.add_api_capability(
            "schema",
            description="Validates collection records with JSON schemas.",
            url="https://kinto.readthedocs.io/en/latest/api/1.x/"
            "collections.html#collection-json-schema",
        )

    # Scan Kinto views.
    kwargs = {}

    # Permissions endpoint enabled if permission backend is setup.
    is_admin_enabled = "kinto.plugins.admin" in settings["includes"]
    permissions_endpoint_enabled = (
        is_admin_enabled or asbool(settings["experimental_permissions_endpoint"])
    ) and hasattr(config.registry, "permission")
    if permissions_endpoint_enabled:
        config.add_api_capability(
            "permissions_endpoint",
            description="The permissions endpoint can be used to list all "
            "user objects permissions.",
            url="https://kinto.readthedocs.io/en/latest/configuration/"
            "settings.html#activating-the-permissions-endpoint",
        )
    else:
        kwargs.setdefault("ignore", []).append("kinto.views.permissions")

    config.scan("kinto.views", **kwargs)

    app = config.make_wsgi_app()

    # Install middleware (no-op if disabled)
    return kinto.core.install_middlewares(app, settings)
