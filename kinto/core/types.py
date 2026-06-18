from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pyramid.config import Configurator as PyramidConfigurator
from pyramid.registry import Registry as PyramidRegistry
from pyramid.request import Request as PyramidRequest


if TYPE_CHECKING:
    from kinto.core.cache import CacheBase
    from kinto.core.permission import PermissionBase
    from kinto.core.storage import StorageBase


class Registry(PyramidRegistry):
    """Pyramid registry, augmented with the backends and attributes that
    Kinto attaches at startup.

    This exists so that type checkers know about the dynamically-attached
    attributes (``storage``, ``permission``, ``cache``, ...) that are not
    declared on :class:`pyramid.registry.Registry`.
    """

    settings: dict
    notify: Callable
    registerUtility: Callable
    metrics: Any
    storage: "StorageBase"
    permission: "PermissionBase"
    cache: "CacheBase"
    id_generators: dict
    api_capabilities: dict
    heartbeats: dict
    command: Any
    route_prefix: str


class Request(PyramidRequest):
    """Pyramid request, augmented with the properties and methods that Kinto
    attaches via ``config.add_request_method()`` (see :func:`kinto.core.includeme`).

    This exists so that type checkers know about the dynamically-attached
    attributes (``prefixed_userid``, ``bound_data``, ``registry.storage``, ...)
    that are not declared on :class:`pyramid.request.Request`.
    """

    registry: Registry
    bound_data: dict
    matchdict: dict
    errors: Any
    validated: dict
    selected_userid: str
    authn_type: str
    prefixed_userid: str | None
    prefixed_principals: list
    current_resource_name: str


class Configurator(PyramidConfigurator):
    """Pyramid configurator whose ``registry`` is a Kinto :class:`Registry`.

    This exists so that type checkers know about the attributes that Kinto
    attaches to the registry (``storage``, ``api_capabilities``, ...) when
    they are accessed through ``config.registry``.
    """

    registry: Registry
